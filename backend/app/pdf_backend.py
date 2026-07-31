"""Einziger Zugangspunkt zu den Fremdbibliotheken der Dokumentverarbeitung.

Warum es dieses Modul gibt
--------------------------
Die Anwendung stützt sich auf Bibliotheken, die niemand hier selbst schreiben
könnte: PyMuPDF (Python-Hülle über die C-Bibliothek MuPDF), pikepdf (über
qpdf), pyHanko für Signaturen, OCRmyPDF, dazu die externen Programme
Ghostscript, LibreOffice, Tesseract und qpdf. Das ist eine bewusste
Entscheidung — ein selbst gebauter PDF-Parser wäre gegenüber diesen
jahrzehntelang gehärteten Implementierungen auch sicherheitstechnisch ein
Rückschritt.

Die Abhängigkeit wird deshalb nicht vermieden, sondern **eingefasst**:

1. **Ein Importpunkt.** Kein Service importiert `fitz` oder `pikepdf` mehr
   selbst; alle beziehen sie von hier. Ein Versionswechsel, ein Austausch
   oder eine Notabschaltung trifft eine Datei statt sieben.
2. **Eine Verfügbarkeitserkennung.** Vorher hatte jeder Service eigene
   `try/except ImportError`-Blöcke mit eigenen Flags — sechs Stellen, die
   auseinanderlaufen konnten. Jetzt steht die Erkennung einmal hier, inklusive
   der externen Programme (die Suche im PATH kostet Zeit und wird gemerkt).
3. **Ein Register.** `DEPENDENCIES` beschreibt zu jeder Komponente, wofür sie
   gebraucht wird, unter welcher Lizenz sie steht und wodurch sie sich
   ersetzen ließe. Das Register speist die Lizenzseite der Anwendung und ist
   damit die Grundlage der AGPL-Pflichtangaben — nicht ein Dokument, das
   irgendwann veraltet.

Was dieses Modul **nicht** ist: eine Abstraktionsschicht, die jede
PyMuPDF-Funktion nachbaut. Die Services rufen `fitz` weiterhin direkt auf
(146 Stellen) — eine vollständige Fassade wäre eine zweite Bibliothek mit
eigenen Fehlern und würde die Abhängigkeit nur verstecken, nicht verringern.
Eingefasst sind der Zugang, die Erkennung und die Buchführung; die
fachlichen Aufrufe bleiben sichtbar da, wo sie fachlich hingehören.
"""

import shutil
from dataclasses import dataclass, field
from typing import Any

# ── Python-Bibliotheken ───────────────────────────────────────

try:
    import fitz  # PyMuPDF

    PYMUPDF_AVAILABLE = True
except ImportError:  # pragma: no cover — nur ohne installierte Bibliothek
    fitz = None  # type: ignore[assignment]
    PYMUPDF_AVAILABLE = False

try:
    import pikepdf

    PIKEPDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    pikepdf = None  # type: ignore[assignment]
    PIKEPDF_AVAILABLE = False

try:
    from PIL import Image  # noqa: F401

    PILLOW_AVAILABLE = True
except ImportError:  # pragma: no cover
    PILLOW_AVAILABLE = False

try:
    import docx  # noqa: F401  — python-docx

    DOCX_AVAILABLE = True
except ImportError:  # pragma: no cover
    DOCX_AVAILABLE = False

try:
    import openpyxl  # noqa: F401

    OPENPYXL_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENPYXL_AVAILABLE = False

try:
    from pyhanko.sign import signers as pyhanko_signers  # noqa: F401

    PYHANKO_AVAILABLE = True
except ImportError:  # pragma: no cover
    pyhanko_signers = None  # type: ignore[assignment]
    PYHANKO_AVAILABLE = False

try:
    from pyhanko.pdf_utils.reader import PdfFileReader as HankoReader  # noqa: F401
    from pyhanko.sign.validation import validate_pdf_signature  # noqa: F401
    from pyhanko.sign.validation.settings import KeyUsageConstraints  # noqa: F401

    PYHANKO_VALIDATION_AVAILABLE = True
except ImportError:  # pragma: no cover
    HankoReader = None  # type: ignore[assignment]
    validate_pdf_signature = None  # type: ignore[assignment]
    KeyUsageConstraints = None  # type: ignore[assignment]
    PYHANKO_VALIDATION_AVAILABLE = False

try:
    import ocrmypdf  # noqa: F401

    _OCRMYPDF_IMPORTED = True
except ImportError:  # pragma: no cover
    ocrmypdf = None  # type: ignore[assignment]
    _OCRMYPDF_IMPORTED = False


