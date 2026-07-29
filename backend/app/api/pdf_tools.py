"""
API endpoints for PDF & Document Tools.
Provides merge, split, rotate, compress, watermark, convert, and more.
"""

import io
import json

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import current_limits
from app.services.pdf_tools_service import get_pdf_tools

router = APIRouter(prefix="/pdf-tools", tags=["PDF & Dokument Tools"])


# === Schemas ===


class FeaturesResponse(BaseModel):
    pymupdf: bool
    pillow: bool
    python_docx: bool
    libreoffice: bool
    pdf_merge: bool
    pdf_split: bool
    pdf_rotate: bool
    pdf_to_images: bool
    pdf_compress: bool
    pdf_watermark: bool
    images_to_pdf: bool
    pdf_page_ops: bool
    pdf_metadata: bool
    word_to_pdf: bool
    word_merge: bool
    word_diff: bool
    word_metadata: bool
    excel_metadata: bool
    pikepdf: bool
    pdf_protect: bool
    pdf_unlock: bool


class MetadataResponse(BaseModel):
    title: str
    author: str
    subject: str
    keywords: str
    creator: str
    producer: str
    creation_date: str
    modification_date: str
    page_count: int
    file_size: int


class WordDiffResponse(BaseModel):
    file_a: str
    file_b: str
    paragraphs_a: int
    paragraphs_b: int
    similarity: float
    stats: dict
    changes: list[dict]


class WordMetadataResponse(BaseModel):
    title: str
    author: str
    subject: str
    keywords: str
    category: str
    comments: str
    last_modified_by: str
    revision: int | str
    created: str
    modified: str
    last_printed: str


class ExcelMetadataResponse(BaseModel):
    title: str
    creator: str
    subject: str
    keywords: str
    category: str
    description: str
    last_modified_by: str
    revision: str
    created: str
    modified: str
    last_printed: str
    sheet_count: int
    sheet_names: list[str]


# === Helpers ===


def _validate_pdf(file: UploadFile, content: bytes, max_size: int | None = None):
    """Validate a PDF upload."""
    max_size = max_size if max_size is not None else current_limits().max_file
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Nur PDF-Dateien werden unterstützt"
        )
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximum: {max_size // (1024*1024)} MB",
        )


def _validate_docx(file: UploadFile, content: bytes, max_size: int | None = None):
    """Validate a Word upload."""
    max_size = max_size if max_size is not None else current_limits().max_file
    if not file.filename or not file.filename.lower().endswith((".docx", ".doc")):
        raise HTTPException(
            status_code=400, detail="Nur Word-Dateien (.docx) werden unterstützt"
        )
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximum: {max_size // (1024*1024)} MB",
        )


def _safe_name(name: str) -> str:
    """Anführungszeichen/Steuerzeichen aus Dateinamen entfernen (Header-Injection)."""
    import re as _re

    return _re.sub(r'[\r\n"\\;]+', "_", name)[:150] or "datei"


def _pdf_response(
    data: bytes, filename: str, headers: dict | None = None
) -> StreamingResponse:
    """Create a PDF download response."""
    h = {"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'}
    if headers:
        h.update(headers)
    return StreamingResponse(io.BytesIO(data), media_type="application/pdf", headers=h)


def _zip_response(data: bytes, filename: str) -> StreamingResponse:
    """Create a ZIP download response."""
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'},
    )


def _validate_xlsx(file: UploadFile, content: bytes, max_size: int | None = None):
    """Validate an Excel upload."""
    max_size = max_size if max_size is not None else current_limits().max_file
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400, detail="Nur Excel-Dateien (.xlsx) werden unterstützt"
        )
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Datei zu groß. Maximum: {max_size // (1024*1024)} MB",
        )


def _docx_response(data: bytes, filename: str) -> StreamingResponse:
    """Create a DOCX download response."""
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'},
    )


def _xlsx_response(data: bytes, filename: str) -> StreamingResponse:
    """Create an XLSX download response."""
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{_safe_name(filename)}"'},
    )


