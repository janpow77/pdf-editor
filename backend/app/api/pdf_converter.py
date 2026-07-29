"""
API endpoints for PDF Converter.
Provides PDF to Word/Excel conversion with page selection and table extraction.
"""

import io

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.pdf_converter_service import get_pdf_converter

router = APIRouter(prefix="/pdf-convert", tags=["PDF Converter"])


# === Schemas ===


class PdfInfoResponse(BaseModel):
    """Response with PDF file information."""

    page_count: int
    pages: list[dict]
    metadata: dict
    file_size: int


class TablePreview(BaseModel):
    """Preview of a table from PDF."""

    page: int
    table_index: int
    total_rows: int
    total_columns: int
    headers: list[str]
    preview_rows: list[list]
    has_more: bool


class TablePreviewResponse(BaseModel):
    """Response with table previews."""

    success: bool
    tables: list[TablePreview]
    total_tables: int
    pages_processed: list[int]
    warnings: list[str] = []
    error: str | None = None


class ConversionRequest(BaseModel):
    """Request for PDF conversion."""

    pages: str | None = Field(None, description="Page range (e.g., '1-5,10' or 'all')")
    use_ocr: bool = Field(False, description="Use OCR for scanned documents")
    ocr_language: str = Field("deu", description="OCR language code")
    consolidate_tables: bool = Field(
        True, description="Merge tables from multiple pages"
    )


class DependenciesResponse(BaseModel):
    """Response with available dependencies."""

    pymupdf: bool
    tabula: bool
    pandas: bool
    ocr: bool
    openpyxl: bool


# === Endpoints ===


@router.get("/status", response_model=DependenciesResponse)
async def check_status():
    """Check which PDF conversion features are available."""
    service = get_pdf_converter()
    deps = service.check_dependencies()
    return DependenciesResponse(**deps)


@router.post("/info", response_model=PdfInfoResponse)
async def get_pdf_info(
    file: UploadFile = File(...)
):
    """
    Get information about a PDF file including page count and metadata.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt",
        )

    content = await file.read()

    if len(content) > 100 * 1024 * 1024:  # 100 MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Datei zu groß. Maximum: 100 MB",
        )

    try:
        service = get_pdf_converter()
        info = service.get_pdf_info(content)
        return PdfInfoResponse(**info)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler beim Lesen der PDF: {str(e)}",
        )


@router.post("/thumbnails")
async def get_thumbnails(
    file: UploadFile = File(...),
    pages: str | None = Query(
        None, description="Page numbers (e.g., '1,2,3' or '1-5')"
    ),
    max_width: int = Query(200, description="Maximum thumbnail width"),
):
    """
    Generate thumbnail images for PDF pages.
    Returns a dict mapping page numbers to base64-encoded PNG images.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt",
        )

    content = await file.read()

    try:
        service = get_pdf_converter()

        # Parse page specification
        page_list = None
        if pages:
            info = service.get_pdf_info(content)
            page_list = service.parse_page_range(pages, info["page_count"])

        thumbnails = service.get_page_thumbnails(content, page_list, max_width)

        return {"thumbnails": thumbnails, "count": len(thumbnails)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei Thumbnail-Generierung: {str(e)}",
        )


@router.post("/preview-tables", response_model=TablePreviewResponse)
async def preview_tables(
    file: UploadFile = File(...),
    pages: str | None = Query(None, description="Page range (e.g., '69-72')"),
    max_rows: int = Query(10, description="Maximum rows per table in preview"),
):
    """
    Preview tables in the PDF before extraction.
    Shows the first few rows of each detected table.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt",
        )

    content = await file.read()

    try:
        service = get_pdf_converter()

        # Parse page specification
        page_list = None
        if pages:
            info = service.get_pdf_info(content)
            page_list = service.parse_page_range(pages, info["page_count"])

        result = service.get_table_preview(content, page_list, max_rows)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Vorschau fehlgeschlagen",
            )

        return TablePreviewResponse(
            success=True,
            tables=[TablePreview(**t) for t in result.preview_data.get("tables", [])],
            total_tables=result.preview_data.get("total_tables", 0),
            pages_processed=result.preview_data.get("pages_processed", []),
            warnings=result.warnings,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fehler bei Tabellenvorschau: {str(e)}",
        )


@router.post("/to-word")
async def convert_to_word(
    file: UploadFile = File(...),
    pages: str | None = Query(None, description="Page range (e.g., '1-5,10')"),
    use_ocr: bool = Query(False, description="Use OCR for scanned documents"),
    ocr_language: str = Query("deu", description="OCR language (deu, eng, etc.)"),
):
    """
    Convert PDF pages to Word document.

    Supports:
    - Page range selection
    - OCR for scanned documents
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt",
        )

    content = await file.read()

    try:
        service = get_pdf_converter()

        # Parse page specification
        page_list = None
        if pages:
            info = service.get_pdf_info(content)
            page_list = service.parse_page_range(pages, info["page_count"])

        result = service.convert_to_word(content, page_list, use_ocr, ocr_language)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error or "Konvertierung fehlgeschlagen",
            )

        # Create filename
        original_name = file.filename.rsplit(".", 1)[0] if file.filename else "document"
        output_filename = f"{original_name}_converted.docx"

        return StreamingResponse(
            io.BytesIO(result.file_content),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "X-Warnings": "; ".join(result.warnings) if result.warnings else "",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Konvertierung fehlgeschlagen: {str(e)}",
        )


