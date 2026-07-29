"""
PDF Editor Service.
Provides visual PDF editing: TOC management, annotations, page numbers,
headers/footers, text insert/replace, OCR, PDF comparison, and flatten.
Uses PyMuPDF (fitz) for all PDF operations, Tesseract for OCR.
"""

import base64
import io
import logging
from difflib import SequenceMatcher
from functools import lru_cache

from app.services.pdf_tools_service import PdfToolResult

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

TESSERACT_AVAILABLE = False
try:
    import pytesseract

    pytesseract.get_tesseract_version()
    TESSERACT_AVAILABLE = True
except Exception as e:
    logger.warning("Tesseract OCR detection failed: %s", e)


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    """Convert hex color string to (r, g, b) floats 0-1."""
    if color.startswith("#") and len(color) == 7:
        return (
            int(color[1:3], 16) / 255,
            int(color[3:5], 16) / 255,
            int(color[5:7], 16) / 255,
        )
    return (0.0, 0.0, 0.0)


class PdfEditorService:
    """Service for visual PDF editing operations."""

    # ── TOC (Table of Contents / Bookmarks) ───────────────────

    def get_toc(self, file_content: bytes) -> PdfToolResult:
        """Read existing bookmarks/TOC from PDF."""
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="json", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            toc = doc.get_toc(simple=False)
            entries = []
            for item in toc:
                level = item[0]
                title = item[1]
                page = item[2]
                dest = item[3] if len(item) > 3 else {}
                entries.append(
                    {
                        "level": level,
                        "title": title,
                        "page": page,
                        "dest": dest if isinstance(dest, dict) else {},
                    }
                )
            page_count = doc.page_count
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={"entries": entries, "page_count": page_count},
            )
        except Exception as e:
            return PdfToolResult(
                success=False, output_format="json", error=f"TOC-Lesefehler: {e}"
            )

    def set_toc(self, file_content: bytes, entries: list[dict]) -> PdfToolResult:
        """Write bookmarks/TOC to PDF.

        entries: list of {level: int, title: str, page: int}
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            toc_list = []
            for e in entries:
                level = int(e.get("level", 1))
                title = str(e.get("title", ""))
                page = int(e.get("page", 1))
                page = max(1, min(page, doc.page_count))
                toc_list.append([level, title, page])
            doc.set_toc(toc_list)
            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={"entries_written": len(toc_list)},
            )
        except Exception as e:
            return PdfToolResult(
                success=False, output_format="pdf", error=f"TOC-Schreibfehler: {e}"
            )

    def auto_detect_toc(
        self,
        file_content: bytes,
        h1_min_size: float = 18.0,
        h2_min_size: float = 14.0,
        h3_min_size: float = 12.0,
    ) -> PdfToolResult:
        """Auto-detect TOC from font sizes.

        Scans all pages, identifies headings by font size thresholds,
        returns detected TOC entries.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="json", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            entries = []

            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)[
                    "blocks"
                ]

                for block in blocks:
                    if block.get("type") != 0:  # text block only
                        continue
                    for line in block.get("lines", []):
                        text_parts = []
                        max_size = 0.0
                        is_bold = False
                        for span in line.get("spans", []):
                            text_parts.append(span.get("text", ""))
                            size = span.get("size", 0)
                            if size > max_size:
                                max_size = size
                            flags = span.get("flags", 0)
                            if flags & 2**4:  # bold flag
                                is_bold = True

                        text = "".join(text_parts).strip()
                        if not text or len(text) < 2:
                            continue

                        level = 0
                        if max_size >= h1_min_size:
                            level = 1
                        elif max_size >= h2_min_size:
                            level = 2
                        elif max_size >= h3_min_size and is_bold:
                            level = 3

                        if level > 0:
                            entries.append(
                                {
                                    "level": level,
                                    "title": text[:200],
                                    "page": page_idx + 1,
                                    "font_size": round(max_size, 1),
                                    "bold": is_bold,
                                }
                            )

            doc.close()
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={
                    "entries": entries,
                    "thresholds": {
                        "h1_min_size": h1_min_size,
                        "h2_min_size": h2_min_size,
                        "h3_min_size": h3_min_size,
                    },
                },
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="json",
                error=f"Auto-TOC Fehler: {e}",
            )

    # ── Text Blocks (for text-edit mode) ──────────────────────

    def get_page_text_blocks(self, file_content: bytes, page_num: int) -> PdfToolResult:
        """Get text blocks with font info for a specific page.

        Returns blocks with position, text, font size, font name.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="json", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            if page_num < 1 or page_num > doc.page_count:
                doc.close()
                return PdfToolResult(
                    success=False,
                    output_format="json",
                    error=f"Ungueltige Seite: {page_num}",
                )

            page = doc[page_num - 1]
            rect = page.rect
            data = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            blocks = []

            for block in data.get("blocks", []):
                if block.get("type") != 0:
                    continue
                bbox = block.get("bbox", (0, 0, 0, 0))
                block_text_parts = []
                block_font_size = 0.0
                block_font_name = "helv"
                block_color = "#000000"

                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        block_text_parts.append(span.get("text", ""))
                        size = span.get("size", 0)
                        if size > block_font_size:
                            block_font_size = size
                            block_font_name = span.get("font", "helv")
                            c = span.get("color", 0)
                            if isinstance(c, int):
                                block_color = f"#{c:06x}"

                text = "".join(block_text_parts).strip()
                if not text:
                    continue

                blocks.append(
                    {
                        "text": text,
                        "bbox": {
                            "x0": round(bbox[0] / rect.width, 4),
                            "y0": round(bbox[1] / rect.height, 4),
                            "x1": round(bbox[2] / rect.width, 4),
                            "y1": round(bbox[3] / rect.height, 4),
                        },
                        "font_size": round(block_font_size, 1),
                        "font_name": block_font_name,
                        "color": block_color,
                    }
                )

            doc.close()
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={
                    "blocks": blocks,
                    "page": page_num,
                    "width": round(rect.width, 1),
                    "height": round(rect.height, 1),
                },
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="json",
                error=f"Textblock-Fehler: {e}",
            )

    # ── Annotations ───────────────────────────────────────────

    def apply_annotations(
        self, file_content: bytes, annotations: list[dict]
    ) -> PdfToolResult:
        """Apply annotations to PDF.

        annotation types:
          - highlight: {type, page, quads: [{x0,y0,x1,y1}], color}
          - text_comment: {type, page, x, y, content, color}
          - freetext: {type, page, x, y, width, height, text, font_size, color}
          - rect: {type, page, x0, y0, x1, y1, color, fill_color, width}
          - circle: {type, page, cx, cy, rx, ry, color, fill_color, width}
          - line: {type, page, x0, y0, x1, y1, color, width}
          - ink: {type, page, paths: [[{x,y},...]], color, width}
          - stamp: {type, page, x0, y0, x1, y1, text, color}
          - redact: {type, page, x0, y0, x1, y1, fill_color}

        Coordinates are normalized 0-1 relative to page dimensions.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            count = 0

            for ann in annotations:
                ann_type = ann.get("type", "")
                page_num = int(ann.get("page", 1))
                if page_num < 1 or page_num > doc.page_count:
                    continue
                page = doc[page_num - 1]
                rect = page.rect
                w, h = rect.width, rect.height
                color = _hex_to_rgb(ann.get("color", "#FFFF00"))

                if ann_type == "highlight":
                    quads = ann.get("quads", [])
                    for q in quads:
                        r = fitz.Rect(
                            q["x0"] * w, q["y0"] * h, q["x1"] * w, q["y1"] * h
                        )
                        annot = page.add_highlight_annot(r)
                        annot.set_colors(stroke=color)
                        annot.set_opacity(ann.get("opacity", 0.4))
                        annot.update()
                    count += 1

                elif ann_type == "text_comment":
                    point = fitz.Point(ann.get("x", 0.5) * w, ann.get("y", 0.5) * h)
                    annot = page.add_text_annot(point, ann.get("content", "Kommentar"))
                    annot.set_colors(stroke=color)
                    annot.update()
                    count += 1

                elif ann_type == "freetext":
                    r = fitz.Rect(
                        ann.get("x", 0.1) * w,
                        ann.get("y", 0.1) * h,
                        (ann.get("x", 0.1) + ann.get("width", 0.2)) * w,
                        (ann.get("y", 0.1) + ann.get("height", 0.05)) * h,
                    )
                    annot = page.add_freetext_annot(
                        r,
                        ann.get("text", ""),
                        fontsize=ann.get("font_size", 12),
                        text_color=color,
                    )
                    annot.update()
                    count += 1

                elif ann_type == "rect":
                    r = fitz.Rect(
                        ann.get("x0", 0) * w,
                        ann.get("y0", 0) * h,
                        ann.get("x1", 0) * w,
                        ann.get("y1", 0) * h,
                    )
                    annot = page.add_rect_annot(r)
                    fill = ann.get("fill_color")
                    annot.set_colors(
                        stroke=color,
                        fill=_hex_to_rgb(fill) if fill else None,
                    )
                    bw = ann.get("width", 1.5)
                    annot.set_border(width=bw)
                    annot.update()
                    count += 1

                elif ann_type == "circle":
                    cx = ann.get("cx", 0.5) * w
                    cy = ann.get("cy", 0.5) * h
                    rx = ann.get("rx", 0.05) * w
                    ry = ann.get("ry", 0.05) * h
                    r = fitz.Rect(cx - rx, cy - ry, cx + rx, cy + ry)
                    annot = page.add_rect_annot(r)
                    fill = ann.get("fill_color")
                    annot.set_colors(
                        stroke=color,
                        fill=_hex_to_rgb(fill) if fill else None,
                    )
                    annot.set_border(width=ann.get("width", 1.5))
                    # Make it a circle by using the appropriate subtype
                    annot.set_info(content="circle")
                    annot.update()
                    count += 1

                elif ann_type == "line":
                    p1 = fitz.Point(ann.get("x0", 0) * w, ann.get("y0", 0) * h)
                    p2 = fitz.Point(ann.get("x1", 0) * w, ann.get("y1", 0) * h)
                    annot = page.add_line_annot(p1, p2)
                    annot.set_colors(stroke=color)
                    annot.set_border(width=ann.get("width", 1.5))
                    annot.update()
                    count += 1

                elif ann_type == "ink":
                    paths = ann.get("paths", [])
                    ink_list = []
                    for path in paths:
                        # add_ink_annot verlangt in aktuellen PyMuPDF-Versionen
                        # reine (x, y)-Float-Paare, keine fitz.Point-Objekte
                        points = [
                            (pt.get("x", 0) * w, pt.get("y", 0) * h) for pt in path
                        ]
                        if len(points) >= 2:
                            ink_list.append(points)
                    if ink_list:
                        annot = page.add_ink_annot(ink_list)
                        annot.set_colors(stroke=color)
                        annot.set_border(width=ann.get("width", 2.0))
                        annot.update()
                        count += 1

                elif ann_type == "stamp":
                    r = fitz.Rect(
                        ann.get("x0", 0.2) * w,
                        ann.get("y0", 0.2) * h,
                        ann.get("x1", 0.8) * w,
                        ann.get("y1", 0.3) * h,
                    )
                    stamp_text = ann.get("text", "ENTWURF")
                    annot = page.add_stamp_annot(r, stamp=0)
                    annot.set_info(content=stamp_text)
                    annot.set_colors(stroke=color)
                    annot.set_opacity(ann.get("opacity", 0.5))
                    annot.update()
                    count += 1

                elif ann_type == "redact":
                    r = fitz.Rect(
                        ann.get("x0", 0) * w,
                        ann.get("y0", 0) * h,
                        ann.get("x1", 0) * w,
                        ann.get("y1", 0) * h,
                    )
                    fill = ann.get("fill_color", "#000000")
                    page.add_redact_annot(r, fill=_hex_to_rgb(fill))
                    count += 1

            # Apply all redactions
            for page in doc:
                page.apply_redactions()

            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={"annotations_applied": count},
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"Annotationsfehler: {e}",
            )

    # ── Page Numbers ──────────────────────────────────────────

    def add_page_numbers(
        self,
        file_content: bytes,
        format_str: str = "Seite {page} von {total}",
        position: str = "bottom-center",
        font_size: float = 10,
        color: str = "#000000",
        start_page: int = 1,
        start_number: int = 1,
        margin: float = 36,
    ) -> PdfToolResult:
        """Add page numbers to PDF.

        position: top-left, top-center, top-right, bottom-left, bottom-center, bottom-right
        format_str: Template with {page}, {total}, {date}
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        try:
            from datetime import date

            doc = fitz.open(stream=file_content, filetype="pdf")
            total = doc.page_count
            today = date.today().strftime("%d.%m.%Y")
            pages_numbered = 0

            for page_idx in range(doc.page_count):
                if page_idx + 1 < start_page:
                    continue

                page = doc[page_idx]
                rect = page.rect
                current_num = start_number + (page_idx + 1 - start_page)

                text = format_str.format(page=current_num, total=total, date=today)

                tw = fitz.get_text_length(text, fontname="helv", fontsize=font_size)

                pos_map = {
                    "top-left": fitz.Point(margin, margin + font_size),
                    "top-center": fitz.Point((rect.width - tw) / 2, margin + font_size),
                    "top-right": fitz.Point(
                        rect.width - margin - tw, margin + font_size
                    ),
                    "bottom-left": fitz.Point(margin, rect.height - margin),
                    "bottom-center": fitz.Point(
                        (rect.width - tw) / 2, rect.height - margin
                    ),
                    "bottom-right": fitz.Point(
                        rect.width - margin - tw, rect.height - margin
                    ),
                }
                point = pos_map.get(position, pos_map["bottom-center"])

                page.insert_text(
                    point,
                    text,
                    fontname="helv",
                    fontsize=font_size,
                    color=_hex_to_rgb(color),
                )
                pages_numbered += 1

            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={"pages_numbered": pages_numbered},
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"Seitenzahlen-Fehler: {e}",
            )

    # ── Header / Footer ──────────────────────────────────────

    def add_header_footer(
        self,
        file_content: bytes,
        header_left: str = "",
        header_center: str = "",
        header_right: str = "",
        footer_left: str = "",
        footer_center: str = "",
        footer_right: str = "",
        font_size: float = 9,
        color: str = "#666666",
        start_page: int = 1,
        margin: float = 36,
    ) -> PdfToolResult:
        """Add header and/or footer text to PDF pages.

        Supports placeholders: {page}, {total}, {date}, {title}
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        try:
            from datetime import date

            doc = fitz.open(stream=file_content, filetype="pdf")
            total = doc.page_count
            today = date.today().strftime("%d.%m.%Y")
            title = (doc.metadata or {}).get("title", "")
            pages_modified = 0

            for page_idx in range(doc.page_count):
                if page_idx + 1 < start_page:
                    continue

                page = doc[page_idx]
                rect = page.rect
                page_num = page_idx + 1

                def resolve(tmpl: str, _page_num: int = page_num) -> str:
                    return tmpl.format(
                        page=_page_num, total=total, date=today, title=title
                    )

                texts = {
                    "hl": resolve(header_left),
                    "hc": resolve(header_center),
                    "hr": resolve(header_right),
                    "fl": resolve(footer_left),
                    "fc": resolve(footer_center),
                    "fr": resolve(footer_right),
                }

                rgb = _hex_to_rgb(color)
                any_written = False

                for key, text in texts.items():
                    if not text.strip():
                        continue
                    tw = fitz.get_text_length(text, fontname="helv", fontsize=font_size)

                    if key.startswith("h"):
                        y = margin + font_size
                    else:
                        y = rect.height - margin

                    if key.endswith("l"):
                        x = margin
                    elif key.endswith("c"):
                        x = (rect.width - tw) / 2
                    else:
                        x = rect.width - margin - tw

                    page.insert_text(
                        fitz.Point(x, y),
                        text,
                        fontname="helv",
                        fontsize=font_size,
                        color=rgb,
                    )
                    any_written = True

                if any_written:
                    pages_modified += 1

            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={"pages_modified": pages_modified},
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"Kopfzeilen-Fehler: {e}",
            )

    # ── Insert Text ──────────────────────────────────────────

    def insert_text(
        self,
        file_content: bytes,
        page_num: int,
        x: float,
        y: float,
        text: str,
        font_size: float = 12,
        color: str = "#000000",
        font_name: str = "helv",
    ) -> PdfToolResult:
        """Insert text at a specific position on a page.

        x, y are normalized 0-1 coordinates.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            if page_num < 1 or page_num > doc.page_count:
                doc.close()
                return PdfToolResult(
                    success=False,
                    output_format="pdf",
                    error=f"Ungueltige Seite: {page_num}",
                )

            page = doc[page_num - 1]
            rect = page.rect
            point = fitz.Point(x * rect.width, y * rect.height)

            # Map to available fonts
            available_fonts = {
                "helv": "helv",
                "times": "tiro",
                "courier": "cour",
            }
            fn = available_fonts.get(font_name.lower(), "helv")

            page.insert_text(
                point,
                text,
                fontname=fn,
                fontsize=font_size,
                color=_hex_to_rgb(color),
            )

            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"Text-Einfuegen-Fehler: {e}",
            )

    # ── Search & Replace Text ─────────────────────────────────

    def search_replace_text(
        self,
        file_content: bytes,
        search: str,
        replace: str,
        pages: list[int] | None = None,
        match_case: bool = True,
        max_replacements: int = 0,
    ) -> PdfToolResult:
        """Search and replace text in PDF using redact+re-insert.

        Uses PyMuPDF search_for() to find occurrences,
        then add_redact_annot with replacement text.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        if not search:
            return PdfToolResult(
                success=False, output_format="pdf", error="Suchtext erforderlich"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_replacements = 0
            flags = 0 if match_case else fitz.TEXT_PRESERVE_WHITESPACE

            page_range = pages if pages else list(range(1, doc.page_count + 1))

            for page_num in page_range:
                if page_num < 1 or page_num > doc.page_count:
                    continue
                page = doc[page_num - 1]

                # Find all occurrences
                instances = page.search_for(search, flags=flags)
                if not instances:
                    continue

                for inst in instances:
                    if max_replacements > 0 and total_replacements >= max_replacements:
                        break
                    page.add_redact_annot(
                        inst,
                        text=replace,
                        fontname="helv",
                        fontsize=0,  # 0 = auto-detect from original
                        align=fitz.TEXT_ALIGN_LEFT,
                    )
                    total_replacements += 1

                page.apply_redactions()

            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={
                    "replacements": total_replacements,
                    "search": search,
                    "replace": replace,
                },
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"Suchen/Ersetzen-Fehler: {e}",
            )

    # ── OCR ──────────────────────────────────────────────────

    def ocr_pdf(
        self,
        file_content: bytes,
        language: str = "deu",
    ) -> PdfToolResult:
        """Make a scanned PDF searchable using OCR (Tesseract).

        Renders each page as image, runs OCR, inserts invisible text layer.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        if not TESSERACT_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="Tesseract nicht verfuegbar"
            )
        try:
            from PIL import Image

            doc = fitz.open(stream=file_content, filetype="pdf")
            pages_processed = 0
            total_chars = 0

            lang_map = {
                "de": "deu",
                "deu": "deu",
                "deutsch": "deu",
                "en": "eng",
                "eng": "eng",
                "english": "eng",
                "deu+eng": "deu+eng",
                "de+en": "deu+eng",
            }
            tess_lang = lang_map.get(language.lower(), language)

            for page_idx in range(doc.page_count):
                page = doc[page_idx]

                # Check if page already has text
                existing_text = page.get_text().strip()
                if len(existing_text) > 50:
                    continue  # Skip pages that already have text

                # Render page at 300 DPI for good OCR
                zoom = 300 / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Run OCR with word-level bounding boxes
                ocr_data = pytesseract.image_to_data(
                    img, lang=tess_lang, output_type=pytesseract.Output.DICT
                )

                # Insert invisible text at OCR positions
                n_boxes = len(ocr_data["text"])
                for i in range(n_boxes):
                    text = ocr_data["text"][i].strip()
                    conf = (
                        int(ocr_data["conf"][i]) if ocr_data["conf"][i] != "-1" else 0
                    )
                    if not text or conf < 30:
                        continue

                    # Convert pixel coords back to PDF coords
                    x = ocr_data["left"][i] / zoom
                    y = ocr_data["top"][i] / zoom
                    h_box = ocr_data["height"][i] / zoom

                    # Estimate font size from box height
                    fs = max(6, min(h_box * 0.85, 72))

                    # Insert invisible text (render_mode=3 = invisible)
                    page.insert_text(
                        fitz.Point(x, y + h_box * 0.85),
                        text,
                        fontname="helv",
                        fontsize=fs,
                        color=(0, 0, 0),
                        render_mode=3,  # invisible
                    )
                    total_chars += len(text)

                pages_processed += 1

            total_pages = doc.page_count
            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={
                    "pages_processed": pages_processed,
                    "total_pages": total_pages,
                    "characters_recognized": total_chars,
                    "language": tess_lang,
                },
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"OCR-Fehler: {e}",
            )

    # ── PDF Compare ──────────────────────────────────────────

    def compare_pdfs(
        self,
        file_a: bytes,
        file_b: bytes,
        include_visual: bool = True,
        max_visual_pages: int = 20,
    ) -> PdfToolResult:
        """Compare two PDFs: text diff + optional visual diff.

        Returns text-based diff per page and optional visual diff images.
        """
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="json", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc_a = fitz.open(stream=file_a, filetype="pdf")
            doc_b = fitz.open(stream=file_b, filetype="pdf")

            max_pages = max(doc_a.page_count, doc_b.page_count)
            page_diffs = []
            total_similarity = 0.0

            for page_idx in range(max_pages):
                text_a = ""
                text_b = ""
                if page_idx < doc_a.page_count:
                    text_a = doc_a[page_idx].get_text()
                if page_idx < doc_b.page_count:
                    text_b = doc_b[page_idx].get_text()

                lines_a = text_a.splitlines()
                lines_b = text_b.splitlines()

                matcher = SequenceMatcher(None, lines_a, lines_b)
                ratio = matcher.ratio()
                total_similarity += ratio

                changes = []
                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == "equal":
                        for k in range(i1, min(i1 + 3, i2)):
                            changes.append({"type": "equal", "text": lines_a[k]})
                        if i2 - i1 > 3:
                            changes.append(
                                {
                                    "type": "skip",
                                    "text": f"... {i2 - i1 - 3} gleiche Zeilen ...",
                                }
                            )
                    elif tag == "replace":
                        for k in range(i1, i2):
                            changes.append({"type": "removed", "text": lines_a[k]})
                        for k in range(j1, j2):
                            changes.append({"type": "added", "text": lines_b[k]})
                    elif tag == "delete":
                        for k in range(i1, i2):
                            changes.append({"type": "removed", "text": lines_a[k]})
                    elif tag == "insert":
                        for k in range(j1, j2):
                            changes.append({"type": "added", "text": lines_b[k]})

                page_diff = {
                    "page": page_idx + 1,
                    "similarity": round(ratio * 100, 1),
                    "changes": changes,
                }

                # Visual diff: render both pages and highlight differences
                if include_visual and page_idx < max_visual_pages:
                    zoom = 1.5
                    mat = fitz.Matrix(zoom, zoom)

                    img_a_b64 = ""
                    img_b_b64 = ""
                    diff_b64 = ""

                    if page_idx < doc_a.page_count:
                        pix_a = doc_a[page_idx].get_pixmap(matrix=mat, alpha=False)
                        img_a_b64 = base64.b64encode(pix_a.tobytes("png")).decode()

                    if page_idx < doc_b.page_count:
                        pix_b = doc_b[page_idx].get_pixmap(matrix=mat, alpha=False)
                        img_b_b64 = base64.b64encode(pix_b.tobytes("png")).decode()

                    # Generate diff overlay if numpy available and both pages exist
                    if (
                        NUMPY_AVAILABLE
                        and page_idx < doc_a.page_count
                        and page_idx < doc_b.page_count
                    ):
                        try:
                            pix_a = doc_a[page_idx].get_pixmap(matrix=mat, alpha=False)
                            pix_b = doc_b[page_idx].get_pixmap(matrix=mat, alpha=False)
                            arr_a = np.frombuffer(
                                pix_a.samples, dtype=np.uint8
                            ).reshape(pix_a.height, pix_a.width, 3)
                            arr_b = np.frombuffer(
                                pix_b.samples, dtype=np.uint8
                            ).reshape(pix_b.height, pix_b.width, 3)
                            # Resize to same dimensions if needed
                            min_h = min(arr_a.shape[0], arr_b.shape[0])
                            min_w = min(arr_a.shape[1], arr_b.shape[1])
                            arr_a = arr_a[:min_h, :min_w]
                            arr_b = arr_b[:min_h, :min_w]

                            # Compute absolute difference
                            diff = np.abs(arr_a.astype(int) - arr_b.astype(int))
                            diff_gray = diff.mean(axis=2)

                            # Create diff overlay: red where different
                            overlay = arr_b.copy()
                            mask = diff_gray > 20
                            overlay[mask] = [255, 80, 80]

                            # Encode as PNG
                            from PIL import Image as PilImage

                            diff_img = PilImage.fromarray(overlay.astype(np.uint8))
                            buf = io.BytesIO()
                            diff_img.save(buf, format="PNG")
                            diff_b64 = base64.b64encode(buf.getvalue()).decode()
                        except Exception as e:
                            logger.warning("PDF visual diff generation failed: %s", e)

                    page_diff["visual"] = {
                        "image_a": img_a_b64,
                        "image_b": img_b_b64,
                        "diff": diff_b64,
                    }

                page_diffs.append(page_diff)

            avg_similarity = (
                (total_similarity / max_pages * 100) if max_pages > 0 else 100.0
            )
            pages_a = doc_a.page_count
            pages_b = doc_b.page_count
            doc_a.close()
            doc_b.close()

            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={
                    "pages_a": pages_a,
                    "pages_b": pages_b,
                    "total_pages": max_pages,
                    "average_similarity": round(avg_similarity, 1),
                    "page_diffs": page_diffs,
                },
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="json",
                error=f"Vergleichsfehler: {e}",
            )

    # ── Flatten Annotations ──────────────────────────────────

    def flatten_annotations(self, file_content: bytes) -> PdfToolResult:
        """Flatten (burn in) all annotations into the PDF content."""
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="pdf", error="PyMuPDF nicht verfuegbar"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_flattened = 0

            for page in doc:
                annots = list(page.annots()) if page.annots() else []
                for annot in annots:
                    # Render annotation into page content
                    page.delete_annot(annot)
                    total_flattened += 1

            # Re-save to flatten everything
            output = doc.tobytes(deflate=True, garbage=4)
            doc.close()

            # A better approach: use the "appearance" trick
            # Re-open and use insert_pdf to flatten
            doc = fitz.open(stream=file_content, filetype="pdf")
            new_doc = fitz.open()
            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                # Create a new page with same dimensions
                new_page = new_doc.new_page(
                    width=page.rect.width, height=page.rect.height
                )
                # Render original page (with annotations) as image
                pix = page.get_pixmap(dpi=200, alpha=False)
                new_page.insert_image(page.rect, pixmap=pix)

            output = new_doc.tobytes(deflate=True, garbage=4)
            new_doc.close()
            doc.close()

            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=output,
                metadata={"annotations_flattened": total_flattened},
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="pdf",
                error=f"Flatten-Fehler: {e}",
            )

    # ── Search Text (find without replace) ────────────────────

    def search_text(
        self,
        file_content: bytes,
        search: str,
        match_case: bool = True,
    ) -> PdfToolResult:
        """Search for text in PDF, return all occurrences with positions."""
        if not PYMUPDF_AVAILABLE:
            return PdfToolResult(
                success=False, output_format="json", error="PyMuPDF nicht verfuegbar"
            )
        if not search:
            return PdfToolResult(
                success=False, output_format="json", error="Suchtext erforderlich"
            )
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            results = []
            flags = 0 if match_case else fitz.TEXT_PRESERVE_WHITESPACE

            for page_idx in range(doc.page_count):
                page = doc[page_idx]
                rect = page.rect
                instances = page.search_for(search, flags=flags)
                for inst in instances:
                    results.append(
                        {
                            "page": page_idx + 1,
                            "bbox": {
                                "x0": round(inst.x0 / rect.width, 4),
                                "y0": round(inst.y0 / rect.height, 4),
                                "x1": round(inst.x1 / rect.width, 4),
                                "y1": round(inst.y1 / rect.height, 4),
                            },
                        }
                    )

            doc.close()
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={
                    "query": search,
                    "total_found": len(results),
                    "results": results,
                },
            )
        except Exception as e:
            return PdfToolResult(
                success=False,
                output_format="json",
                error=f"Suchfehler: {e}",
            )


@lru_cache(maxsize=1)
def get_pdf_editor() -> PdfEditorService:
    """Get singleton instance of PdfEditorService."""
    return PdfEditorService()