# === Endpoints ===


@router.get("/status", response_model=FeaturesResponse)
async def check_status():
    """Check which PDF/Document tool features are available."""
    service = get_pdf_tools()
    return FeaturesResponse(**service.check_features())


@router.post("/thumbnails")
async def get_thumbnails(
    file: UploadFile = File(...),
    pages: str | None = Query(
        None, description="Seitennummern (z.B. '1,2,3' oder '1-5')"
    ),
    max_width: int = Query(200, ge=32, le=1400, description="Max Thumbnail-Breite in Pixel"),
):
    """Generate thumbnail previews for PDF pages."""
    content = await file.read()
    _validate_pdf(file, content)

    try:
        import fitz

        from app.services.pdf_tools_service import _parse_page_range

        service = get_pdf_tools()

        # Seiten VOR dem Rendern bestimmen (sonst rendert der Service alles)
        doc = fitz.open(stream=content, filetype="pdf")
        total = doc.page_count
        doc.close()
        page_list = _parse_page_range(pages, total) if pages else list(range(1, total + 1))
        if len(page_list) > 50:
            raise HTTPException(
                status_code=400, detail="Maximal 50 Thumbnails pro Anfrage"
            )

        thumbnails = service.get_thumbnails(content, page_list, max_width)
        thumbnails = {k: v for k, v in thumbnails.items() if int(k) in page_list}

        return {"thumbnails": thumbnails, "count": len(thumbnails)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Fehler bei Thumbnail-Generierung: {e}"
        )


@router.post("/merge")
async def merge_pdfs(
    files: list[UploadFile] = File(..., description="PDF-Dateien zum Zusammenführen"),
    page_selections: str | None = Form(None, description="JSON: {filename: page_spec}"),
):
    """Merge multiple PDF files into one."""
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Mindestens 2 PDFs erforderlich")
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 Dateien")

    file_data = []
    total_size = 0
    for f in files:
        content = await f.read()
        total_size += len(content)
        if total_size > current_limits().max_total:
            raise HTTPException(
                status_code=400, detail=f"Gesamtgröße überschreitet {current_limits().max_total_mb} MB"
            )
        _validate_pdf(f, content)
        file_data.append((f.filename or f"file_{len(file_data)}.pdf", content))

    selections = None
    if page_selections:
        try:
            selections = json.loads(page_selections)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Ungültiges JSON für page_selections"
            )

    service = get_pdf_tools()
    result = service.merge_pdfs(file_data, selections)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return _pdf_response(result.file_content, "zusammengefuehrt.pdf")


@router.post("/split")
async def split_pdf(
    file: UploadFile = File(...),
    mode: str = Form("ranges", description="'ranges' oder 'every_n'"),
    ranges: str | None = Form(
        None, description="Seitenbereiche getrennt durch ; (z.B. '1-3;4-6;7-10')"
    ),
    every_n: int = Form(1, description="Alle N Seiten teilen"),
):
    """Split a PDF into multiple parts."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_tools()
    result = service.split_pdf(content, mode=mode, ranges=ranges, every_n=every_n)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]

    if result.output_format == "zip":
        return _zip_response(result.file_content, f"{original_name}_geteilt.zip")
    return _pdf_response(result.file_content, f"{original_name}_teil.pdf")


@router.post("/rotate")
async def rotate_pages(
    file: UploadFile = File(...),
    rotations: str = Form(
        ..., description="JSON: {page_num: angle} z.B. {'1': 90, '3': 180}"
    ),
):
    """Rotate specific pages in a PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    try:
        rot_dict = json.loads(rotations)
        rot_dict = {int(k): int(v) for k, v in rot_dict.items()}
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Ungültiges JSON für rotations")

    # Validate angles
    for angle in rot_dict.values():
        if angle not in (90, 180, 270):
            raise HTTPException(
                status_code=400, detail="Winkel muss 90, 180 oder 270 sein"
            )

    service = get_pdf_tools()
    result = service.rotate_pages(content, rot_dict)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}_rotiert.pdf")


