"""Mailversand von Verarbeitungsergebnissen.

Datenschutz-Vertrag dieses Endpunkts:
- Die Empfängeradresse wird ausschließlich für den einen Versand verwendet.
- Die Adresse wird weder persistiert noch geloggt (auch nicht in Fehlerpfaden).
- Ohne konfigurierten SMTP-Host (PDFAPP_SMTP_HOST) antwortet der Endpoint 503.
"""

import re
from email.message import EmailMessage

import aiosmtplib
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.config import settings
from app.ratelimit import limiter

router = APIRouter(prefix="/mail", tags=["Mail"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.get("/status")
async def mail_status():
    """Ob Mailversand auf diesem Server konfiguriert ist."""
    return {"available": bool(settings.smtp_host)}


@router.post("/send")
@limiter.limit(settings.rate_limit_mail)
async def send_results(
    request: Request,
    to: str = Form(...),
    subject: str = Form("Ihre Dateien vom PDF-Editor"),
    files: list[UploadFile] = File(...),
    turnstile_token: str | None = Form(None),
):
    """Sendet die übergebenen Ergebnis-Dateien als Anhang an die angegebene Adresse."""
    from fastapi.concurrency import run_in_threadpool

    from app.api.auth import verify_turnstile_or_403

    # Turnstile-HTTP-Aufruf blockiert sonst den Event-Loop (sync httpx)
    await run_in_threadpool(
        verify_turnstile_or_403,
        turnstile_token,
        request.client.host if request.client else None,
    )
    # Header-Injection über das Betreff-Feld verhindern
    subject = subject.replace("\r", " ").replace("\n", " ").strip()[:200] or "Ihre Dateien"
    if not settings.smtp_host:
        raise HTTPException(
            status_code=503, detail="Mailversand ist auf diesem Server nicht konfiguriert"
        )

    to = to.strip()
    if not EMAIL_RE.match(to):
        raise HTTPException(status_code=400, detail="Ungültige E-Mail-Adresse")
    if not files:
        raise HTTPException(status_code=400, detail="Keine Dateien übergeben")

    max_bytes = settings.mail_max_attachment_mb * 1024 * 1024
    attachments: list[tuple[str, bytes]] = []
    total = 0
    for f in files:
        content = await f.read()
        total += len(content)
        if total > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Anhänge zu groß für den Mailversand "
                    f"(max {settings.mail_max_attachment_mb} MB gesamt) — "
                    "bitte den ZIP-Download nutzen"
                ),
            )
        attachments.append((f.filename or "datei.pdf", content))

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(
        "Guten Tag,\n\n"
        "anbei die von Ihnen im PDF-Editor erstellten Dateien.\n\n"
        "Hinweis: Ihre E-Mail-Adresse wurde ausschließlich für diesen einen "
        "Versand verwendet und weder gespeichert noch protokolliert.\n"
    )
    for filename, content in attachments:
        msg.add_attachment(
            content,
            maintype="application",
            subtype="octet-stream",
            filename=filename,
        )

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_starttls,
            timeout=30,
        )
    except Exception:
        # Bewusst ohne Exception-Detail und ohne Adresse: SMTP-Fehlermeldungen
        # können die Empfängeradresse enthalten und würden sonst geloggt.
        raise HTTPException(
            status_code=502, detail="Mailversand fehlgeschlagen — bitte später erneut versuchen"
        ) from None

    return {"sent": True, "attachments": len(attachments)}