@router.post("/to-excel")
async def convert_to_excel(
    file: UploadFile = File(...),
    pages: str | None = Query(None, description="Page range (e.g., '69-72')"),
    consolidate: bool = Query(True, description="Merge tables from multiple pages"),
):
    """
    Extract tables from PDF and convert to Excel.

    Supports:
    - Page range selection
    - Multi-page table consolidation
    - Automatic header detection
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt",
        )

    content = await file.read()

    try:
        service = get_pdf_converter()

        # Parse page specification
        page_list = None
        if pages:
            info = service.get_pdf_info(content)
            page_list = service.parse_page_range(pages, info["page_count"])

        result = service.extract_tables(content, page_list, consolidate)

        if not result.success:
            # Include table data in error response for partial results
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": result.error or "Extraktion fehlgeschlagen",
                    "warnings": result.warnings,
                    "tables_found": len(result.tables),
                },
            )

        # Create filename
        original_name = file.filename.rsplit(".", 1)[0] if file.filename else "tables"
        output_filename = f"{original_name}_tables.xlsx"

        return StreamingResponse(
            io.BytesIO(result.file_content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="{output_filename}"',
                "X-Warnings": "; ".join(result.warnings) if result.warnings else "",
                "X-Tables-Count": str(len(result.tables)),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraktion fehlgeschlagen: {str(e)}",
        )


@router.post("/to-excel/preview")
async def preview_excel_extraction(
    file: UploadFile = File(...),
    pages: str | None = Query(None, description="Page range"),
    consolidate: bool = Query(True, description="Preview with consolidation"),
):
    """
    Preview what the Excel extraction will look like.
    Returns table structure and sample data without generating the file.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nur PDF-Dateien werden unterstützt",
        )

    content = await file.read()

    try:
        service = get_pdf_converter()

        # Parse page specification
        page_list = None
        if pages:
            info = service.get_pdf_info(content)
            page_list = service.parse_page_range(pages, info["page_count"])

        result = service.get_table_preview(content, page_list, max_rows=20)

        # Calculate consolidated preview if requested
        consolidated_preview = None
        if consolidate and result.preview_data:
            tables = result.preview_data.get("tables", [])
            if len(tables) > 1:
                # Check if tables can be consolidated
                col_counts = [t["total_columns"] for t in tables]
                if len(set(col_counts)) == 1:
                    total_rows = sum(t["total_rows"] for t in tables)
                    consolidated_preview = {
                        "can_consolidate": True,
                        "total_rows": total_rows,
                        "total_columns": col_counts[0],
                        "source_tables": len(tables),
                        "source_pages": list({t["page"] for t in tables}),
                    }
                else:
                    consolidated_preview = {
                        "can_consolidate": False,
                        "reason": "Unterschiedliche Spaltenanzahl",
                        "column_counts": col_counts,
                    }

        return {
            "success": result.success,
            "tables": (
                result.preview_data.get("tables", []) if result.preview_data else []
            ),
            "total_tables": (
                result.preview_data.get("total_tables", 0) if result.preview_data else 0
            ),
            "pages_processed": (
                result.preview_data.get("pages_processed", [])
                if result.preview_data
                else []
            ),
            "consolidation_preview": consolidated_preview,
            "warnings": result.warnings,
            "error": result.error,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vorschau fehlgeschlagen: {str(e)}",
        )
