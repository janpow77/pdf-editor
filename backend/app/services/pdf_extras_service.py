"""Erweiterte PDF-Werkzeuge der Standalone-App.

Ergänzt die aus audit_designer kopierten Services (die bewusst unverändert
bleiben) um: Textextraktion, Formulare, Bates-Nummerierung, suchbasierte
Schwärzung, Bild-Signatur, blockbasierte WYSIWYG-Textbearbeitung und
PDF/A-Konvertierung (Ghostscript). Alles in-memory; PDF/A nutzt wie die
LibreOffice-Konvertierung ein automatisch gelöschtes TemporaryDirectory.
"""

import csv
import io
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
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

try:
    from pyhanko.sign import signers as _pyhanko_signers

    PYHANKO_AVAILABLE = True
except ImportError:
    PYHANKO_AVAILABLE = False

try:
    import ocrmypdf as _ocrmypdf

    # OCRmyPDF braucht Ghostscript zur Laufzeit
    OCRMYPDF_AVAILABLE = bool(GHOSTSCRIPT_BIN)
except ImportError:
    OCRMYPDF_AVAILABLE = False


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


# ── Schrifteinbettung für die Textbearbeitung ─────────────────
# Die eingebauten Basis-14-Schriften können nur Latin-1; damit gingen bisher
# Zeichen wie „—" oder „✓" verloren. Stattdessen werden echte TrueType-Dateien
# eingebettet: Liberation ist metrisch kompatibel zu Arial/Times/Courier (das
# Layout bleibt also ähnlich), DejaVu deckt deutlich mehr Zeichen ab und dient
# als Rückfall. Fehlen beide, greift wieder Basis-14 mit Latin-1-Ersetzung.

_FONT_DIRS = (
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation2",
)

# (Familie, fett, kursiv) → Dateiname in bevorzugter Reihenfolge
_FONT_FILES: dict[tuple[str, bool, bool], tuple[str, ...]] = {
    ("sans", False, False): ("LiberationSans-Regular.ttf", "DejaVuSans.ttf"),
    ("sans", True, False): ("LiberationSans-Bold.ttf", "DejaVuSans-Bold.ttf"),
    ("sans", False, True): ("LiberationSans-Italic.ttf", "DejaVuSans-Oblique.ttf"),
    ("sans", True, True): ("LiberationSans-BoldItalic.ttf", "DejaVuSans-BoldOblique.ttf"),
    ("serif", False, False): ("LiberationSerif-Regular.ttf", "DejaVuSerif.ttf"),
    ("serif", True, False): ("LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"),
    ("serif", False, True): ("LiberationSerif-Italic.ttf", "DejaVuSerif-Italic.ttf"),
    ("serif", True, True): ("LiberationSerif-BoldItalic.ttf", "DejaVuSerif-BoldItalic.ttf"),
    ("mono", False, False): ("LiberationMono-Regular.ttf", "DejaVuSansMono.ttf"),
    ("mono", True, False): ("LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"),
    ("mono", False, True): ("LiberationMono-Italic.ttf", "DejaVuSansMono-Oblique.ttf"),
    ("mono", True, True): (
        "LiberationMono-BoldItalic.ttf",
        "DejaVuSansMono-BoldOblique.ttf",
    ),
}

_UNICODE_FALLBACKS = ("DejaVuSans.ttf", "DejaVuSerif.ttf")


@lru_cache(maxsize=64)
def _font_path(filename: str) -> str | None:
    for directory in _FONT_DIRS:
        candidate = Path(directory) / filename
        if candidate.is_file():
            return str(candidate)
    return None


@lru_cache(maxsize=32)
def _font_covers(path: str, text: str) -> bool:
    """Deckt die Schrift alle Zeichen ab? (Leerraum bleibt außen vor)"""
    if not PYMUPDF_AVAILABLE:
        return False
    try:
        font = fitz.Font(fontfile=path)
    except Exception:
        return False
    return all(font.has_glyph(ord(ch)) for ch in set(text) if not ch.isspace())


def classify_font(font_name: str) -> tuple[str, bool, bool]:
    """Schriftname aus dem PDF auf (Familie, fett, kursiv) abbilden."""
    name = (font_name or "").lower()
    bold = "bold" in name or "black" in name or "heavy" in name or ",b" in name
    italic = "italic" in name or "oblique" in name or ",i" in name
    if any(k in name for k in ("courier", "mono", "consol")):
        family = "mono"
    elif any(k in name for k in ("times", "serif", "georgia", "garamond", "book", "roman")):
        family = "serif"
    else:
        family = "sans"
    return family, bold, italic


def select_font_file(font_name: str, text: str) -> str | None:
    """Passende einbettbare Schriftdatei — None, wenn keine gefunden wurde."""
    key = classify_font(font_name)
    for filename in _FONT_FILES.get(key, ()):
        path = _font_path(filename)
        if path and _font_covers(path, text):
            return path
    # Stil beibehalten war nicht möglich: breiteste Abdeckung gewinnt
    for filename in _UNICODE_FALLBACKS:
        path = _font_path(filename)
        if path and _font_covers(path, text):
            return path
    # Keine vollständige Abdeckung: beste vorhandene Schrift trotzdem nutzen
    for filename in _FONT_FILES.get(key, ()) + _UNICODE_FALLBACKS:
        path = _font_path(filename)
        if path:
            return path
    return None


