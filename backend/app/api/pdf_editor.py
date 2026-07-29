"""
API endpoints for PDF Editor.
Visual PDF editing: TOC, annotations, page numbers, headers/footers,
text insert/replace, OCR, PDF comparison, flatten.
"""

import io
import json

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from app.services.pdf_editor_service import get_pdf_editor

router = APIRouter(prefix="/pdf-editor", tags=["PDF Editor"])

from app.api.deps import current_limits


def _validate_pdf(file: UploadFile, content: bytes):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien erlaubt")
    limits = current_limits()
    if len(content) > limits.max_file:
        raise HTTPException(
            status_code=400, detail=f"Datei zu gross (max {limits.max_file_mb} MB)"
        )


def _safe_name(name: str) -> str:
    """Anführungszeichen/Steuerzeichen aus Dateinamen entfernen (Header-Injection)."""
    import re as _re

    return _re.sub(r'[\r\n"\\;]+', "_", name)[:150] or "datei"


def _pdf_response(data: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'},
    )


# ── TOC Endpoints ─────────────────────────────────────────


@router.post("/toc/read")
async def read_toc(
    file: UploadFile = File(...),
):
    """Read existing bookmarks/TOC from PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.get_toc(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


@router.post("/toc/write")
async def write_toc(
    file: UploadFile = File(...),
    entries: str = Form(..., description="JSON array of {level, title, page}"),
):
    """Write bookmarks/TOC to PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    try:
        toc_entries = json.loads(entries)
        if not isinstance(toc_entries, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Ungueltiges JSON fuer entries")

    service = get_pdf_editor()
    result = service.set_toc(content, toc_entries)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{name}_toc.pdf")


@router.post("/toc/auto-detect")
async def auto_detect_toc(
    file: UploadFile = File(...),
    h1_min_size: float = Form(18.0, description="Mindest-Schriftgroesse fuer H1"),
    h2_min_size: float = Form(14.0, description="Mindest-Schriftgroesse fuer H2"),
    h3_min_size: float = Form(12.0, description="Mindest-Schriftgroesse fuer H3"),
):
    """Auto-detect TOC entries from font sizes."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.auto_detect_toc(content, h1_min_size, h2_min_size, h3_min_size)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


# ── Text Blocks ───────────────────────────────────────────


@router.post("/text-blocks")
async def get_text_blocks(
    file: UploadFile = File(...),
    page: int = Form(1, description="Seitennummer (1-basiert)"),
):
    """Get text blocks with font info for text-edit mode."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.get_page_text_blocks(content, page)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


# ── Annotations ───────────────────────────────────────────


@router.post("/annotations")
async def apply_annotations(
    file: UploadFile = File(...),
    annotations: str = Form(..., description="JSON array of annotation objects"),
):
    """Apply annotations to PDF and return modified PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    try:
        ann_list = json.loads(annotations)
        if not isinstance(ann_list, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Ungueltiges JSON fuer annotations")

    service = get_pdf_editor()
    result = service.apply_annotations(content, ann_list)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{name}_annotiert.pdf")


# ── Page Numbers ──────────────────────────────────────────


@router.post("/page-numbers")
async def add_page_numbers(
    file: UploadFile = File(...),
    format_str: str = Form(
        "Seite {page} von {total}", description="Format mit {page}, {total}, {date}"
    ),
    position: str = Form("bottom-center", description="Position der Seitenzahl"),
    font_size: float = Form(10),
    color: str = Form("#000000"),
    start_page: int = Form(1, description="Ab welcher Seite nummerieren"),
    start_number: int = Form(1, description="Startnummer"),
):
    """Add page numbers to PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.add_page_numbers(
        content,
        format_str=format_str,
        position=position,
        font_size=font_size,
        color=color,
        start_page=start_page,
        start_number=start_number,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{name}_nummeriert.pdf")


# ── Header / Footer ──────────────────────────────────────


@router.post("/header-footer")
async def add_header_footer(
    file: UploadFile = File(...),
    header_left: str = Form(""),
    header_center: str = Form(""),
    header_right: str = Form(""),
    footer_left: str = Form(""),
    footer_center: str = Form(""),
    footer_right: str = Form(""),
    font_size: float = Form(9),
    color: str = Form("#666666"),
    start_page: int = Form(1),
):
    """Add header and/or footer to PDF pages."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.add_header_footer(
        content,
        header_left=header_left,
        header_center=header_center,
        header_right=header_right,
        footer_left=footer_left,
        footer_center=footer_center,
        footer_right=footer_right,
        font_size=font_size,
        color=color,
        start_page=start_page,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{name}_kopfzeilen.pdf")


# ── Text Insert ──────────────────────────────────────────


@router.post("/text/insert")
async def insert_text(
    file: UploadFile = File(...),
    page: int = Form(1),
    x: float = Form(..., description="X-Position (0-1 normalisiert)"),
    y: float = Form(..., description="Y-Position (0-1 normalisiert)"),
    text: str = Form(...),
    font_size: float = Form(12),
    color: str = Form("#000000"),
    font_name: str = Form("helv"),
):
    """Insert text at position on a PDF page."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.insert_text(
        content,
        page_num=page,
        x=x,
        y=y,
        text=text,
        font_size=font_size,
        color=color,
        font_name=font_name,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{name}_text.pdf")


# ── Search & Replace ─────────────────────────────────────


@router.post("/text/search")
async def search_text(
    file: UploadFile = File(...),
    search: str = Form(..., description="Suchtext"),
    match_case: bool = Form(True),
):
    """Search for text in PDF, return occurrences with positions."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.search_text(content, search, match_case=match_case)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


@router.post("/text/replace")
async def replace_text(
    file: UploadFile = File(...),
    search: str = Form(..., description="Suchtext"),
    replace: str = Form(..., description="Ersetzungstext"),
    match_case: bool = Form(True),
    pages: str | None = Form(None, description="JSON array of page numbers"),
    max_replacements: int = Form(0, description="Max Ersetzungen (0=alle)"),
):
    """Search and replace text in PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    page_list = None
    if pages:
        try:
            page_list = json.loads(pages)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Ungueltiges JSON fuer pages")

    service = get_pdf_editor()
    result = service.search_replace_text(
        content,
        search=search,
        replace=replace,
        pages=page_list,
        match_case=match_case,
        max_replacements=max_replacements,
    )
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    resp = _pdf_response(result.file_content, f"{name}_ersetzt.pdf")
    meta = result.metadata or {}
    resp.headers["X-Replacements"] = str(meta.get("replacements", 0))
    return resp


# ── OCR ──────────────────────────────────────────────────


@router.post("/ocr")
async def ocr_pdf(
    file: UploadFile = File(...),
    language: str = Form("deu", description="Sprache: deu, eng, deu+eng"),
):
    """Make scanned PDF searchable using OCR."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.ocr_pdf(content, language=language)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    resp = _pdf_response(result.file_content, f"{name}_ocr.pdf")
    meta = result.metadata or {}
    resp.headers["X-Pages-Processed"] = str(meta.get("pages_processed", 0))
    resp.headers["X-Characters-Recognized"] = str(meta.get("characters_recognized", 0))
    return resp


# ── PDF Compare ──────────────────────────────────────────


@router.post("/compare")
async def compare_pdfs(
    file_a: UploadFile = File(..., description="PDF Version A"),
    file_b: UploadFile = File(..., description="PDF Version B"),
    include_visual: bool = Form(True, description="Visual-Diff einbeziehen"),
):
    """Compare two PDF files (text diff + visual diff)."""
    content_a = await file_a.read()
    content_b = await file_b.read()
    _validate_pdf(file_a, content_a)
    _validate_pdf(file_b, content_b)

    service = get_pdf_editor()
    result = service.compare_pdfs(content_a, content_b, include_visual=include_visual)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    return result.metadata


# ── Flatten ──────────────────────────────────────────────


@router.post("/flatten")
async def flatten_annotations(
    file: UploadFile = File(...),
):
    """Flatten (burn in) all annotations into PDF content."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_editor()
    result = service.flatten_annotations(content)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{name}_flatten.pdf")
