"""Erweiterte PDF-Werkzeuge der Standalone-App.

Ergänzt die aus audit_designer kopierten Services (die bewusst unverändert
bleiben) um: Textextraktion, Formulare, Bates-Nummerierung, suchbasierte
Schwärzung, Bild-Signatur, blockbasierte WYSIWYG-Textbearbeitung und
PDF/A-Konvertierung (Ghostscript). Alles in-memory; PDF/A nutzt wie die
LibreOffice-Konvertierung ein automatisch gelöschtes TemporaryDirectory.
"""

import io
import logging
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from app.services.pdf_tools_service import PdfToolResult

logger = logging.getLogger(__name__)

try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

GHOSTSCRIPT_BIN = shutil.which("gs")


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = (hex_color or "#000000").lstrip("#")
    if len(h) != 6:
        return (0, 0, 0)
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))


def _fail(msg: str, fmt: str = "pdf") -> PdfToolResult:
    return PdfToolResult(success=False, output_format=fmt, error=msg)


# Die eingebauten Basis-Fonts (helv) können nur Latin-1 — typografische
# Zeichen vorab auf Latin-1-Äquivalente abbilden statt sie zu "?" zu machen.
_LATIN1_MAP = str.maketrans(
    {
        "–": "-",  # – Halbgeviertstrich
        "—": "-",  # — Geviertstrich
        "‘": "'",
        "’": "'",
        "‚": ",",
        "“": '"',
        "”": '"',
        "„": '"',
        "…": "...",
        " ": " ",
        "•": "-",
        "€": "EUR",
    }
)


def _latin1_safe(text: str) -> str:
    return text.translate(_LATIN1_MAP).encode("latin-1", "replace").decode("latin-1")