# ── Musterbasierte Schwärzung ─────────────────────────────────
# Bewusst konservativ formuliert: lieber ein Treffer weniger als eine falsche
# Schwärzung. Die Vorschau zeigt jede Fundstelle vor dem unumkehrbaren Schritt.


@dataclass(frozen=True)
class RedactionPattern:
    label: str
    regex: str
    hint: str


REDACTION_PATTERNS: dict[str, RedactionPattern] = {
    "iban": RedactionPattern(
        "IBAN",
        r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4})+(?:\s?[A-Z0-9]{1,3})?\b",
        "Kontonummern, auch in Vierergruppen geschrieben",
    ),
    "email": RedactionPattern(
        "E-Mail-Adresse",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "Adressen in Anschreiben und Verteilern",
    ),
    "telefon": RedactionPattern(
        "Telefonnummer",
        r"(?:\+49|0)\s?(?:\d{2,5}[\s/-]?){1,3}\d{2,8}",
        "deutsche Rufnummern mit Vorwahl",
    ),
    "steuer_id": RedactionPattern(
        "Steuer-Identifikationsnummer",
        r"\b\d{11}\b",
        "11-stellige Steuer-ID — prüfen, sonst werden lange Zahlen mitgeschwärzt",
    ),
    "ust_id": RedactionPattern(
        "Umsatzsteuer-Identifikationsnummer",
        r"\bDE\s?\d{9}\b",
        "USt-IdNr. der Begünstigten",
    ),
    "kreditkarte": RedactionPattern(
        "Kreditkartennummer",
        r"\b(?:\d{4}[\s-]?){3}\d{4}\b",
        "16-stellige Kartennummern",
    ),
    "geburtsdatum": RedactionPattern(
        "Datum (TT.MM.JJJJ)",
        r"\b(?:0?[1-9]|[12]\d|3[01])\.(?:0?[1-9]|1[0-2])\.(?:19|20)\d{2}\b",
        "z.B. Geburtsdaten — trifft alle Datumsangaben dieses Formats",
    ),
    "ip_adresse": RedactionPattern(
        "IP-Adresse",
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "IPv4-Adressen aus Protokollauszügen",
    ),
    "aktenzeichen": RedactionPattern(
        "Aktenzeichen",
        r"\b[A-Z]{1,4}[-/ ]?\d{1,6}[-/]\d{2,4}\b",
        "Muster wie AZ-1234/26 — vor dem Schwärzen prüfen",
    ),
}


# ── Formular-Designer: Feldtypen ──────────────────────────────
# Radio-Gruppen fehlen bewusst: PyMuPDF 1.28 kann mehrere Radio-Widgets
# derselben Gruppe nicht anlegen ("bad xref" beim ersten Widget) und liefert
# keine getrennten On-States. Ersatz im UI: Dropdown bzw. Checkboxen.
FORM_FIELD_TYPES = ("text", "textarea", "checkbox", "dropdown", "listbox", "signature")

_WIDGET_TO_DESIGNER: dict[int, str] = (
    {
        fitz.PDF_WIDGET_TYPE_TEXT: "text",
        fitz.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
        fitz.PDF_WIDGET_TYPE_COMBOBOX: "dropdown",
        fitz.PDF_WIDGET_TYPE_LISTBOX: "listbox",
        fitz.PDF_WIDGET_TYPE_SIGNATURE: "signature",
    }
    if PYMUPDF_AVAILABLE
    else {}
)

# Feldnamen landen im PDF-AcroForm — Punkt (Hierarchie), Klammern und
# Steuerzeichen führen zu unbrauchbaren oder mehrdeutigen Namen.
_FIELD_NAME_FORBIDDEN = str.maketrans({c: "_" for c in '.[]()/<>{}"\r\n\t'})


def _field_name_safe(name: str, fallback: str) -> str:
    cleaned = (name or "").strip().translate(_FIELD_NAME_FORBIDDEN)
    cleaned = "".join(ch for ch in cleaned if ch.isprintable()).strip()
    return (cleaned or fallback)[:120]


# ── Formular-Berechnung, -Formatierung und -Prüfung ───────────
# Es wird bewusst KEIN freies JavaScript übernommen: der Designer liefert nur
# eine Rechenart bzw. einen arithmetischen Ausdruck über Feldnamen, das Skript
# baut dieser Service. Sonst wäre die App ein bequemer Weg, beliebiges
# JavaScript in fremde PDFs zu schreiben.
CALC_KINDS = {"sum": "SUM", "product": "PRD", "average": "AVG", "min": "MIN", "max": "MAX"}
FORMAT_KINDS = ("none", "number", "currency", "percent")

_FORMULA_TOKEN = re.compile(r"[A-Za-zÄÖÜäöüß_][A-Za-zÄÖÜäöüß0-9_]*|\d+(?:[.,]\d+)?|[-+*/()]|\s+")


