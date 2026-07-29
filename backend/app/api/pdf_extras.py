"""API der erweiterten PDF-Werkzeuge (siehe pdf_extras_service)."""

import io
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import current_limits
from app.services.pdf_extras_service import get_pdf_extras

router = APIRouter(prefix="/pdf-extras", tags=["PDF Extras"])


def _validate_pdf(file: UploadFile, content: bytes):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien erlaubt")
    limits = current_limits()
    if len(content) > limits.max_file:
        raise HTTPException(
            status_code=400, detail=f"Datei zu groß (max {limits.max_file_mb} MB)"
        )


def _safe_name(name: str) -> str:
    """Anführungszeichen/Steuerzeichen aus Dateinamen entfernen (Header-Injection)."""
    import re as _re

    return _re.sub(r'[\r\n"\\;]+', "_", name)[:150] or "datei"


def _pdf_response(data: bytes, filename: str, headers: dict | None = None):
    h = {"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'}
    if headers:
        h.update(headers)
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=h)


def _name(file: UploadFile) -> str:
    return (file.filename or "document").rsplit(".", 1)[0]


@router.get("/status")
async def check_status():
    return get_pdf_extras().check_features()


@router.post("/to-text")
async def pdf_to_text(file: UploadFile = File(...)):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().extract_text(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(_name(file))}.txt"'},
    )


@router.post("/form/fields")
async def form_fields(file: UploadFile = File(...)):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().get_form_fields(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


@router.post("/form/fill")
async def form_fill(
    file: UploadFile = File(...),
    values: str = Form(..., description='JSON-Objekt {"feldname": "wert"}'),
    flatten: bool = Form(False, description="Felder nach dem Ausfüllen einbrennen"),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        values_dict = json.loads(values)
        assert isinstance(values_dict, dict)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="values muss ein JSON-Objekt sein")
    result = get_pdf_extras().fill_form(content, values_dict, flatten=flatten)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_ausgefuellt.pdf",
        headers={"X-Fields-Filled": str((result.metadata or {}).get("filled", 0))},
    )


@router.post("/bates")
async def bates_numbers(
    file: UploadFile = File(...),
    prefix: str = Form("", description="Präfix, z.B. AKTE-"),
    start: int = Form(1),
    digits: int = Form(6, ge=1, le=12),
    position: str = Form("bottom-right"),
    font_size: float = Form(9),
    color: str = Form("#000000"),
):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().add_bates_numbers(
        content,
        prefix=prefix,
        start=start,
        digits=digits,
        position=position,
        font_size=font_size,
        color=color,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    meta = result.metadata or {}
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_bates.pdf",
        headers={"X-Bates-First": str(meta.get("first", "")), "X-Bates-Last": str(meta.get("last", ""))},
    )


@router.post("/redact")
async def redact_by_search(
    file: UploadFile = File(...),
    term: str = Form(..., min_length=1, description="Zu schwärzender Text"),
    match_case: bool = Form(False),
):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().redact_search(content, term, match_case=match_case)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_geschwaerzt.pdf",
        headers={"X-Redactions": str((result.metadata or {}).get("redactions", 0))},
    )