@router.post("/to-images")
async def pdf_to_images(
    file: UploadFile = File(...),
    pages: str | None = Form(None, description="Seitenbereiche (z.B. '1-5')"),
    format: str = Form("png", description="Bildformat: png oder jpg"),
    dpi: int = Form(150, description="Auflösung in DPI (72-600)"),
):
    """Convert PDF pages to images (PNG/JPG), returned as ZIP."""
    content = await file.read()
    _validate_pdf(file, content)

    dpi = max(72, min(600, dpi))

    service = get_pdf_tools()
    result = service.pdf_to_images(content, pages=pages, fmt=format, dpi=dpi)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _zip_response(result.file_content, f"{original_name}_bilder.zip")


@router.post("/protect")
async def protect_pdf(
    file: UploadFile = File(...),
    password: str = Form(..., min_length=1, description="Öffnen-Passwort"),
    owner_password: str | None = Form(
        None, description="Optionales Besitzer-Passwort (Default: wie Öffnen-Passwort)"
    ),
):
    """Encrypt a PDF with a password (AES-256)."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_tools()
    result = service.protect_pdf(content, password, owner_password)

    if not result.success:
        status = 400 if "passwortgeschützt" in (result.error or "") else 500
        raise HTTPException(status_code=status, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}_geschuetzt.pdf")


@router.post("/unlock")
async def unlock_pdf(
    file: UploadFile = File(...),
    password: str = Form(..., description="Bekanntes Passwort des PDFs"),
):
    """Remove password protection from a PDF using the known password."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_tools()
    result = service.unlock_pdf(content, password)

    if not result.success:
        status = 400 if result.error == "Falsches Passwort" else 500
        raise HTTPException(status_code=status, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}_entsperrt.pdf")


@router.post("/compress")
async def compress_pdf(
    file: UploadFile = File(...),
    quality: str = Form("medium", description="Qualität: low, medium, high"),
):
    """Compress a PDF to reduce file size."""
    content = await file.read()
    _validate_pdf(file, content)

    if quality not in ("low", "medium", "high"):
        quality = "medium"

    service = get_pdf_tools()
    result = service.compress_pdf(content, quality=quality)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    meta = result.metadata or {}
    original_name = (file.filename or "document").rsplit(".", 1)[0]

    return _pdf_response(
        result.file_content,
        f"{original_name}_komprimiert.pdf",
        headers={
            "X-Original-Size": str(meta.get("original_size", 0)),
            "X-Compressed-Size": str(meta.get("compressed_size", 0)),
            "X-Savings-Bytes": str(meta.get("savings_bytes", 0)),
            "X-Compression-Ratio": str(meta.get("compression_ratio", 0)),
        },
    )


