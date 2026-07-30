"""API der Modulkatalog-Erweiterungen (siehe pdf_more_service).

Office→PDF, Text-Exporte (Markdown/HTML/JSON/CSV), Bereinigung,
Rechteverwaltung, Signaturprüfung, leere Seiten, Prüfakte,
Qualitätsprüfung und lokale KI-Funktionen.
"""

import io
import re

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import current_limits
from app.services.pdf_more_service import OFFICE_EXTENSIONS, get_pdf_more

router = APIRouter(prefix="/pdf-more", tags=["PDF Erweiterungen"])

_EXPORT_MEDIA = {
    "markdown": ("text/markdown; charset=utf-8", ".md"),
    "html": ("text/html; charset=utf-8", ".html"),
    "json": ("application/json; charset=utf-8", ".json"),
}


def _safe_name(name: str) -> str:
    return re.sub(r'[\r\n"\\;]+', "_", name)[:150] or "datei"


def _name(file: UploadFile) -> str:
    return (file.filename or "document").rsplit(".", 1)[0]


def _validate_pdf(file: UploadFile, content: bytes):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien erlaubt")
    limits = current_limits()
    if len(content) > limits.max_file:
        raise HTTPException(
            status_code=400, detail=f"Datei zu groß (max {limits.max_file_mb} MB)"
        )


def _pdf_response(data: bytes, filename: str, headers: dict | None = None):
    h = {"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'}
    if headers:
        h.update(headers)
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=h)


@router.get("/status")
async def check_status():
    return get_pdf_more().check_features()


# ── Office/HTML → PDF ─────────────────────────────────────────


@router.post("/office-to-pdf")
def office_to_pdf(file: UploadFile = File(...)):
    """Sync-Endpoint (Threadpool): LibreOffice läuft als Subprozess."""
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in OFFICE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp nicht unterstützt. Erlaubt: {', '.join(sorted(OFFICE_EXTENSIONS))}",
        )
    content = file.file.read()
    limits = current_limits()
    if len(content) > limits.max_file:
        raise HTTPException(
            status_code=400, detail=f"Datei zu groß (max {limits.max_file_mb} MB)"
        )
    result = get_pdf_more().office_to_pdf(content, ext)
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}.pdf")


# ── PDF → Markdown / HTML / JSON / CSV ────────────────────────


@router.post("/export/{fmt}")
async def export_format(fmt: str, file: UploadFile = File(...)):
    if fmt not in _EXPORT_MEDIA:
        raise HTTPException(
            status_code=400, detail="Format muss markdown, html oder json sein"
        )
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().export_text_format(content, fmt)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    media, suffix = _EXPORT_MEDIA[fmt]
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_name(_name(file))}{suffix}"'
        },
    )


@router.post("/to-csv")
async def to_csv(
    file: UploadFile = File(...),
    pages: str = Form("", description='Seitenbereich, z.B. "1-3,5" — leer = alle'),
):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().pdf_to_csv(content, pages=pages or None)
    if not result.success:
        status = 422 if "Keine Tabellen" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_name(_name(file))}.csv"',
            "X-Tables-Found": str((result.metadata or {}).get("tables", 0)),
        },
    )


# ── Bereinigen ────────────────────────────────────────────────