@router.post("/sign-image")
async def sign_with_image(
    file: UploadFile = File(...),
    image: UploadFile = File(..., description="Signatur-/Stempelbild (PNG/JPG)"),
    page: int = Form(1, ge=1),
    x: float = Form(0.6, ge=0, le=1),
    y: float = Form(0.85, ge=0, le=1),
    width: float = Form(0.25, gt=0, le=1, description="Breite relativ zur Seite"),
):
    content = await file.read()
    _validate_pdf(file, content)
    if not image.filename or not image.filename.lower().endswith(
        (".png", ".jpg", ".jpeg")
    ):
        raise HTTPException(status_code=400, detail="Bild muss PNG oder JPG sein")
    image_content = await image.read()
    if len(image_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Bild zu groß (max 10 MB)")
    result = get_pdf_extras().place_image(
        content, image_content, page_num=page, x=x, y=y, width_frac=width
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_signiert.pdf")


@router.post("/edit-text-blocks")
async def edit_text_blocks(
    file: UploadFile = File(...),
    edits: str = Form(
        ...,
        description='JSON-Liste [{"page":1,"bbox":{...},"text":"...","font_size":11,"color":"#000000"}]',
    ),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        edits_list = json.loads(edits)
        assert isinstance(edits_list, list)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="edits muss eine JSON-Liste sein")
    if len(edits_list) > 200:
        raise HTTPException(status_code=400, detail="Maximal 200 Änderungen pro Aufruf")
    result = get_pdf_extras().edit_text_blocks(content, edits_list)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return _pdf_response(
        result.file_content,
        f"{_name(file)}_bearbeitet.pdf",
        headers={"X-Warnings": str(len(result.warnings or []))},
    )


@router.post("/sign-digital")
def sign_digital(
    file: UploadFile = File(...),
    certificate: UploadFile = File(..., description="PKCS#12-Zertifikat (.p12/.pfx)"),
    passphrase: str = Form("", description="Zertifikats-Passwort"),
    reason: str = Form(""),
    location: str = Form(""),
):
    """Zertifikatsbasierte digitale Signatur (PAdES). Zertifikat nur transient.

    Bewusst ein sync-Endpoint (Threadpool): pyhankos sign_pdf nutzt intern
    asyncio.run und darf nicht im laufenden Event-Loop aufgerufen werden.
    """
    content = file.file.read()
    _validate_pdf(file, content)
    if not certificate.filename or not certificate.filename.lower().endswith(
        (".p12", ".pfx")
    ):
        raise HTTPException(status_code=400, detail="Zertifikat muss .p12/.pfx sein")
    p12 = certificate.file.read()
    if len(p12) > 1024 * 1024:
        raise HTTPException(status_code=400, detail="Zertifikatsdatei zu groß")
    result = get_pdf_extras().sign_digital(
        content, p12, passphrase, reason=reason, location=location
    )
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 400
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_signiert.pdf")


@router.post("/scan-optimize")
def scan_optimize(
    file: UploadFile = File(...),
    language: str = Form("deu"),
    deskew: bool = Form(True),
    rotate_pages: bool = Form(True),
    force_ocr: bool = Form(False),
):
    """Sync-Endpoint (Threadpool): OCRmyPDF darf den Event-Loop nicht blockieren."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().scan_optimize(
        content,
        language=language,
        deskew=deskew,
        rotate_pages=rotate_pages,
        force_ocr=force_ocr,
    )
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_optimiert.pdf")


@router.post("/batch")
def batch_apply(
    files: list[UploadFile] = File(...),
    operation: str = Form(..., description="compress | rotate | protect | bates | pdfa"),
    params: str = Form("{}", description="JSON-Objekt mit Operations-Parametern"),
):
    """Eine Operation auf viele Dateien anwenden — Ergebnis als ZIP."""
    if len(files) < 1:
        raise HTTPException(status_code=400, detail="Mindestens eine Datei erforderlich")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximal 50 Dateien")
    try:
        params_dict = json.loads(params)
        assert isinstance(params_dict, dict)
    except (json.JSONDecodeError, AssertionError):
        raise HTTPException(status_code=400, detail="params muss ein JSON-Objekt sein")

    limits = current_limits()
    total = 0
    file_data: list[tuple[str, bytes]] = []
    for f in files:
        content = f.file.read()
        total += len(content)
        if total > limits.max_total:
            raise HTTPException(
                status_code=400,
                detail=f"Gesamtgröße überschreitet {limits.max_total_mb} MB",
            )
        _validate_pdf(f, content)
        file_data.append((f.filename or f"datei_{len(file_data)}.pdf", content))

    result = get_pdf_extras().batch_apply(file_data, operation, params_dict)
    if not result.success:
        raise HTTPException(status_code=422, detail=result.error)
    meta = result.metadata or {}
    return StreamingResponse(
        io.BytesIO(result.file_content),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="batch_ergebnisse.zip"',
            "X-Batch-Ok": str(meta.get("ok", 0)),
            "X-Batch-Failed": str(meta.get("failed", 0)),
        },
    )


@router.post("/to-pdfa")
def to_pdfa(
    file: UploadFile = File(...),
    level: str = Form("2b", description="PDF/A-Level: 1b, 2b, 3b"),
):
    """Sync-Endpoint (Threadpool): Ghostscript darf den Event-Loop nicht blockieren."""
    content = file.file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().convert_pdfa(content, level=level)
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_pdfa.pdf")


# ── Asynchrone Jobs für langlaufende Verarbeitungen ───────────
# OCR, Vergleich und Scan-Optimierung können bei großen Dateien länger dauern
# als Browser-Timeouts erlauben. Ablauf: POST /jobs/<op> → job_id,
# GET /jobs/{id} → Status, GET /jobs/{id}/result → Ergebnis (einmalig,
# danach aus dem RAM gelöscht). Jobs sind an Nutzer-ID bzw. Client-IP gebunden.

from fastapi import Request  # noqa: E402

from app import jobs as job_store  # noqa: E402
from app.ratelimit import tier_key  # noqa: E402


def _job_ocr(content: bytes, language: str):
    from app.services.pdf_editor_service import get_pdf_editor

    result = get_pdf_editor().ocr_pdf(content, language=language)
    if not result.success:
        raise RuntimeError(result.error or "OCR fehlgeschlagen")
    meta = result.metadata or {}
    return result.file_content, {
        "X-Pages-Processed": str(meta.get("pages_processed", 0)),
        "X-Characters-Recognized": str(meta.get("characters_recognized", 0)),
    }


def _job_compare(content_a: bytes, content_b: bytes, include_visual: bool):
    import json as _json

    from app.services.pdf_editor_service import get_pdf_editor

    result = get_pdf_editor().compare_pdfs(content_a, content_b, include_visual)
    if not result.success:
        raise RuntimeError(result.error or "Vergleich fehlgeschlagen")
    return _json.dumps(result.metadata or {}).encode(), {}


def _job_scan(content: bytes, language: str, deskew: bool, rotate: bool, force: bool):
    result = get_pdf_extras().scan_optimize(
        content, language=language, deskew=deskew, rotate_pages=rotate, force_ocr=force
    )
    if not result.success:
        raise RuntimeError(result.error or "Scan-Optimierung fehlgeschlagen")
    return result.file_content, {}


@router.post("/jobs/ocr", status_code=202)
async def start_ocr_job(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("deu"),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        job_id = job_store.submit(
            tier_key(request),
            f"{_name(file)}_ocr.pdf",
            "application/pdf",
            _job_ocr,
            content,
            language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id}


@router.post("/jobs/compare", status_code=202)
async def start_compare_job(
    request: Request,
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    include_visual: bool = Form(True),
):
    content_a = await file_a.read()
    content_b = await file_b.read()
    _validate_pdf(file_a, content_a)
    _validate_pdf(file_b, content_b)
    try:
        job_id = job_store.submit(
            tier_key(request),
            "vergleich.json",
            "application/json",
            _job_compare,
            content_a,
            content_b,
            include_visual,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id}


@router.post("/jobs/scan-optimize", status_code=202)
async def start_scan_job(
    request: Request,
    file: UploadFile = File(...),
    language: str = Form("deu"),
    deskew: bool = Form(True),
    rotate_pages: bool = Form(True),
    force_ocr: bool = Form(False),
):
    content = await file.read()
    _validate_pdf(file, content)
    try:
        job_id = job_store.submit(
            tier_key(request),
            f"{_name(file)}_optimiert.pdf",
            "application/pdf",
            _job_scan,
            content,
            language,
            deskew,
            rotate_pages,
            force_ocr,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
async def job_status(job_id: str, request: Request):
    job = job_store.get(job_id, tier_key(request))
    if job is None:
        raise HTTPException(status_code=404, detail="Auftrag nicht gefunden")
    return {"job_id": job.id, "status": job.status, "error": job.error}


@router.get("/jobs/{job_id}/result")
async def job_result(job_id: str, request: Request):
    job = job_store.take_result(job_id, tier_key(request))
    if job is None:
        raise HTTPException(
            status_code=404, detail="Ergebnis nicht verfügbar (abgeholt, abgelaufen oder nicht fertig)"
        )
    headers = {
        "Content-Disposition": f'attachment; filename="{_safe_name(job.filename)}"',
        **job.headers,
    }
    return StreamingResponse(io.BytesIO(job.content), media_type=job.media_type, headers=headers)
