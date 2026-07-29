"""Weitere Werkzeuge (Modulkatalog-Ausbau): Konvertierungen, Bereinigung,
Rechte, Signaturprüfung, Prüfakte, Qualitätsprüfung, lokale KI.

Alles in-memory bzw. mit automatisch gelöschten TemporaryDirectories.
KI-Funktionen sprechen ausschließlich den konfigurierten lokalen
OpenAI-kompatiblen Endpoint an (PDFAPP_LLM_URL) — keine Cloud.
"""

import csv
import hashlib
import io
import logging
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import httpx

from app.config import settings
from app.services.pdf_tools_service import PdfToolResult

logger = logging.getLogger(__name__)

try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pikepdf

    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

try:
    from pyhanko.pdf_utils.reader import PdfFileReader as _HankoReader
    from pyhanko.sign.validation import validate_pdf_signature as _validate_sig
    from pyhanko.sign.validation.settings import KeyUsageConstraints

    PYHANKO_VALIDATION_AVAILABLE = True
except ImportError:
    PYHANKO_VALIDATION_AVAILABLE = False

SOFFICE_BIN = shutil.which("libreoffice") or shutil.which("soffice")

OFFICE_EXTENSIONS = {".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp", ".html", ".htm", ".rtf", ".txt"}


def _fail(msg: str, fmt: str = "pdf") -> PdfToolResult:
    return PdfToolResult(success=False, output_format=fmt, error=msg)