@router.post("/clean")
async def clean_pdf(file: UploadFile = File(...)):
    """Metadaten, XMP, JavaScript, eingebettete Dateien und versteckte
    Inhalte entfernen."""
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().clean_pdf(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_bereinigt.pdf")


# ── Rechteverwaltung ──────────────────────────────────────────


@router.post("/permissions")
async def set_permissions(
    file: UploadFile = File(...),
    owner_password: str = Form(..., min_length=1),
    allow_print: bool = Form(True),
    allow_copy: bool = Form(False),
    allow_modify: bool = Form(False),
    allow_annotate: bool = Form(True),
):
    """Nutzungsrechte einschränken (Drucken/Kopieren/Ändern/Kommentieren) —
    ohne Öffnen-Passwort, gesichert über ein Besitzer-Passwort."""
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().set_permissions(
        content,
        owner_password,
        allow_print=allow_print,
        allow_copy=allow_copy,
        allow_modify=allow_modify,
        allow_annotate=allow_annotate,
    )
    if not result.success:
        status = 400 if "passwortgeschützt" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_rechte.pdf")


# ── Signaturprüfung ───────────────────────────────────────────


@router.post("/verify-signatures")
def verify_signatures(
    file: UploadFile = File(...),
    trust_anchors: UploadFile | None = File(
        None, description="Optional: Vertrauensanker (PEM/DER) für die Kettenprüfung"
    ),
):
    """Sync-Endpoint (Threadpool): Kryptoprüfung kann CPU-lastig sein."""
    content = file.file.read()
    _validate_pdf(file, content)
    anchors: bytes | None = None
    if trust_anchors is not None and trust_anchors.filename:
        anchors = trust_anchors.file.read()
        if len(anchors) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Vertrauensanker-Datei zu groß (max 2 MB)")
    result = get_pdf_more().verify_signatures(content, trust_anchors=anchors)
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return result.metadata


# ── Leere Seiten einfügen ─────────────────────────────────────


@router.post("/insert-blank")
async def insert_blank(
    file: UploadFile = File(...),
    after_page: int = Form(0, ge=0, description="0 = vor der ersten Seite"),
    count: int = Form(1, ge=1, le=50),
):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().insert_blank_pages(content, after_page, count=count)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_ergaenzt.pdf")


# ── Prüfakte ──────────────────────────────────────────────────


@router.post("/pruefakte")
async def build_pruefakte(
    files: list[UploadFile] = File(...),
    bates_prefix: str = Form("", description="Optional: Bates-Präfix, z.B. AKTE-"),
    bates_digits: int = Form(6, ge=1, le=12),
):
    """Mehrere PDFs zu einer Prüfakte zusammenführen: ein Lesezeichen pro
    Dokument, optional durchgehende Bates-Nummerierung."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Mindestens zwei Dateien erforderlich")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximal 50 Dateien")
    limits = current_limits()
    total = 0
    file_data: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        total += len(content)
        if total > limits.max_total:
            raise HTTPException(
                status_code=400,
                detail=f"Gesamtgröße überschreitet {limits.max_total_mb} MB",
            )
        _validate_pdf(f, content)
        file_data.append((f.filename or f"datei_{len(file_data)}.pdf", content))
    result = get_pdf_more().build_pruefakte(
        file_data, bates_prefix=bates_prefix, bates_digits=bates_digits
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    meta = result.metadata or {}
    return _pdf_response(
        result.file_content,
        "pruefakte.pdf",
        headers={
            "X-Documents": str(meta.get("documents", 0)),
            "X-Pages": str(meta.get("pages", 0)),
        },
    )


# ── Qualitätsprüfung ──────────────────────────────────────────


@router.post("/quality-check")
def quality_check(file: UploadFile = File(...)):
    """Sync-Endpoint (Threadpool): rendert jede Seite als Mini-Pixmap."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().quality_check(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


# ── Bilder auflisten und ersetzen ─────────────────────────────


@router.post("/images/list")
def list_images(file: UploadFile = File(...)):
    """Alle Bilder mit Vorschau auflisten (Sync-Endpoint: rendert Vorschauen)."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().list_images(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


@router.post("/images/replace")
def replace_image(
    file: UploadFile = File(...),
    xref: int = Form(..., ge=1, description="Referenz aus /images/list"),
    image: UploadFile = File(..., description="Neues Bild (PNG/JPG)"),
):
    content = file.file.read()
    _validate_pdf(file, content)
    if not image.filename or not image.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Bild muss PNG oder JPG sein")
    image_content = image.file.read()
    if len(image_content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu groß (max 20 MB)")
    result = get_pdf_more().replace_image(content, xref, image_content)
    if not result.success:
        status = 404 if "nicht gefunden" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_bild.pdf")


# ── Lokale KI (nur bei konfiguriertem PDFAPP_LLM_URL) ─────────


@router.post("/ai/summarize")
def ai_summarize(file: UploadFile = File(...)):
    """Sync-Endpoint (Threadpool): blockierender HTTP-Call zum lokalen LLM.

    Inhalte werden nur transient an die eigene LLM-Instanz übertragen —
    keine Cloud, keine Speicherung.
    """
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().ai_ask(content, "", mode="summary")
    if not result.success:
        status = 503 if "LLM" in (result.error or "") else 422
        raise HTTPException(status_code=status, detail=result.error)
    return result.metadata


@router.post("/ai/ask")
def ai_ask(
    file: UploadFile = File(...),
    question: str = Form(..., min_length=3, max_length=2000),
):
    """Sync-Endpoint (Threadpool): blockierender HTTP-Call zum lokalen LLM."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().ai_ask(content, question, mode="ask")
    if not result.success:
        status = 503 if "LLM" in (result.error or "") else 422
        raise HTTPException(status_code=status, detail=result.error)
    return result.metadata


@router.post("/ai/translate")
def ai_translate(
    file: UploadFile = File(...),
    target_language: str = Form("Englisch", max_length=60),
):
    """Dokumenttext mit dem lokalen LLM übersetzen (Entwurfsqualität)."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().ai_ask(
        content, "", mode="translate", target_language=target_language
    )
    if not result.success:
        status = 503 if "LLM" in (result.error or "") else 422
        raise HTTPException(status_code=status, detail=result.error)
    return result.metadata


@router.post("/ai/keywords")
def ai_keywords(file: UploadFile = File(...)):
    """Schlagwörter zum Dokument (lokales LLM)."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().ai_ask(content, "", mode="keywords")
    if not result.success:
        status = 503 if "LLM" in (result.error or "") else 422
        raise HTTPException(status_code=status, detail=result.error)
    return result.metadata


@router.post("/ai/outline")
def ai_outline(file: UploadFile = File(...)):
    """Gliederungsvorschlag zum Dokument (lokales LLM)."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_more().ai_ask(content, "", mode="outline")
    if not result.success:
        status = 503 if "LLM" in (result.error or "") else 422
        raise HTTPException(status_code=status, detail=result.error)
    return result.metadata