class PdfExtrasService:
    def check_features(self) -> dict[str, bool]:
        return {
            "pdf_to_text": PYMUPDF_AVAILABLE,
            "form_fill": PYMUPDF_AVAILABLE,
            "bates": PYMUPDF_AVAILABLE,
            "redact_search": PYMUPDF_AVAILABLE,
            "sign_image": PYMUPDF_AVAILABLE,
            "text_edit_blocks": PYMUPDF_AVAILABLE,
            "pdfa": bool(GHOSTSCRIPT_BIN),
        }

    # ── Textextraktion ────────────────────────────────────────

    def extract_text(self, file_content: bytes) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar", "txt")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            parts = []
            for i in range(doc.page_count):
                parts.append(f"===== Seite {i + 1} =====\n")
                parts.append(doc[i].get_text("text"))
                parts.append("\n")
            doc.close()
            text = "".join(parts)
            return PdfToolResult(
                success=True,
                output_format="txt",
                file_content=text.encode("utf-8"),
                metadata={"characters": len(text)},
            )
        except Exception as e:
            return _fail(f"Textextraktion fehlgeschlagen: {e}", "txt")

    # ── Formulare (AcroForm) ──────────────────────────────────

    def get_form_fields(self, file_content: bytes) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar", "json")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            fields = []
            for page_idx in range(doc.page_count):
                for widget in doc[page_idx].widgets() or []:
                    fields.append(
                        {
                            "name": widget.field_name or f"feld_{len(fields)}",
                            "type": widget.field_type_string,
                            "value": widget.field_value or "",
                            "options": widget.choice_values or [],
                            "page": page_idx + 1,
                        }
                    )
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={"fields": fields, "count": len(fields)},
            )
        except Exception as e:
            return _fail(f"Formularfelder lesen fehlgeschlagen: {e}", "json")

    def fill_form(
        self, file_content: bytes, values: dict, flatten: bool = False
    ) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            filled = 0
            for page_idx in range(doc.page_count):
                for widget in doc[page_idx].widgets() or []:
                    name = widget.field_name
                    if name not in values:
                        continue
                    value = values[name]
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_CHECKBOX:
                        widget.field_value = bool(value) and value not in (
                            "false",
                            "Off",
                            "0",
                        )
                    else:
                        widget.field_value = str(value)
                    widget.update()
                    filled += 1
            if flatten:
                # Feldinhalte einbrennen: Widgets in Seiteninhalt konvertieren
                data = doc.convert_to_pdf()
                doc.close()
                doc = fitz.open(stream=data, filetype="pdf")
            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=out,
                metadata={"filled": filled},
            )
        except Exception as e:
            return _fail(f"Formular ausfüllen fehlgeschlagen: {e}")

    # ── Bates-Nummerierung ────────────────────────────────────

    def add_bates_numbers(
        self,
        file_content: bytes,
        prefix: str = "",
        start: int = 1,
        digits: int = 6,
        position: str = "bottom-right",
        font_size: float = 9,
        color: str = "#000000",
    ) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            rgb = _hex_to_rgb(color)
            margin = 24
            for i in range(doc.page_count):
                page = doc[i]
                label = f"{prefix}{start + i:0{digits}d}"
                rect = page.rect
                width = fitz.get_text_length(label, fontname="helv", fontsize=font_size)
                if "left" in position:
                    x = margin
                elif "center" in position:
                    x = (rect.width - width) / 2
                else:
                    x = rect.width - margin - width
                y = margin if position.startswith("top") else rect.height - margin
                page.insert_text(
                    fitz.Point(x, y), label, fontsize=font_size, fontname="helv", color=rgb
                )
            out = doc.tobytes(garbage=3, deflate=True)
            last = f"{prefix}{start + doc.page_count - 1:0{digits}d}"
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=out,
                metadata={"first": f"{prefix}{start:0{digits}d}", "last": last},
            )
        except Exception as e:
            return _fail(f"Bates-Nummerierung fehlgeschlagen: {e}")

    # ── Suchbasierte Schwärzung ───────────────────────────────

    def redact_search(
        self, file_content: bytes, term: str, match_case: bool = False
    ) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        if not term.strip():
            return _fail("Suchbegriff erforderlich")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            count = 0
            flags = 0 if match_case else fitz.TEXT_DEHYPHENATE
            for i in range(doc.page_count):
                page = doc[i]
                hits = page.search_for(term, flags=flags)
                for rect in hits:
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                    count += 1
                if hits:
                    page.apply_redactions()
            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=out,
                metadata={"redactions": count},
            )
        except Exception as e:
            return _fail(f"Schwärzung fehlgeschlagen: {e}")

    # ── Bild-Signatur / Stempelbild ───────────────────────────

    def place_image(
        self,
        file_content: bytes,
        image_content: bytes,
        page_num: int,
        x: float,
        y: float,
        width_frac: float = 0.25,
    ) -> PdfToolResult:
        """Bild (Signatur/Stempel) auf einer Seite platzieren.

        x/y sind die normierte (0-1) linke obere Ecke, width_frac die Breite
        relativ zur Seitenbreite; die Höhe folgt dem Seitenverhältnis.
        """
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            if page_num < 1 or page_num > doc.page_count:
                doc.close()
                return _fail(f"Ungültige Seite: {page_num}")
            img = fitz.open(stream=image_content)
            iw, ih = img[0].rect.width, img[0].rect.height
            img.close()
            page = doc[page_num - 1]
            rect = page.rect
            w = max(0.02, min(width_frac, 1.0)) * rect.width
            h = w * (ih / iw) if iw else w
            x0 = min(max(x, 0.0), 1.0) * rect.width
            y0 = min(max(y, 0.0), 1.0) * rect.height
            target = fitz.Rect(x0, y0, min(x0 + w, rect.width), min(y0 + h, rect.height))
            page.insert_image(target, stream=image_content, keep_proportion=True)
            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(success=True, output_format="pdf", file_content=out)
        except Exception as e:
            return _fail(f"Bild platzieren fehlgeschlagen: {e}")

    # ── Blockbasierte WYSIWYG-Textbearbeitung ─────────────────

    def edit_text_blocks(self, file_content: bytes, edits: list[dict]) -> PdfToolResult:
        """Textblöcke ersetzen: Originalbereich schwärzungsfrei entfernen
        (Redaction mit weißer Füllung), neuen Text in dieselbe Box setzen.

        edit: {page, bbox: {x0,y0,x1,y1} (normiert), text, font_size, color}
        Kein Acrobat-Reflow: Der Text bleibt in der Box; bei Überlauf wird die
        Schriftgröße schrittweise verkleinert (Warnung in metadata).
        """
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        if not edits:
            return _fail("Keine Änderungen übergeben")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            warnings: list[str] = []

            # 1. Alle Originalbereiche pro Seite entfernen (weiße Redaction)
            by_page: dict[int, list[dict]] = {}
            for edit in edits:
                by_page.setdefault(int(edit.get("page", 1)), []).append(edit)

            for page_num, page_edits in by_page.items():
                if page_num < 1 or page_num > doc.page_count:
                    warnings.append(f"Seite {page_num} existiert nicht — übersprungen")
                    continue
                page = doc[page_num - 1]
                rect = page.rect
                for edit in page_edits:
                    b = edit.get("bbox", {})
                    r = fitz.Rect(
                        float(b.get("x0", 0)) * rect.width,
                        float(b.get("y0", 0)) * rect.height,
                        float(b.get("x1", 0)) * rect.width,
                        float(b.get("y1", 0)) * rect.height,
                    )
                    page.add_redact_annot(r, fill=(1, 1, 1))
                page.apply_redactions()

                # 2. Neuen Text in die Boxen setzen (Auto-Shrink bei Überlauf)
                for edit in page_edits:
                    text = _latin1_safe(str(edit.get("text", "")))
                    if not text.strip():
                        continue  # leerer Text = Block nur entfernen
                    b = edit.get("bbox", {})
                    r = fitz.Rect(
                        float(b.get("x0", 0)) * rect.width,
                        float(b.get("y0", 0)) * rect.height,
                        float(b.get("x1", 0)) * rect.width,
                        float(b.get("y1", 0)) * rect.height,
                    )
                    size = float(edit.get("font_size", 11)) or 11
                    rgb = _hex_to_rgb(edit.get("color", "#000000"))
                    placed = False
                    while size >= 5:
                        leftover = page.insert_textbox(
                            r, text, fontsize=size, fontname="helv", color=rgb, align=0
                        )
                        if leftover >= 0:
                            placed = True
                            break
                        size -= 0.5
                    if not placed:
                        # letzter Versuch: minimal klein, Box leicht vergrößert
                        bigger = fitz.Rect(r.x0, r.y0, r.x1, min(r.y1 + 14, rect.height))
                        page.insert_textbox(
                            bigger, text, fontsize=5, fontname="helv", color=rgb, align=0
                        )
                        warnings.append(
                            f"Seite {page_num}: Text passte nicht vollständig in die Box"
                        )

            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=out,
                metadata={"edits": len(edits)},
                warnings=warnings,
            )
        except Exception as e:
            return _fail(f"Textbearbeitung fehlgeschlagen: {e}")

    # ── PDF/A (Ghostscript) ───────────────────────────────────

    def convert_pdfa(self, file_content: bytes, level: str = "2b") -> PdfToolResult:
        if not GHOSTSCRIPT_BIN:
            return _fail("Ghostscript nicht verfügbar — PDF/A deaktiviert")
        if level not in ("1b", "2b", "3b"):
            level = "2b"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "in.pdf"
                dst = Path(tmp) / "out.pdf"
                src.write_bytes(file_content)
                part = level[0]
                cmd = [
                    GHOSTSCRIPT_BIN,
                    f"-dPDFA={part}",
                    "-dBATCH",
                    "-dNOPAUSE",
                    "-dNOOUTERSAVE",
                    "-sColorConversionStrategy=UseDeviceIndependentColor",
                    "-sDEVICE=pdfwrite",
                    "-dPDFACompatibilityPolicy=1",
                    f"-sOutputFile={dst}",
                    str(src),
                ]
                proc = subprocess.run(cmd, capture_output=True, timeout=300)
                if proc.returncode != 0 or not dst.exists():
                    logger.warning("Ghostscript PDF/A fehlgeschlagen: rc=%s", proc.returncode)
                    return _fail("PDF/A-Konvertierung fehlgeschlagen")
                return PdfToolResult(
                    success=True,
                    output_format="pdf",
                    file_content=dst.read_bytes(),
                    metadata={"level": f"PDF/A-{level}"},
                )
        except subprocess.TimeoutExpired:
            return _fail("PDF/A-Konvertierung: Zeitlimit überschritten")
        except Exception as e:
            return _fail(f"PDF/A-Konvertierung fehlgeschlagen: {e}")


@lru_cache(maxsize=1)
def get_pdf_extras() -> PdfExtrasService:
    return PdfExtrasService()