def _js_string(value: str) -> str:
    """Zeichenkette für die Einbettung in erzeugtes PDF-JavaScript maskieren."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ")


def _build_format_script(fmt: dict) -> str:
    kind = str(fmt.get("kind", "none")).lower()
    if kind not in FORMAT_KINDS or kind == "none":
        return ""
    decimals = max(0, min(6, int(fmt.get("decimals", 2))))
    if kind == "percent":
        return f"AFPercent_Format({decimals}, 0);"
    currency = _js_string(str(fmt.get("currency", "€"))[:8]) if kind == "currency" else ""
    # sepStyle 3 = 1.234,56 (deutsches Format), negStyle 0 = Minuszeichen
    if kind == "currency":
        return f'AFNumber_Format({decimals}, 3, 0, 0, " {currency}", false);'
    return f'AFNumber_Format({decimals}, 3, 0, 0, "", false);'


def _build_calc_script(calc: dict, known_names: set[str]) -> tuple[str, str]:
    """(Skript, Fehlermeldung) — leeres Skript heißt: keine Berechnung."""
    kind = str(calc.get("kind", "")).lower()
    if not kind or kind == "none":
        return "", ""
    if kind in CALC_KINDS:
        names = [str(n).strip() for n in (calc.get("fields") or []) if str(n).strip()]
        unknown = [n for n in names if n not in known_names]
        if not names:
            return "", "Berechnung ohne Quellfelder"
        if unknown:
            return "", f"Berechnung verweist auf unbekannte Felder: {', '.join(unknown)}"
        array = ", ".join(f'"{_js_string(n)}"' for n in names)
        return f'AFSimple_Calc("{CALC_KINDS[kind]}", new Array({array}));', ""
    if kind != "formula":
        return "", f"Unbekannte Rechenart '{kind}'"

    formula = str(calc.get("formula", "")).strip()
    if not formula:
        return "", "Formel ist leer"
    if len(formula) > 200:
        return "", "Formel ist zu lang (max. 200 Zeichen)"
    parts: list[str] = []
    used: list[str] = []
    pos = 0
    while pos < len(formula):
        m = _FORMULA_TOKEN.match(formula, pos)
        if not m:
            return "", f"Unerlaubtes Zeichen in Formel: '{formula[pos]}'"
        token = m.group(0)
        pos = m.end()
        if token.isspace():
            parts.append(" ")
        elif token[0].isdigit():
            parts.append(token.replace(",", "."))
        elif token in "+-*/()":
            parts.append(token)
        else:
            if token not in known_names:
                return "", f"Formel verweist auf unbekanntes Feld '{token}'"
            used.append(token)
            parts.append(f'(Number(this.getField("{_js_string(token)}").value) || 0)')
    if not used:
        return "", "Formel enthält kein Feld"
    return f"event.value = {''.join(parts)};", ""


def _build_validate_script(rule: dict) -> str:
    lo, hi = rule.get("min"), rule.get("max")
    has_lo = lo is not None and str(lo) != ""
    has_hi = hi is not None and str(hi) != ""
    if not has_lo and not has_hi:
        return ""
    lo_v = float(lo) if has_lo else 0
    hi_v = float(hi) if has_hi else 0
    return (
        f"AFRange_Validate({str(has_lo).lower()}, {lo_v}, "
        f"{str(has_hi).lower()}, {hi_v});"
    )


class PdfExtrasService:
    def check_features(self) -> dict[str, bool]:
        return {
            "pdf_to_text": PYMUPDF_AVAILABLE,
            "form_fill": PYMUPDF_AVAILABLE,
            "form_design": PYMUPDF_AVAILABLE,
            "bates": PYMUPDF_AVAILABLE,
            "redact_search": PYMUPDF_AVAILABLE,
            "sign_image": PYMUPDF_AVAILABLE,
            "text_edit_blocks": PYMUPDF_AVAILABLE,
            "pdfa": bool(GHOSTSCRIPT_BIN),
            "sign_digital": PYHANKO_AVAILABLE,
            "scan_optimize": OCRMYPDF_AVAILABLE,
            "batch": PYMUPDF_AVAILABLE,
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
                page = doc[page_idx]
                prect = page.rect
                for widget in page.widgets() or []:
                    flags = int(widget.field_flags or 0)
                    multiline = bool(flags & fitz.PDF_TX_FIELD_IS_MULTILINE)
                    r = widget.rect
                    fields.append(
                        {
                            "name": widget.field_name or f"feld_{len(fields)}",
                            "type": widget.field_type_string,
                            "value": widget.field_value or "",
                            "options": widget.choice_values or [],
                            "page": page_idx + 1,
                            # Designer-Daten: normierte Geometrie + Eigenschaften,
                            # damit vorhandene Formulare importiert werden können
                            "designer_type": _WIDGET_TO_DESIGNER.get(
                                widget.field_type, "text"
                            )
                            if not multiline
                            else "textarea",
                            "x0": round(r.x0 / prect.width, 5) if prect.width else 0,
                            "y0": round(r.y0 / prect.height, 5) if prect.height else 0,
                            "x1": round(r.x1 / prect.width, 5) if prect.width else 0,
                            "y1": round(r.y1 / prect.height, 5) if prect.height else 0,
                            "font_size": float(widget.text_fontsize or 0) or 11.0,
                            "required": bool(flags & fitz.PDF_FIELD_IS_REQUIRED),
                            "readonly": bool(flags & fitz.PDF_FIELD_IS_READ_ONLY),
                            "tooltip": widget.field_label or "",
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

    # ── Musterbasierte Schwärzung ─────────────────────────────

    def _line_groups(self, page) -> list[tuple[str, list[tuple[int, int]], list]]:
        """Zeilen einer Seite als (Text, Zeichen-Spannen je Wort, Wort-Rechtecke).

        Regex-Treffer werden über die Zeichen-Spannen auf Wörter und damit auf
        Rechtecke zurückgeführt — so werden auch Muster gefunden, die über
        Leerzeichen laufen (z.B. eine IBAN in Vierergruppen).
        """
        lines: dict[tuple[int, int], list] = {}
        for word in page.get_text("words"):
            lines.setdefault((word[5], word[6]), []).append(word)
        result = []
        for key in sorted(lines):
            words = sorted(lines[key], key=lambda w: w[7])
            text_parts: list[str] = []
            spans: list[tuple[int, int]] = []
            pos = 0
            for w in words:
                token = w[4]
                spans.append((pos, pos + len(token)))
                text_parts.append(token)
                pos += len(token) + 1  # Trennzeichen
            result.append((" ".join(text_parts), spans, words))
        return result

    def find_pattern_matches(
        self,
        file_content: bytes,
        patterns: list[str],
        terms: list[str] | None = None,
        case_sensitive: bool = False,
        whole_word: bool = True,
    ) -> tuple[list[dict], dict[str, int]] | None:
        """Alle Fundstellen mit Seite, Text und Rechteck — Basis für Vorschau
        und Schwärzung. None, wenn PyMuPDF fehlt."""
        if not PYMUPDF_AVAILABLE:
            return None
        compiled: list[tuple[str, re.Pattern]] = []
        flags = 0 if case_sensitive else re.IGNORECASE
        for key in patterns:
            spec = REDACTION_PATTERNS.get(key)
            if spec:
                compiled.append((key, re.compile(spec.regex, flags)))
        for term in terms or []:
            term = term.strip()
            if not term:
                continue
            escaped = re.escape(term)
            if whole_word:
                escaped = rf"(?<!\w){escaped}(?!\w)"
            compiled.append((f"begriff:{term}", re.compile(escaped, flags)))

        findings: list[dict] = []
        counts: dict[str, int] = {}
        doc = fitz.open(stream=file_content, filetype="pdf")
        try:
            for pno in range(doc.page_count):
                page = doc[pno]
                for line_text, spans, words in self._line_groups(page):
                    for key, rx in compiled:
                        for match in rx.finditer(line_text):
                            start, end = match.span()
                            hit_rects = [
                                fitz.Rect(w[:4])
                                for (s, e), w in zip(spans, words)
                                if s < end and e > start
                            ]
                            if not hit_rects:
                                continue
                            box = hit_rects[0]
                            for r in hit_rects[1:]:
                                box |= r
                            findings.append(
                                {
                                    "pattern": key,
                                    "page": pno + 1,
                                    "text": match.group(0),
                                    "rect": [round(v, 2) for v in box],
                                }
                            )
                            counts[key] = counts.get(key, 0) + 1
        finally:
            doc.close()
        return findings, counts

    def redact_patterns(
        self,
        file_content: bytes,
        patterns: list[str],
        terms: list[str] | None = None,
        case_sensitive: bool = False,
        whole_word: bool = True,
    ) -> PdfToolResult:
        """Fundstellen der gewählten Muster/Begriffe unwiderruflich entfernen."""
        found = self.find_pattern_matches(
            file_content, patterns, terms, case_sensitive, whole_word
        )
        if found is None:
            return _fail("PyMuPDF nicht verfügbar")
        findings, counts = found
        if not findings:
            return _fail("Keine Fundstellen für die gewählten Muster")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            by_page: dict[int, list] = {}
            for f in findings:
                by_page.setdefault(f["page"], []).append(fitz.Rect(*f["rect"]))
            for pno, rects in by_page.items():
                page = doc[pno - 1]
                for rect in rects:
                    page.add_redact_annot(rect, fill=(0, 0, 0))
                page.apply_redactions()
            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=out,
                metadata={"redactions": len(findings), "by_pattern": counts},
            )
        except Exception as e:
            return _fail(f"Schwärzung fehlgeschlagen: {e}")

    # ── Formulardaten als CSV ─────────────────────────────────

    def export_field_values_csv(self, file_content: bytes) -> PdfToolResult:
        """Feldwerte als CSV (Semikolon, UTF-8-BOM → Excel-tauglich)."""
        fields_result = self.get_form_fields(file_content)
        if not fields_result.success:
            return _fail(fields_result.error or "Formularfelder lesen fehlgeschlagen", "csv")
        fields = (fields_result.metadata or {}).get("fields", [])
        if not fields:
            return _fail("PDF enthält keine Formularfelder", "csv")
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
        writer.writerow(["feldname", "typ", "seite", "wert", "auswahlwerte"])
        for f in fields:
            writer.writerow(
                [
                    f.get("name", ""),
                    f.get("designer_type", f.get("type", "")),
                    f.get("page", ""),
                    str(f.get("value", "")).replace("\n", " "),
                    ", ".join(f.get("options") or []),
                ]
            )
        return PdfToolResult(
            success=True,
            output_format="csv",
            file_content=buf.getvalue().encode("utf-8-sig"),
            metadata={"fields": len(fields)},
        )

    def export_values_template_csv(self, file_content: bytes) -> PdfToolResult:
        """Vorlage für die Serienbefüllung: Kopfzeile mit allen Feldnamen."""
        fields_result = self.get_form_fields(file_content)
        if not fields_result.success:
            return _fail(fields_result.error or "Formularfelder lesen fehlgeschlagen", "csv")
        names = [f.get("name", "") for f in (fields_result.metadata or {}).get("fields", [])]
        if not names:
            return _fail("PDF enthält keine Formularfelder", "csv")
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=";", lineterminator="\r\n")
        writer.writerow(["dateiname"] + names)
        writer.writerow(["formular_1"] + ["" for _ in names])
        return PdfToolResult(
            success=True,
            output_format="csv",
            file_content=buf.getvalue().encode("utf-8-sig"),
            metadata={"fields": len(names)},
        )

    MAX_CSV_ROWS = 200

    def fill_from_csv(
        self, file_content: bytes, csv_content: bytes, flatten: bool = False
    ) -> PdfToolResult:
        """Serienbefüllung: eine Zeile = ein ausgefülltes PDF.

        Kopfzeile enthält die Feldnamen; die optionale Spalte `dateiname`
        bestimmt den Namen der Ausgabedatei. Mehrere Zeilen ergeben ein ZIP.
        """
        import zipfile

        try:
            text = csv_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = csv_content.decode("cp1252")
            except UnicodeDecodeError:
                return _fail("CSV-Datei ist weder UTF-8 noch Windows-1252", "zip")
        # Trennzeichen aus der Kopfzeile bestimmen (deutsche Exporte nutzen ";")
        header_line = text.splitlines()[0] if text.strip() else ""
        counts = {d: header_line.count(d) for d in (";", ",", "\t")}
        delimiter = max(counts, key=lambda d: counts[d]) if any(counts.values()) else ";"
        rows = list(csv.DictReader(io.StringIO(text), delimiter=delimiter))
        if not rows:
            return _fail("CSV enthält keine Datenzeilen", "zip")
        if len(rows) > self.MAX_CSV_ROWS:
            return _fail(f"Maximal {self.MAX_CSV_ROWS} Datenzeilen pro Aufruf", "zip")

        available = {
            f.get("name")
            for f in (self.get_form_fields(file_content).metadata or {}).get("fields", [])
        }
        if not available:
            return _fail("PDF enthält keine Formularfelder", "zip")
        headers = [h for h in (rows[0].keys()) if h and h.lower() != "dateiname"]
        unknown = [h for h in headers if h not in available]
        warnings = (
            [f"Spalten ohne passendes Feld ignoriert: {', '.join(unknown)}"] if unknown else []
        )

        outputs: list[tuple[str, bytes]] = []
        for i, row in enumerate(rows, start=1):
            values = {k: v for k, v in row.items() if k in available and v not in (None, "")}
            result = self.fill_form(file_content, values, flatten=flatten)
            if not result.success:
                warnings.append(f"Zeile {i}: {result.error}")
                continue
            raw_name = (row.get("dateiname") or row.get("Dateiname") or f"formular_{i}").strip()
            safe = re.sub(r'[\\/:*?"<>|\r\n]+', "_", raw_name)[:100] or f"formular_{i}"
            outputs.append((f"{safe}.pdf", result.file_content))

        if not outputs:
            return PdfToolResult(
                success=False,
                output_format="zip",
                error="Keine Zeile konnte verarbeitet werden",
                warnings=warnings,
            )
        if len(outputs) == 1:
            name, data = outputs[0]
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=data,
                metadata={"rows": 1, "filename": name},
                warnings=warnings,
            )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            seen: dict[str, int] = {}
            for name, data in outputs:
                if name in seen:
                    seen[name] += 1
                    name = name.replace(".pdf", f"_{seen[name]}.pdf")
                else:
                    seen[name] = 1
                zf.writestr(name, data)
            if warnings:
                zf.writestr("hinweise.txt", "\n".join(warnings))
        return PdfToolResult(
            success=True,
            output_format="zip",
            file_content=buf.getvalue(),
            metadata={"rows": len(outputs)},
            warnings=warnings,
        )

    # ── Formular-Designer: Felder anlegen ─────────────────────

    def create_form_fields(
        self, file_content: bytes, fields: list[dict]
    ) -> PdfToolResult:
        """AcroForm-Felder aus einem Designer-Layout in das PDF schreiben.

        Koordinaten sind auf 0–1 normiert (wie im Annotations-Editor), damit
        das Layout unabhängig von der Vorschau-Auflösung gilt. Fehlerhafte
        Einzelfelder brechen den Vorgang nicht ab — sie landen in `warnings`.
        """
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        if not fields:
            return _fail("Keine Felder übergeben")
        if len(fields) > 200:
            return _fail("Maximal 200 Felder pro Aufruf")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            warnings: list[str] = []
            used_names: set[str] = {
                w.field_name
                for i in range(doc.page_count)
                for w in (doc[i].widgets() or [])
                if w.field_name
            }
            created = 0

            # Durchlauf 1: endgültige Feldnamen festlegen. Berechnungen dürfen
            # nur auf Namen zeigen, die es hinterher wirklich gibt.
            final_names: dict[int, str] = {}
            for idx, spec in enumerate(fields):
                name = _field_name_safe(str(spec.get("name", "")), f"feld_{idx + 1}")
                if name in used_names:
                    suffix = 2
                    while f"{name}_{suffix}" in used_names:
                        suffix += 1
                    warnings.append(
                        f"Feld {idx + 1}: Name '{name}' bereits vergeben → '{name}_{suffix}'"
                    )
                    name = f"{name}_{suffix}"
                used_names.add(name)
                final_names[idx] = name
            known_names = set(used_names)
            scripted = False

            # Durchlauf 2: Widgets anlegen
            for idx, spec in enumerate(fields):
                label = f"Feld {idx + 1}"
                try:
                    ftype = str(spec.get("type", "text")).lower()
                    if ftype not in FORM_FIELD_TYPES:
                        warnings.append(f"{label}: unbekannter Typ '{ftype}' übersprungen")
                        continue
                    page_no = int(spec.get("page", 1))
                    if not 1 <= page_no <= doc.page_count:
                        warnings.append(f"{label}: Seite {page_no} existiert nicht")
                        continue
                    page = doc[page_no - 1]
                    prect = page.rect

                    # normierte Geometrie → Seitenkoordinaten, mit Mindestgröße
                    x0, x1 = sorted((float(spec.get("x0", 0)), float(spec.get("x1", 0))))
                    y0, y1 = sorted((float(spec.get("y0", 0)), float(spec.get("y1", 0))))
                    rect = fitz.Rect(
                        prect.x0 + max(0.0, min(1.0, x0)) * prect.width,
                        prect.y0 + max(0.0, min(1.0, y0)) * prect.height,
                        prect.x0 + max(0.0, min(1.0, x1)) * prect.width,
                        prect.y0 + max(0.0, min(1.0, y1)) * prect.height,
                    )
                    if rect.width < 8 or rect.height < 8:
                        warnings.append(f"{label}: zu klein (mindestens 8 × 8 Punkte)")
                        continue

                    name = final_names[idx]

                    widget = fitz.Widget()
                    widget.field_name = name
                    widget.rect = rect
                    widget.text_fontsize = max(4.0, min(72.0, float(spec.get("font_size", 11))))
                    tooltip = str(spec.get("tooltip", "")).strip()
                    if tooltip:
                        widget.field_label = _latin1_safe(tooltip[:200])

                    flags = 0
                    if spec.get("required"):
                        flags |= fitz.PDF_FIELD_IS_REQUIRED
                    if spec.get("readonly"):
                        flags |= fitz.PDF_FIELD_IS_READ_ONLY

                    if ftype in ("text", "textarea"):
                        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
                        if ftype == "textarea":
                            flags |= fitz.PDF_TX_FIELD_IS_MULTILINE
                        widget.field_value = _latin1_safe(str(spec.get("value", "")))
                    elif ftype == "checkbox":
                        widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
                        widget.field_value = bool(spec.get("value")) and str(
                            spec.get("value")
                        ).lower() not in ("false", "off", "0", "")
                    elif ftype in ("dropdown", "listbox"):
                        options = [
                            _latin1_safe(str(o)) for o in (spec.get("options") or []) if str(o).strip()
                        ]
                        if not options:
                            warnings.append(f"{label}: ohne Auswahlwerte übersprungen")
                            continue
                        widget.field_type = (
                            fitz.PDF_WIDGET_TYPE_COMBOBOX
                            if ftype == "dropdown"
                            else fitz.PDF_WIDGET_TYPE_LISTBOX
                        )
                        widget.choice_values = options
                        value = _latin1_safe(str(spec.get("value", "")))
                        widget.field_value = value if value in options else options[0]
                    else:  # signature
                        widget.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE

                    # Formatierung / Berechnung / Wertebereich (nur Textfelder)
                    if ftype in ("text", "textarea"):
                        fmt = spec.get("format") or {}
                        if isinstance(fmt, dict):
                            script = _build_format_script(fmt)
                            if script:
                                widget.script_format = script
                                scripted = True
                        calc = spec.get("calc") or {}
                        if isinstance(calc, dict):
                            script, problem = _build_calc_script(calc, known_names)
                            if problem:
                                warnings.append(f"{label}: {problem} — Feld ohne Berechnung")
                            elif script:
                                widget.script_calc = script
                                # Rechenfelder sind standardmäßig schreibgeschützt,
                                # damit Eingaben das Ergebnis nicht überschreiben
                                if spec.get("calc_readonly", True):
                                    flags |= fitz.PDF_FIELD_IS_READ_ONLY
                                scripted = True
                        rule = spec.get("validate") or {}
                        if isinstance(rule, dict):
                            script = _build_validate_script(rule)
                            if script:
                                widget.script_change = script
                                scripted = True

                    if flags:
                        widget.field_flags = flags
                    page.add_widget(widget)
                    created += 1
                except Exception as e:  # einzelnes Feld darf den Rest nicht kippen
                    warnings.append(f"{label}: {e}")

            if created == 0:
                doc.close()
                return PdfToolResult(
                    success=False,
                    output_format="pdf",
                    error="Kein Feld konnte angelegt werden",
                    warnings=warnings,
                )
            if scripted:
                # Viewer sollen die Darstellung nach Berechnung/Formatierung
                # selbst neu aufbauen
                doc.need_appearances(True)
            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=out,
                metadata={"created": created, "skipped": len(fields) - created},
                warnings=warnings,
            )
        except Exception as e:
            return _fail(f"Formularfelder anlegen fehlgeschlagen: {e}")

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
            embedded_fonts: set[str] = set()
            fallbacks = 0

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
                for idx, edit in enumerate(page_edits):
                    original = str(edit.get("text", ""))
                    if not original.strip():
                        continue  # leerer Text = Block nur entfernen

                    # Schrift des Originalblocks fortführen und einbetten
                    font_file = select_font_file(str(edit.get("font", "")), original)
                    if font_file:
                        text = original
                        alias = f"E{page_num}_{idx}"
                        try:
                            page.insert_font(fontname=alias, fontfile=font_file)
                            fontname = alias
                            embedded_fonts.add(Path(font_file).stem)
                        except Exception:
                            fontname, text = "helv", _latin1_safe(original)
                            fallbacks += 1
                    else:
                        fontname, text = "helv", _latin1_safe(original)
                        fallbacks += 1
                    if fontname == "helv" and text != original:
                        warnings.append(
                            f"Seite {page_num}: keine einbettbare Schrift gefunden — "
                            "Sonderzeichen wurden ersetzt"
                        )

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
                            r, text, fontsize=size, fontname=fontname, color=rgb, align=0
                        )
                        if leftover >= 0:
                            placed = True
                            break
                        size -= 0.5
                    if not placed:
                        # letzter Versuch: minimal klein, Box leicht vergrößert
                        bigger = fitz.Rect(r.x0, r.y0, r.x1, min(r.y1 + 14, rect.height))
                        page.insert_textbox(
                            bigger, text, fontsize=5, fontname=fontname, color=rgb, align=0
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
                metadata={
                    "edits": len(edits),
                    "fonts_embedded": sorted(embedded_fonts),
                    "fallback_blocks": fallbacks,
                },
                warnings=warnings,
            )
        except Exception as e:
            return _fail(f"Textbearbeitung fehlgeschlagen: {e}")

    # ── Digitale Signatur (pyHanko, PAdES) ────────────────────

    def sign_digital(
        self,
        file_content: bytes,
        p12_content: bytes,
        passphrase: str,
        reason: str = "",
        location: str = "",
        tsa_url: str = "",
    ) -> PdfToolResult:
        """Zertifikatsbasierte Signatur mit einem PKCS#12-Zertifikat (.p12/.pfx).

        Zertifikat und Passphrase werden ausschließlich transient verwendet —
        weder persistiert noch geloggt (auch nicht in Fehlerpfaden).
        """
        if not PYHANKO_AVAILABLE:
            return _fail("pyHanko nicht verfügbar — digitale Signatur deaktiviert")
        try:
            # load_pkcs12 erwartet einen Pfad — transiente Tempdatei,
            # nach dem with-Block sofort gelöscht
            with tempfile.TemporaryDirectory() as tmp:
                p12_path = Path(tmp) / "cert.p12"
                p12_path.write_bytes(p12_content)
                signer = _pyhanko_signers.SimpleSigner.load_pkcs12(
                    str(p12_path),
                    passphrase=passphrase.encode() if passphrase else None,
                )
        except Exception:
            # Bewusst ohne Detail: Fehlermeldungen könnten Zertifikatsdaten tragen
            return _fail("Zertifikat konnte nicht geladen werden — Datei oder Passwort prüfen")
        if signer is None:
            return _fail("Zertifikat konnte nicht geladen werden — Datei oder Passwort prüfen")
        try:
            from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

            writer = IncrementalPdfFileWriter(io.BytesIO(file_content))
            meta = _pyhanko_signers.PdfSignatureMetadata(
                field_name="Signatur1",
                reason=reason or None,
                location=location or None,
            )
            timestamper = None
            if tsa_url:
                from pyhanko.sign.timestamps import HTTPTimeStamper

                timestamper = HTTPTimeStamper(tsa_url)
            out = _pyhanko_signers.sign_pdf(
                writer, meta, signer=signer, timestamper=timestamper
            )
            return PdfToolResult(
                success=True, output_format="pdf", file_content=out.getvalue()
            )
        except Exception as e:
            logger.warning("Digitale Signatur fehlgeschlagen: %s", type(e).__name__)
            return _fail("Signieren fehlgeschlagen — ist das PDF bereits abschließend signiert?")

    # ── Scan-Optimierung (OCRmyPDF) ───────────────────────────

    def scan_optimize(
        self,
        file_content: bytes,
        language: str = "deu",
        deskew: bool = True,
        rotate_pages: bool = True,
        force_ocr: bool = False,
        clean: bool = False,
    ) -> PdfToolResult:
        """Gescannte PDFs aufbereiten: geraderücken, Seiten drehen, OCR-Textebene."""
        if not OCRMYPDF_AVAILABLE:
            return _fail("OCRmyPDF/Ghostscript nicht verfügbar — Scan-Optimierung deaktiviert")
        allowed_langs = {"deu", "eng", "fra", "ita", "spa", "nld", "pol"}
        parts = [p for p in language.split("+") if p in allowed_langs]
        language = "+".join(parts) if parts else "deu"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "in.pdf"
                dst = Path(tmp) / "out.pdf"
                src.write_bytes(file_content)
                _ocrmypdf.ocr(
                    str(src),
                    str(dst),
                    language=language,
                    deskew=deskew,
                    rotate_pages=rotate_pages,
                    force_ocr=force_ocr,
                    clean=clean,
                    skip_text=not force_ocr,
                    output_type="pdf",
                    progress_bar=False,
                    tesseract_timeout=120,  # pro Seite — begrenzt CPU-Bindung
                )
                return PdfToolResult(
                    success=True, output_format="pdf", file_content=dst.read_bytes()
                )
        except Exception as e:
            return _fail(f"Scan-Optimierung fehlgeschlagen: {e}")

    # ── Batch-Verarbeitung ────────────────────────────────────

    BATCH_OPERATIONS = (
        "compress",
        "rotate",
        "protect",
        "bates",
        "pdfa",
        "watermark",
        "clean",
        "sign",
        "rename",
    )

    def batch_apply(
        self,
        files: list[tuple[str, bytes]],
        operation: str,
        params: dict,
        certificate: tuple[bytes, str] | None = None,
    ) -> PdfToolResult:
        """Eine Operation auf mehrere Dateien anwenden, Ergebnis als ZIP.

        Fehler einzelner Dateien brechen den Batch nicht ab — sie landen als
        fehler.txt im ZIP.
        """
        import zipfile

        from app.services.pdf_tools_service import get_pdf_tools

        if operation not in self.BATCH_OPERATIONS:
            return _fail(f"Unbekannte Operation: {operation}", "zip")
        tools = get_pdf_tools()
        errors: list[str] = []
        ok = 0
        buf = io.BytesIO()
        bates_counter = int(params.get("start", 1))
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for filename, content in files:
                base = filename.rsplit(".", 1)[0]
                try:
                    if operation == "compress":
                        result = tools.compress_pdf(
                            content, quality=params.get("quality", "medium")
                        )
                        suffix = "_komprimiert"
                    elif operation == "rotate":
                        import fitz as _fitz

                        angle = int(params.get("rotation", 90))
                        with _fitz.open(stream=content, filetype="pdf") as d:
                            rotations = {p: angle for p in range(1, d.page_count + 1)}
                        result = tools.rotate_pages(content, rotations)
                        suffix = "_rotiert"
                    elif operation == "protect":
                        result = self.protect_pdf_delegate(
                            content, params.get("password", "")
                        )
                        suffix = "_geschuetzt"
                    elif operation == "bates":
                        result = self.add_bates_numbers(
                            content,
                            prefix=params.get("prefix", ""),
                            start=bates_counter,
                            digits=int(params.get("digits", 6)),
                            position=params.get("position", "bottom-right"),
                        )
                        if result.success:
                            # fortlaufend über alle Dateien hinweg
                            import fitz as _fitz

                            with _fitz.open(stream=content, filetype="pdf") as d:
                                bates_counter += d.page_count
                        suffix = "_bates"
                    elif operation == "watermark":
                        result = tools.add_watermark(
                            content,
                            text=params.get("text", "ENTWURF"),
                            opacity=float(params.get("opacity", 0.3)),
                            rotation=int(params.get("rotation", -45)),
                            font_size=int(params.get("font_size", 60)),
                        )
                        suffix = "_wasserzeichen"
                    elif operation == "clean":
                        from app.services.pdf_more_service import get_pdf_more

                        result = get_pdf_more().clean_pdf(content)
                        suffix = "_bereinigt"
                    elif operation == "sign":
                        if not certificate:
                            errors.append(f"{filename}: kein Zertifikat übergeben")
                            continue
                        p12, passphrase = certificate
                        result = self.sign_digital(
                            content,
                            p12,
                            passphrase,
                            reason=params.get("reason", ""),
                            location=params.get("location", ""),
                            tsa_url=params.get("tsa_url", ""),
                        )
                        suffix = "_signiert"
                    elif operation == "rename":
                        # Nur umbenennen: Inhalt unverändert ins ZIP
                        pattern = str(params.get("pattern", "{name}"))[:120]
                        digits = max(1, min(8, int(params.get("digits", 3))))
                        start = int(params.get("start", 1))
                        new_base = (
                            pattern.replace("{name}", base)
                            .replace("{n}", f"{start + ok:0{digits}d}")
                            .strip()
                        )
                        new_base = re.sub(r'[\\/:*?"<>|\r\n]+', "_", new_base)[:100] or base
                        zf.writestr(f"{new_base}.pdf", content)
                        ok += 1
                        continue
                    else:  # pdfa
                        result = self.convert_pdfa(
                            content, level=params.get("level", "2b")
                        )
                        suffix = "_pdfa"

                    if result.success and result.file_content:
                        zf.writestr(f"{base}{suffix}.pdf", result.file_content)
                        ok += 1
                    else:
                        errors.append(f"{filename}: {result.error}")
                except Exception as e:
                    errors.append(f"{filename}: {e}")
            if errors:
                zf.writestr("fehler.txt", "\n".join(errors))
        return PdfToolResult(
            success=ok > 0,
            output_format="zip",
            file_content=buf.getvalue(),
            metadata={"ok": ok, "failed": len(errors)},
            warnings=errors,
            error=None if ok > 0 else "Keine Datei konnte verarbeitet werden",
        )

    def protect_pdf_delegate(self, content: bytes, password: str) -> PdfToolResult:
        """Batch-Helfer: Passwortschutz über den pdf_tools-Service."""
        from app.services.pdf_tools_service import get_pdf_tools

        if not password:
            return _fail("Passwort erforderlich")
        return get_pdf_tools().protect_pdf(content, password)

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