@router.post("/watermark")
async def add_watermark(
    file: UploadFile = File(...),
    text: str | None = Form(None, description="Wasserzeichen-Text"),
    image: UploadFile | None = File(None, description="Wasserzeichen-Bild"),
    position: str = Form(
        "center",
        description="Position: center, top-left, top-right, bottom-left, bottom-right",
    ),
    opacity: float = Form(0.3, description="Transparenz (0.0 - 1.0)"),
    rotation: float = Form(-45, description="Text-Rotation in Grad"),
    font_size: float = Form(60, description="Schriftgröße"),
    color: str = Form("#808080", description="Textfarbe als Hex"),
    pages: str | None = Form(None, description="Seitenbereiche (leer = alle)"),
):
    """Add text or image watermark to PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    image_content = None
    if image:
        image_content = await image.read()
        if len(image_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="Wasserzeichen-Bild zu groß (max 10 MB)"
            )

    if not text and not image_content:
        raise HTTPException(
            status_code=400, detail="Text oder Bild für Wasserzeichen erforderlich"
        )

    opacity = max(0.0, min(1.0, opacity))

    service = get_pdf_tools()
    result = service.add_watermark(
        content,
        text=text,
        image_content=image_content,
        position=position,
        opacity=opacity,
        rotation=rotation,
        font_size=font_size,
        color=color,
        pages=pages,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}_wasserzeichen.pdf")


@router.post("/images-to-pdf")
async def images_to_pdf(
    files: list[UploadFile] = File(..., description="Bilddateien"),
    page_size: str = Form("a4", description="Seitengröße: a4, a3, letter, legal"),
    orientation: str = Form(
        "portrait", description="Ausrichtung: portrait oder landscape"
    ),
):
    """Convert multiple images to a single PDF."""
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 Bilder")

    file_data = []
    total_size = 0
    valid_exts = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp")

    for f in files:
        if not f.filename or not f.filename.lower().endswith(valid_exts):
            raise HTTPException(
                status_code=400,
                detail=f"Ungültiges Bildformat: {f.filename}. Erlaubt: {', '.join(valid_exts)}",
            )
        content = await f.read()
        total_size += len(content)
        if total_size > current_limits().max_total:
            raise HTTPException(
                status_code=400,
                detail=f"Gesamtgröße überschreitet {current_limits().max_total_mb} MB",
            )
        file_data.append((f.filename, content))

    service = get_pdf_tools()
    result = service.images_to_pdf(
        file_data, page_size=page_size, orientation=orientation
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return _pdf_response(result.file_content, "bilder_zu_pdf.pdf")


@router.post("/page-operations")
async def page_operations(
    file: UploadFile = File(...),
    new_order: str = Form(
        ..., description="JSON-Array mit Seitenreihenfolge z.B. [3,1,2]"
    ),
):
    """Reorder or delete pages in a PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    try:
        order = json.loads(new_order)
        if not isinstance(order, list):
            raise ValueError
        order = [int(p) for p in order]
    except (json.JSONDecodeError, ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="new_order muss ein JSON-Array von Seitennummern sein",
        )

    service = get_pdf_tools()
    result = service.page_operations(content, order)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}_bearbeitet.pdf")


