"""Werkzeug-Katalog: verbindet die Kacheln der Oberfläche mit ihren Endpunkten.

Der Katalog ist die einzige Quelle dafür, welche Werkzeuge es gibt und welche
API-Pfade zu einem Werkzeug gehören. Damit kann der Administrator einzelne
Werkzeuge auf angemeldete Nutzer beschränken (siehe app/tool_access.py) und die
Beschränkung wird serverseitig durchgesetzt — nicht nur in der Oberfläche.

Bewusst NICHT im Katalog: gemeinsam genutzte Lese-/Vorschau-Endpunkte
(Thumbnails, Metadaten lesen, Formularfelder lesen, TOC lesen, Bilder
auflisten). Sie gehören zu keinem einzelnen Werkzeug und werden von mehreren
Ansichten für die Vorschau gebraucht; gesperrt wird die eigentliche Aktion.

Pfade mit abschließendem "/" gelten als Präfix (z.B. parametrisierte Routen).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolEntry:
    id: str
    label: str
    group: str
    paths: tuple[str, ...]


_PDF = "PDF"
_OFFICE = "Word & Excel"

TOOL_CATALOG: tuple[ToolEntry, ...] = (
    ToolEntry("textEditor", "Text bearbeiten", _PDF, ("/api/pdf-extras/edit-text-blocks",)),
    ToolEntry("annotate", "Anmerkungen", _PDF, ("/api/pdf-editor/annotations",)),
    ToolEntry("merge", "Zusammenführen", _PDF, ("/api/pdf-tools/merge",)),
    ToolEntry("split", "Teilen", _PDF, ("/api/pdf-tools/split",)),
    ToolEntry("rotate", "Rotieren", _PDF, ("/api/pdf-tools/rotate",)),
    ToolEntry("toImages", "PDF → Bilder", _PDF, ("/api/pdf-tools/to-images",)),
    ToolEntry("compress", "Komprimieren", _PDF, ("/api/pdf-tools/compress",)),
    ToolEntry("watermark", "Wasserzeichen", _PDF, ("/api/pdf-tools/watermark",)),
    ToolEntry("imagesToPdf", "Bilder → PDF", _PDF, ("/api/pdf-tools/images-to-pdf",)),
    ToolEntry("pageEditor", "Seiten ordnen", _PDF, ("/api/pdf-tools/page-operations",)),
    ToolEntry("insertBlank", "Leere Seiten", _PDF, ("/api/pdf-more/insert-blank",)),
    ToolEntry(
        "pdfCompare",
        "PDF Vergleich",
        _PDF,
        ("/api/pdf-editor/compare", "/api/pdf-extras/jobs/compare"),
    ),
    ToolEntry("ocr", "OCR", _PDF, ("/api/pdf-editor/ocr", "/api/pdf-extras/jobs/ocr")),
    ToolEntry(
        "protect",
        "Schützen / Entsperren",
        _PDF,
        ("/api/pdf-tools/protect", "/api/pdf-tools/unlock"),
    ),
    ToolEntry("permissions", "Rechteverwaltung", _PDF, ("/api/pdf-more/permissions",)),
    ToolEntry("clean", "Bereinigen", _PDF, ("/api/pdf-more/clean",)),
    ToolEntry("pdfToWord", "PDF → Word", _PDF, ("/api/pdf-convert/to-word",)),
    ToolEntry(
        "pdfToExcel",
        "PDF → Excel",
        _PDF,
        ("/api/pdf-convert/to-excel", "/api/pdf-convert/to-excel/preview"),
    ),
    ToolEntry(
        "pdfExport",
        "PDF exportieren",
        _PDF,
        ("/api/pdf-more/export/", "/api/pdf-more/to-csv"),
    ),
    ToolEntry("metadata", "Metadaten", _PDF, ("/api/pdf-tools/metadata",)),
    ToolEntry("toText", "PDF → Text", _PDF, ("/api/pdf-extras/to-text",)),
    ToolEntry(
        "searchReplace",
        "Suchen & Ersetzen",
        _PDF,
        (
            "/api/pdf-editor/text/replace",
            "/api/pdf-editor/text/insert",
            "/api/pdf-editor/text/search",
        ),
    ),
    ToolEntry(
        "redact",
        "Schwärzen",
        _PDF,
        ("/api/pdf-extras/redact", "/api/pdf-extras/redact-patterns"),
    ),
    ToolEntry("pageNumbers", "Seitenzahlen", _PDF, ("/api/pdf-editor/page-numbers",)),
    ToolEntry("headerFooter", "Kopf-/Fußzeile", _PDF, ("/api/pdf-editor/header-footer",)),
    ToolEntry("bates", "Bates-Nummern", _PDF, ("/api/pdf-extras/bates",)),
    ToolEntry("pruefakte", "Prüfakte", _PDF, ("/api/pdf-more/pruefakte",)),
    ToolEntry("formDesigner", "Formular-Designer", _PDF, ("/api/pdf-extras/form/create",)),
    ToolEntry(
        "formFill",
        "Formular ausfüllen",
        _PDF,
        (
            "/api/pdf-extras/form/fill",
            "/api/pdf-extras/form/fill-csv",
            "/api/pdf-extras/form/export-csv",
        ),
    ),
    ToolEntry("signImage", "Unterschrift", _PDF, ("/api/pdf-extras/sign-image",)),
    ToolEntry("imageReplace", "Bild ersetzen", _PDF, ("/api/pdf-more/images/replace",)),
    ToolEntry("pdfa", "PDF/A", _PDF, ("/api/pdf-extras/to-pdfa",)),
    ToolEntry("flatten", "Einbrennen", _PDF, ("/api/pdf-editor/flatten",)),
    ToolEntry("signDigital", "Digital signieren", _PDF, ("/api/pdf-extras/sign-digital",)),
    ToolEntry(
        "verifySignatures", "Signatur prüfen", _PDF, ("/api/pdf-more/verify-signatures",)
    ),
    ToolEntry(
        "scanOptimize",
        "Scan optimieren",
        _PDF,
        ("/api/pdf-extras/scan-optimize", "/api/pdf-extras/jobs/scan-optimize"),
    ),
    ToolEntry("qualityCheck", "Qualitätsprüfung", _PDF, ("/api/pdf-more/quality-check",)),
    ToolEntry("batch", "Batch", _PDF, ("/api/pdf-extras/batch",)),
    ToolEntry(
        "tocEditor",
        "Lesezeichen",
        _PDF,
        ("/api/pdf-editor/toc/write", "/api/pdf-editor/toc/auto-detect"),
    ),
    ToolEntry("aiAssistant", "KI-Assistent", _PDF, ("/api/pdf-more/ai/",)),
    ToolEntry("officeToPdf", "Office → PDF", _OFFICE, ("/api/pdf-more/office-to-pdf",)),
    ToolEntry("wordToPdf", "Word → PDF", _OFFICE, ("/api/pdf-tools/word-to-pdf",)),
    ToolEntry("wordMerge", "Word verbinden", _OFFICE, ("/api/pdf-tools/word-merge",)),
    ToolEntry("wordDiff", "Word Vergleich", _OFFICE, ("/api/pdf-tools/word-diff",)),
    ToolEntry("wordMeta", "Word Metadaten", _OFFICE, ("/api/pdf-tools/word-metadata",)),
    ToolEntry("excelMeta", "Excel Metadaten", _OFFICE, ("/api/pdf-tools/excel-metadata",)),
)

TOOL_IDS: frozenset[str] = frozenset(t.id for t in TOOL_CATALOG)

_EXACT: dict[str, str] = {
    path: tool.id for tool in TOOL_CATALOG for path in tool.paths if not path.endswith("/")
}
_PREFIX: tuple[tuple[str, str], ...] = tuple(
    (path, tool.id) for tool in TOOL_CATALOG for path in tool.paths if path.endswith("/")
)


def resolve_tool(path: str) -> str | None:
    """Werkzeug-ID zu einem Request-Pfad — None für gemeinsame Endpunkte."""
    tool = _EXACT.get(path)
    if tool:
        return tool
    for prefix, tool_id in _PREFIX:
        if path.startswith(prefix):
            return tool_id
    return None
