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


def _pdf_response(data: bytes, filename: str, headers: dict | None = None):
    h = {"Content-Disposition": f'attachment; filename="{filename}"'}
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
        headers={"Content-Disposition": f'attachment; filename="{_name(file)}.txt"'},
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


@router.post("/to-pdfa")
async def to_pdfa(
    file: UploadFile = File(...),
    level: str = Form("2b", description="PDF/A-Level: 1b, 2b, 3b"),
):
    content = await file.read()
    _validate_pdf(file, content)
    result = get_pdf_extras().convert_pdfa(content, level=level)
    if not result.success:
        status = 503 if "nicht verfügbar" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)
    return _pdf_response(result.file_content, f"{_name(file)}_pdfa.pdf")
