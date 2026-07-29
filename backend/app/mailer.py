"""Einfacher Text-Mailversand für Konto-Flows (Verifikation, Passwort-Reset).

Gleiche Datenschutz-Verträge wie api/mail.py: Adressen werden weder
persistiert noch geloggt; ohne SMTP-Konfiguration ist der Versand deaktiviert.
"""

from email.message import EmailMessage

import aiosmtplib

from app.config import settings


def mail_configured() -> bool:
    return bool(settings.smtp_host)


async def send_plain_mail(to: str, subject: str, body: str) -> None:
    """Wirft bei Fehlern — Aufrufer entscheidet über die Außenwirkung."""
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_starttls,
        timeout=30,
    )