class PdfMoreService:
    def check_features(self) -> dict[str, bool]:
        return {
            "office_to_pdf": bool(SOFFICE_BIN),
            "pdf_export_formats": PYMUPDF_AVAILABLE,
            "pdf_to_csv": PYMUPDF_AVAILABLE,
            "clean_pdf": PYMUPDF_AVAILABLE,
            "permissions": PIKEPDF_AVAILABLE,
            "verify_signatures": PYHANKO_VALIDATION_AVAILABLE,
            "insert_blank": PYMUPDF_AVAILABLE,
            "pruefakte": PYMUPDF_AVAILABLE,
            "quality_check": PYMUPDF_AVAILABLE,
            "ai": bool(settings.llm_url),
        }

    # ── Office/HTML → PDF (LibreOffice headless) ──────────────

    def office_to_pdf(self, file_content: bytes, extension: str) -> PdfToolResult:
        if not SOFFICE_BIN:
            return _fail("LibreOffice nicht verfügbar")
        ext = extension.lower()
        if ext not in OFFICE_EXTENSIONS:
            return _fail(f"Dateityp {ext} wird nicht unterstützt")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / f"eingabe{ext}"
                src.write_bytes(file_content)
                proc = subprocess.run(
                    [SOFFICE_BIN, "--headless", "--convert-to", "pdf", "--outdir", tmp, str(src)],
                    capture_output=True,
                    timeout=180,
                )
                out = Path(tmp) / "eingabe.pdf"
                if proc.returncode != 0 or not out.exists():
                    return _fail("Konvertierung fehlgeschlagen")
                return PdfToolResult(
                    success=True, output_format="pdf", file_content=out.read_bytes()
                )
        except subprocess.TimeoutExpired:
            return _fail("Konvertierung: Zeitlimit überschritten")
        except Exception as e:
            return _fail(f"Konvertierung fehlgeschlagen: {e}")

    # ── PDF → Markdown / HTML / JSON / CSV ────────────────────

    def export_text_format(self, file_content: bytes, fmt: str) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar", fmt)
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            if fmt == "html":
                parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"]
                for i in range(doc.page_count):
                    parts.append(f"<!-- Seite {i + 1} -->")
                    parts.append(doc[i].get_text("xhtml"))
                parts.append("</body></html>")
                data = "\n".join(parts).encode("utf-8")
            elif fmt == "json":
                import json as _json

                pages = []
                for i in range(doc.page_count):
                    d = doc[i].get_text("dict")
                    blocks = []
                    for b in d.get("blocks", []):
                        if b.get("type") != 0:
                            continue
                        text = " ".join(
                            s.get("text", "")
                            for line in b.get("lines", [])
                            for s in line.get("spans", [])
                        ).strip()
                        if text:
                            blocks.append({"bbox": list(b.get("bbox", [])), "text": text})
                    pages.append({"page": i + 1, "blocks": blocks})
                data = _json.dumps({"pages": pages}, ensure_ascii=False, indent=1).encode("utf-8")
            elif fmt == "markdown":
                # Überschriften-Heuristik über Schriftgrößen
                sizes: list[float] = []
                for i in range(doc.page_count):
                    for b in doc[i].get_text("dict").get("blocks", []):
                        for line in b.get("lines", []):
                            for s in line.get("spans", []):
                                if s.get("text", "").strip():
                                    sizes.append(round(s.get("size", 0), 1))
                body_size = max(set(sizes), key=sizes.count) if sizes else 11
                lines_out: list[str] = []
                for i in range(doc.page_count):
                    for b in doc[i].get_text("dict").get("blocks", []):
                        if b.get("type") != 0:
                            continue
                        for line in b.get("lines", []):
                            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
                            if not spans:
                                continue
                            text = "".join(s.get("text", "") for s in spans).strip()
                            size = max(s.get("size", body_size) for s in spans)
                            bold = any(("Bold" in s.get("font", "")) for s in spans)
                            if size >= body_size * 1.6:
                                lines_out.append(f"# {text}")
                            elif size >= body_size * 1.3:
                                lines_out.append(f"## {text}")
                            elif size >= body_size * 1.15 or (bold and size > body_size):
                                lines_out.append(f"### {text}")
                            else:
                                lines_out.append(text)
                        lines_out.append("")
                data = "\n".join(lines_out).encode("utf-8")
            else:
                doc.close()
                return _fail(f"Unbekanntes Format: {fmt}", fmt)
            doc.close()
            return PdfToolResult(success=True, output_format=fmt, file_content=data)
        except Exception as e:
            return _fail(f"Export fehlgeschlagen: {e}", fmt)

    def pdf_to_csv(self, file_content: bytes, pages: str | None = None) -> PdfToolResult:
        """Tabellen als CSV — PyMuPDF find_tables (kein Java nötig)."""
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar", "csv")
        try:
            from app.services.pdf_tools_service import _parse_page_range

            doc = fitz.open(stream=file_content, filetype="pdf")
            page_list = (
                _parse_page_range(pages, doc.page_count)
                if pages
                else list(range(1, doc.page_count + 1))
            )
            buf = io.StringIO()
            writer = csv.writer(buf, delimiter=";")
            found = 0
            for pno in page_list:
                tabs = doc[pno - 1].find_tables()
                for tab in tabs.tables:
                    found += 1
                    writer.writerow([f"# Tabelle {found} (Seite {pno})"])
                    for row in tab.extract():
                        writer.writerow([(c or "").replace("\n", " ") for c in row])
                    writer.writerow([])
            doc.close()
            if found == 0:
                return _fail("Keine Tabellen gefunden", "csv")
            return PdfToolResult(
                success=True,
                output_format="csv",
                file_content=buf.getvalue().encode("utf-8-sig"),
                metadata={"tables": found},
            )
        except Exception as e:
            return _fail(f"CSV-Export fehlgeschlagen: {e}", "csv")

    # ── Bereinigen (Metadaten + versteckte Inhalte) ───────────

    def clean_pdf(self, file_content: bytes) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            doc.scrub(
                metadata=True,
                xml_metadata=True,
                javascript=True,
                attached_files=True,
                embedded_files=True,
                thumbnails=True,
                reset_fields=False,
                reset_responses=True,
                clean_pages=True,
            )
            out = doc.tobytes(garbage=4, deflate=True)
            doc.close()
            return PdfToolResult(success=True, output_format="pdf", file_content=out)
        except Exception as e:
            return _fail(f"Bereinigen fehlgeschlagen: {e}")

    # ── Rechteverwaltung ──────────────────────────────────────

    def set_permissions(
        self,
        file_content: bytes,
        owner_password: str,
        allow_print: bool = True,
        allow_copy: bool = False,
        allow_modify: bool = False,
        allow_annotate: bool = True,
    ) -> PdfToolResult:
        if not PIKEPDF_AVAILABLE:
            return _fail("pikepdf nicht verfügbar")
        if not owner_password:
            return _fail("Besitzer-Passwort erforderlich")
        try:
            perms = pikepdf.Permissions(
                print_lowres=allow_print,
                print_highres=allow_print,
                extract=allow_copy,
                modify_other=allow_modify,
                modify_assembly=allow_modify,
                modify_annotation=allow_annotate,
                modify_form=allow_annotate,
            )
            with pikepdf.open(io.BytesIO(file_content)) as pdf:
                buf = io.BytesIO()
                pdf.save(
                    buf,
                    encryption=pikepdf.Encryption(
                        user="", owner=owner_password, R=6, allow=perms
                    ),
                )
            return PdfToolResult(
                success=True, output_format="pdf", file_content=buf.getvalue()
            )
        except pikepdf.PasswordError:
            return _fail("PDF ist bereits passwortgeschützt — bitte zuerst entsperren")
        except Exception as e:
            return _fail(f"Rechte setzen fehlgeschlagen: {e}")

    # ── Signaturprüfung mit Bericht ───────────────────────────

    def verify_signatures(self, file_content: bytes) -> PdfToolResult:
        if not PYHANKO_VALIDATION_AVAILABLE:
            return _fail("pyHanko nicht verfügbar", "json")
        try:
            reader = _HankoReader(io.BytesIO(file_content))
            sigs = reader.embedded_signatures
            if not sigs:
                return PdfToolResult(
                    success=True,
                    output_format="json",
                    metadata={"signatures": [], "count": 0},
                )
            report = []
            for sig in sigs:
                entry: dict = {"field": sig.field_name}
                try:
                    status = _validate_sig(
                        sig,
                        key_usage_settings=KeyUsageConstraints(key_usage=set()),
                    )
                    cert = status.signing_cert
                    subject = cert.subject.human_friendly if cert else "unbekannt"
                    entry.update(
                        {
                            "signer": subject,
                            "intact": bool(status.intact),
                            "valid_cms": bool(status.valid),
                            "coverage": str(status.coverage),
                            "signing_time": str(status.signer_reported_dt or ""),
                            "trusted": bool(getattr(status, "trusted", False)),
                            "hinweis": (
                                "Integrität geprüft. Vertrauenskette ohne konfigurierte "
                                "Vertrauensanker nicht bewertbar."
                            ),
                        }
                    )
                except Exception as e:
                    entry.update({"error": f"Prüfung fehlgeschlagen: {type(e).__name__}"})
                report.append(entry)
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={"signatures": report, "count": len(report)},
            )
        except Exception as e:
            return _fail(f"Signaturprüfung fehlgeschlagen: {e}", "json")

    # ── Leere Seiten einfügen ─────────────────────────────────

    def insert_blank_pages(
        self, file_content: bytes, after_page: int, count: int = 1
    ) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            count = max(1, min(count, 50))
            after_page = max(0, min(after_page, doc.page_count))
            ref = doc[after_page - 1].rect if after_page >= 1 else doc[0].rect
            for _ in range(count):
                doc.insert_page(after_page, width=ref.width, height=ref.height)
            out = doc.tobytes(garbage=3, deflate=True)
            doc.close()
            return PdfToolResult(success=True, output_format="pdf", file_content=out)
        except Exception as e:
            return _fail(f"Einfügen fehlgeschlagen: {e}")

    # ── Prüfakte: Merge + Lesezeichen je Dokument + Bates ─────

    def build_pruefakte(
        self,
        files: list[tuple[str, bytes]],
        bates_prefix: str = "",
        bates_digits: int = 6,
    ) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar")
        try:
            out_doc = fitz.open()
            toc = []
            for filename, content in files:
                src = fitz.open(stream=content, filetype="pdf")
                start = out_doc.page_count + 1
                out_doc.insert_pdf(src)
                src.close()
                title = filename.rsplit(".", 1)[0]
                toc.append([1, title, start])
            out_doc.set_toc(toc)
            data = out_doc.tobytes(garbage=3, deflate=True)
            page_total = out_doc.page_count
            out_doc.close()
            if bates_prefix:
                from app.services.pdf_extras_service import get_pdf_extras

                result = get_pdf_extras().add_bates_numbers(
                    data, prefix=bates_prefix, start=1, digits=bates_digits
                )
                if not result.success:
                    return result
                data = result.file_content
            return PdfToolResult(
                success=True,
                output_format="pdf",
                file_content=data,
                metadata={"documents": len(files), "pages": page_total},
            )
        except Exception as e:
            return _fail(f"Prüfakte fehlgeschlagen: {e}")

    # ── Scan-Qualitätsprüfung ─────────────────────────────────

    def quality_check(self, file_content: bytes) -> PdfToolResult:
        if not PYMUPDF_AVAILABLE:
            return _fail("PyMuPDF nicht verfügbar", "json")
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            empty_pages: list[int] = []
            no_text_pages: list[int] = []
            duplicates: list[list[int]] = []
            hashes: dict[str, int] = {}
            for i in range(doc.page_count):
                page = doc[i]
                text = page.get_text("text").strip()
                has_images = bool(page.get_images(full=True))
                if not text and not has_images and not page.get_drawings():
                    empty_pages.append(i + 1)
                elif has_images and len(text) < 20:
                    no_text_pages.append(i + 1)
                pix = page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15))
                h = hashlib.md5(pix.samples).hexdigest()
                if h in hashes:
                    duplicates.append([hashes[h], i + 1])
                else:
                    hashes[h] = i + 1
            count = doc.page_count
            doc.close()
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={
                    "pages": count,
                    "empty_pages": empty_pages,
                    "scan_pages_without_text": no_text_pages,
                    "duplicate_page_pairs": duplicates,
                    "ok": not (empty_pages or no_text_pages or duplicates),
                },
            )
        except Exception as e:
            return _fail(f"Qualitätsprüfung fehlgeschlagen: {e}", "json")

    # ── Lokale KI (OpenAI-kompatibler Endpoint, z.B. ai-router) ──

    def _extract_for_ai(self, file_content: bytes, max_chars: int = 60000) -> str:
        doc = fitz.open(stream=file_content, filetype="pdf")
        parts = []
        total = 0
        for i in range(doc.page_count):
            t = doc[i].get_text("text")
            parts.append(f"[Seite {i + 1}]\n{t}")
            total += len(t)
            if total > max_chars:
                parts.append("[… Dokument gekürzt …]")
                break
        doc.close()
        return "\n".join(parts)[: max_chars + 200]

    def ai_ask(self, file_content: bytes, question: str, mode: str = "ask") -> PdfToolResult:
        """Zusammenfassen oder Frage beantworten — ausschließlich lokales LLM,
        Inhalte werden transient übertragen und nicht gespeichert."""
        if not settings.llm_url:
            return _fail("Kein lokales LLM konfiguriert", "json")
        text = self._extract_for_ai(file_content)
        if not text.strip():
            return _fail("Dokument enthält keinen extrahierbaren Text (OCR nötig?)", "json")
        if mode == "summary":
            system = (
                "Du bist ein präziser Dokument-Assistent. Fasse das PDF strukturiert "
                "auf Deutsch zusammen (Kernaussagen, wichtige Zahlen, offene Punkte). "
                "Erfinde nichts."
            )
            user = f"Dokumentinhalt:\n\n{text}"
        else:
            system = (
                "Du bist ein präziser Dokument-Assistent. Beantworte die Frage "
                "ausschließlich aus dem Dokumentinhalt, auf Deutsch, mit Seitenangaben "
                "wo möglich. Wenn die Antwort nicht im Dokument steht, sage das."
            )
            user = f"Dokumentinhalt:\n\n{text}\n\nFrage: {question}"
        try:
            resp = httpx.post(
                settings.llm_url.rstrip("/") + "/chat/completions",
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1500,
                },
                timeout=120,
            )
            if resp.status_code != 200:
                return _fail("Lokales LLM nicht erreichbar oder Fehler", "json")
            answer = resp.json()["choices"][0]["message"]["content"]
            return PdfToolResult(
                success=True,
                output_format="json",
                metadata={"answer": answer, "model": settings.llm_model},
            )
        except Exception:
            return _fail("Lokales LLM nicht erreichbar", "json")


@lru_cache(maxsize=1)
def get_pdf_more() -> PdfMoreService:
    return PdfMoreService()