@router.post("/metadata/read")
async def read_metadata(
    file: UploadFile = File(...),
):
    """Read PDF metadata."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_tools()
    result = service.get_metadata(content)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return MetadataResponse(**result.metadata)


@router.post("/metadata")
async def set_metadata(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    subject: str | None = Form(None),
    keywords: str | None = Form(None),
    creation_date: str | None = Form(
        None, description="Erstelldatum als ISO-String (z.B. 2026-01-15T10:30:00)"
    ),
    modification_date: str | None = Form(
        None, description="Änderungsdatum als ISO-String (z.B. 2026-01-15T10:30:00)"
    ),
    creator: str | None = Form(None, description="Ersteller-Anwendung"),
    producer: str | None = Form(None, description="PDF-Erzeuger"),
):
    """Set PDF metadata fields (including dates) and return the updated PDF."""
    content = await file.read()
    _validate_pdf(file, content)

    service = get_pdf_tools()
    result = service.set_metadata(
        content,
        title=title,
        author=author,
        subject=subject,
        keywords=keywords,
        creation_date=creation_date,
        modification_date=modification_date,
        creator=creator,
        producer=producer,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}_meta.pdf")


@router.post("/word-to-pdf")
async def word_to_pdf(
    file: UploadFile = File(...),
):
    """Convert a Word document (.docx) to PDF."""
    content = await file.read()
    _validate_docx(file, content)

    service = get_pdf_tools()
    result = service.word_to_pdf(content, filename=file.filename or "document.docx")

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _pdf_response(result.file_content, f"{original_name}.pdf")


@router.post("/word-merge")
async def word_merge(
    files: list[UploadFile] = File(..., description="Word-Dateien zum Zusammenführen"),
    add_page_break: bool = Form(True, description="Seitenumbruch zwischen Dokumenten"),
):
    """Merge multiple Word documents into one."""
    if len(files) < 2:
        raise HTTPException(
            status_code=400, detail="Mindestens 2 Dokumente erforderlich"
        )
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 Dateien")

    file_data = []
    total_size = 0
    for f in files:
        content = await f.read()
        total_size += len(content)
        if total_size > current_limits().max_total:
            raise HTTPException(
                status_code=400,
                detail=f"Gesamtgröße überschreitet {current_limits().max_total_mb} MB",
            )
        _validate_docx(f, content)
        file_data.append((f.filename or f"doc_{len(file_data)}.docx", content))

    service = get_pdf_tools()
    result = service.merge_word_docs(file_data, add_page_break=add_page_break)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return _docx_response(result.file_content, "zusammengefuehrt.docx")


@router.post("/word-diff")
async def word_diff(
    file_a: UploadFile = File(..., description="Erstes Word-Dokument"),
    file_b: UploadFile = File(..., description="Zweites Word-Dokument"),
):
    """Compare two Word documents and return differences."""
    content_a = await file_a.read()
    content_b = await file_b.read()
    _validate_docx(file_a, content_a)
    _validate_docx(file_b, content_b)

    service = get_pdf_tools()
    result = service.diff_word_docs(
        content_a,
        content_b,
        file_a_name=file_a.filename or "Dokument A",
        file_b_name=file_b.filename or "Dokument B",
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return WordDiffResponse(**result.metadata)


@router.post("/word-metadata/read")
async def read_word_metadata(
    file: UploadFile = File(...),
):
    """Read Word document metadata."""
    content = await file.read()
    _validate_docx(file, content)

    service = get_pdf_tools()
    result = service.get_word_metadata(content)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return WordMetadataResponse(**result.metadata)


@router.post("/word-metadata")
async def set_word_metadata(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    author: str | None = Form(None),
    subject: str | None = Form(None),
    keywords: str | None = Form(None),
    category: str | None = Form(None),
    comments: str | None = Form(None),
    last_modified_by: str | None = Form(None),
    modified: str | None = Form(
        None, description="Änderungsdatum als ISO-String (z.B. 2026-01-15T10:30:00)"
    ),
    created: str | None = Form(
        None, description="Erstelldatum als ISO-String (z.B. 2026-01-15T10:30:00)"
    ),
):
    """Set Word document metadata and return updated file."""
    content = await file.read()
    _validate_docx(file, content)

    service = get_pdf_tools()
    result = service.set_word_metadata(
        content,
        title=title,
        author=author,
        subject=subject,
        keywords=keywords,
        category=category,
        comments=comments,
        last_modified_by=last_modified_by,
        modified=modified,
        created=created,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _docx_response(result.file_content, f"{original_name}_meta.docx")


@router.post("/excel-metadata/read")
async def read_excel_metadata(
    file: UploadFile = File(...),
):
    """Read Excel document metadata."""
    content = await file.read()
    _validate_xlsx(file, content)

    service = get_pdf_tools()
    result = service.get_excel_metadata(content)

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    return ExcelMetadataResponse(**result.metadata)


@router.post("/excel-metadata")
async def set_excel_metadata(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    creator: str | None = Form(None),
    subject: str | None = Form(None),
    keywords: str | None = Form(None),
    category: str | None = Form(None),
    description: str | None = Form(None),
    last_modified_by: str | None = Form(None),
    modified: str | None = Form(
        None, description="Änderungsdatum als ISO-String (z.B. 2026-01-15T10:30:00)"
    ),
    created: str | None = Form(
        None, description="Erstelldatum als ISO-String (z.B. 2026-01-15T10:30:00)"
    ),
):
    """Set Excel document metadata and return updated file."""
    content = await file.read()
    _validate_xlsx(file, content)

    service = get_pdf_tools()
    result = service.set_excel_metadata(
        content,
        title=title,
        creator=creator,
        subject=subject,
        keywords=keywords,
        category=category,
        description=description,
        last_modified_by=last_modified_by,
        modified=modified,
        created=created,
    )

    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    original_name = (file.filename or "document").rsplit(".", 1)[0]
    return _xlsx_response(result.file_content, f"{original_name}_meta.xlsx")