# ── Externe Programme ─────────────────────────────────────────
#
# `shutil.which` durchsucht den PATH — einmal beim Import, nicht bei jedem
# Aufruf. Die Installation ändert sich zur Laufzeit des Containers nicht.

GHOSTSCRIPT_BIN = shutil.which("gs")
SOFFICE_BIN = shutil.which("libreoffice") or shutil.which("soffice")
TESSERACT_BIN = shutil.which("tesseract")
QPDF_BIN = shutil.which("qpdf")

# OCRmyPDF ruft Ghostscript zur Laufzeit auf — ohne das Programm nützt die
# installierte Bibliothek nichts.
OCRMYPDF_AVAILABLE = _OCRMYPDF_IMPORTED and bool(GHOSTSCRIPT_BIN)


# ── Abhängigkeitsregister ─────────────────────────────────────


@dataclass(frozen=True)
class Dependency:
    """Eine Fremdkomponente mit allem, was für die Pflichtangaben nötig ist."""

    key: str
    name: str
    kind: str  # "bibliothek" | "programm" | "rahmenwerk"
    purpose: str
    license: str
    url: str
    #: Wodurch sich die Komponente ersetzen ließe — leer, wenn es keinen
    #: realistischen Ersatz gibt.
    alternative: str = ""
    #: Verlangt die Lizenz, dass Nutzerinnen und Nutzer des Netzdienstes den
    #: Quelltext bekommen? (AGPL § 13)
    copyleft_network: bool = False
    available: bool = field(default=True)


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency(
        key="pymupdf",
        name="PyMuPDF (MuPDF)",
        kind="bibliothek",
        purpose=(
            "Kern der PDF-Verarbeitung: Seiten lesen und schreiben, Text und "
            "Bilder extrahieren, Anmerkungen, Formularfelder, Schwärzen, "
            "Rendern der Vorschau"
        ),
        license="AGPL-3.0 oder kommerzielle Artifex-Lizenz",
        url="https://pymupdf.readthedocs.io/",
        alternative=(
            "pikepdf/qpdf deckt Struktur und Verschlüsselung ab, aber kein "
            "Rendern und keine Textextraktion"
        ),
        copyleft_network=True,
        available=PYMUPDF_AVAILABLE,
    ),
    Dependency(
        key="pikepdf",
        name="pikepdf (qpdf)",
        kind="bibliothek",
        purpose="Verschlüsselung, Rechteverwaltung, Metadaten-Datumsfelder",
        license="MPL-2.0",
        url="https://pikepdf.readthedocs.io/",
        alternative="PyMuPDF beherrscht Teile davon",
        available=PIKEPDF_AVAILABLE,
    ),
    Dependency(
        key="pyhanko",
        name="pyHanko",
        kind="bibliothek",
        purpose="Digitale Signatur (PAdES) und Signaturprüfung",
        license="MIT",
        url="https://pyhanko.readthedocs.io/",
        alternative="endesive; für die Prüfung auch OpenSSL-basiert selbst gebaut",
        available=PYHANKO_AVAILABLE or PYHANKO_VALIDATION_AVAILABLE,
    ),
    Dependency(
        key="ocrmypdf",
        name="OCRmyPDF",
        kind="bibliothek",
        purpose="Scan-Optimierung: Geraderücken, Auto-Drehen, Textebene anlegen",
        license="MPL-2.0",
        url="https://ocrmypdf.readthedocs.io/",
        alternative="Tesseract direkt ansteuern (ohne Vor- und Nachbereitung)",
        available=OCRMYPDF_AVAILABLE,
    ),
    Dependency(
        key="pillow",
        name="Pillow",
        kind="bibliothek",
        purpose="Bildverarbeitung bei Bilder→PDF und Wasserzeichen",
        license="MIT-CMU",
        url="https://python-pillow.org/",
        available=PILLOW_AVAILABLE,
    ),
    Dependency(
        key="python_docx",
        name="python-docx",
        kind="bibliothek",
        purpose="Word-Dateien lesen, verbinden, vergleichen, Metadaten",
        license="MIT",
        url="https://python-docx.readthedocs.io/",
        available=DOCX_AVAILABLE,
    ),
    Dependency(
        key="openpyxl",
        name="openpyxl",
        kind="bibliothek",
        purpose="Excel-Metadaten und Tabellenexport",
        license="MIT",
        url="https://openpyxl.readthedocs.io/",
        available=OPENPYXL_AVAILABLE,
    ),
    Dependency(
        key="ghostscript",
        name="Ghostscript",
        kind="programm",
        purpose="PDF/A-Konvertierung; wird von OCRmyPDF mitbenutzt",
        license="AGPL-3.0 oder kommerzielle Artifex-Lizenz",
        url="https://www.ghostscript.com/",
        alternative="veraPDF prüft PDF/A, konvertiert aber nicht",
        copyleft_network=True,
        available=bool(GHOSTSCRIPT_BIN),
    ),
    Dependency(
        key="libreoffice",
        name="LibreOffice",
        kind="programm",
        purpose="Office-Dateien (Word, Excel, PowerPoint, ODF, RTF, HTML) nach PDF",
        license="MPL-2.0",
        url="https://www.libreoffice.org/",
        alternative="kein gleichwertiger freier Ersatz",
        available=bool(SOFFICE_BIN),
    ),
    Dependency(
        key="tesseract",
        name="Tesseract OCR",
        kind="programm",
        purpose="Texterkennung in gescannten Dokumenten",
        license="Apache-2.0",
        url="https://tesseract-ocr.github.io/",
        available=bool(TESSERACT_BIN),
    ),
    Dependency(
        key="qpdf",
        name="qpdf",
        kind="programm",
        purpose="Unterbau von pikepdf (als eigenes Programm optional)",
        license="Apache-2.0",
        url="https://qpdf.sourceforge.io/",
        available=bool(QPDF_BIN),
    ),
    Dependency(
        key="fastapi",
        name="FastAPI / Starlette / uvicorn",
        kind="rahmenwerk",
        purpose="Web-Schnittstelle des Backends",
        license="MIT / BSD-3-Clause",
        url="https://fastapi.tiangolo.com/",
        alternative="jedes ASGI-Rahmenwerk",
    ),
    Dependency(
        key="vue",
        name="Vue 3 / Vue Router / Vite",
        kind="rahmenwerk",
        purpose="Oberfläche im Browser",
        license="MIT",
        url="https://vuejs.org/",
        alternative="jedes Komponenten-Rahmenwerk",
    ),
    Dependency(
        key="pdfjs",
        name="pdf.js",
        kind="bibliothek",
        purpose="Anzeige der PDF-Seiten im Browser — die Datei bleibt dabei lokal",
        license="Apache-2.0",
        url="https://mozilla.github.io/pdf.js/",
        alternative="serverseitiges Rendern (war der frühere Weg, langsamer)",
    ),
    Dependency(
        key="jszip",
        name="JSZip",
        kind="bibliothek",
        purpose="ZIP-Bündel der Sitzungsergebnisse und Sitzungsdateien im Browser",
        license="MIT oder GPL-3.0",
        url="https://stuk.github.io/jszip/",
        available=True,
    ),
)


def dependency_report() -> list[dict[str, Any]]:
    """Register als einfache Datenstruktur — Grundlage der Lizenzseite."""
    return [
        {
            "key": d.key,
            "name": d.name,
            "kind": d.kind,
            "purpose": d.purpose,
            "license": d.license,
            "url": d.url,
            "alternative": d.alternative,
            "copyleft_network": d.copyleft_network,
            "available": d.available,
        }
        for d in DEPENDENCIES
    ]


def requires_source_disclosure() -> bool:
    """Ist mindestens eine Komponente mit Netzwerk-Copyleft im Einsatz?

    Nur dann greift die Pflicht aus AGPL § 13, den Quelltext für Nutzerinnen
    und Nutzer des Dienstes bereitzustellen. Die Lizenzseite blendet den
    entsprechenden Hinweis abhängig davon ein — würde PyMuPDF eines Tages
    durch eine permissiv lizenzierte Bibliothek ersetzt, verschwindet er von
    selbst, statt als falsche Angabe stehen zu bleiben.
    """
    return any(d.copyleft_network and d.available for d in DEPENDENCIES)


def open_pdf(content: bytes):
    """PDF aus dem Arbeitsspeicher öffnen — der einzige Einstieg in ein Dokument.

    Bewusst als Funktion und nicht als direkter `fitz.open`-Aufruf in den
    Services: Wenn eine Ablösung ansteht, ist hier die Stelle, an der ein
    anderes Backend ein kompatibles Dokumentobjekt liefern müsste. Auch das
    Versprechen „nur im Arbeitsspeicher" ist damit an einer Stelle ablesbar —
    es gibt keinen Pfad, auf dem eine Nutzerdatei ins Dateisystem gelangt.
    """
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF nicht verfügbar")
    return fitz.open(stream=content, filetype="pdf")
