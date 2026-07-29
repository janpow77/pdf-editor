"""Tests für die Modulkatalog-Erweiterungen (pdf_more) + neue Batch-Operationen."""

import io
import json
import zipfile

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pdf_more_service as svc
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def make_table_pdf() -> bytes:
    """PDF mit gezeichneter 3x3-Tabelle (Linien + Zelltexte) für find_tables."""
    doc = fitz.open()
    page = doc.new_page()
    x0, y0, cell_w, cell_h = 72, 72, 120, 30
    rows, cols = 3, 3
    for r in range(rows + 1):
        y = y0 + r * cell_h
        page.draw_line((x0, y), (x0 + cols * cell_w, y))
    for c in range(cols + 1):
        x = x0 + c * cell_w
        page.draw_line((x, y0), (x, y0 + rows * cell_h))
    data = [["Posten", "Betrag", "Datum"], ["Miete", "1.000,00", "01.01."], ["Strom", "250,50", "05.01."]]
    for r in range(rows):
        for c in range(cols):
            page.insert_text((x0 + c * cell_w + 5, y0 + r * cell_h + 20), data[r][c], fontsize=10)
    out = doc.tobytes()
    doc.close()
    return out


# ── Status ────────────────────────────────────────────────────


def test_status_lists_features(client):
    r = client.get("/api/pdf-more/status")
    assert r.status_code == 200
    body = r.json()
    for key in ("office_to_pdf", "clean_pdf", "permissions", "verify_signatures", "ai"):
        assert key in body
    assert body["ai"] is False  # kein LLM in Tests konfiguriert


def test_health_includes_more_features(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    features = r.json()["features"]
    assert "clean_pdf" in features and "pruefakte" in features


# ── Office → PDF ──────────────────────────────────────────────


def _soffice_can_convert() -> bool:
    """True nur, wenn LibreOffice inkl. Writer-Komponente konvertieren kann —
    das Binary allein reicht nicht (Sandbox ohne libreoffice-writer)."""
    if not svc.SOFFICE_BIN:
        return False
    return svc.get_pdf_more().office_to_pdf(b"Probe", ".txt").success


@pytest.mark.skipif(
    not _soffice_can_convert(), reason="LibreOffice(-Writer) nicht verfügbar"
)
def test_office_to_pdf_txt(client):
    r = client.post(
        "/api/pdf-more/office-to-pdf",
        files={"file": ("notiz.txt", b"Hallo Umlaute \xc3\xa4\xc3\xb6\xc3\xbc", "text/plain")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc.page_count >= 1


def test_office_to_pdf_bad_extension_400(client):
    r = client.post(
        "/api/pdf-more/office-to-pdf",
        files={"file": ("bild.png", b"\x89PNG", "image/png")},
    )
    assert r.status_code == 400


# ── Text-Exporte ──────────────────────────────────────────────


def test_export_markdown_html_json(client):
    pdf = make_pdf(2, "Exporttext")
    for fmt, marker in (("markdown", b"Exporttext"), ("html", b"<html"), ("json", b'"pages"')):
        r = client.post(
            f"/api/pdf-more/export/{fmt}",
            files={"file": ("d.pdf", pdf, "application/pdf")},
        )
        assert r.status_code == 200, (fmt, r.text)
        assert marker in r.content

    r = client.post(
        "/api/pdf-more/export/docbook",
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 400


def test_to_csv_finds_table(client):
    r = client.post(
        "/api/pdf-more/to-csv",
        files={"file": ("t.pdf", make_table_pdf(), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert int(r.headers["X-Tables-Found"]) >= 1
    text = r.content.decode("utf-8-sig")
    assert "Miete" in text and ";" in text


def test_to_csv_no_tables_422(client):
    r = client.post(
        "/api/pdf-more/to-csv",
        files={"file": ("d.pdf", make_pdf(1, "nur Fliesstext"), "application/pdf")},
    )
    assert r.status_code == 422


# ── Bereinigen ────────────────────────────────────────────────


def test_clean_removes_metadata(client):
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Inhalt")
    doc.set_metadata({"author": "Geheimer Autor", "title": "Interner Titel"})
    pdf = doc.tobytes()
    doc.close()
    r = client.post(
        "/api/pdf-more/clean", files={"file": ("d.pdf", pdf, "application/pdf")}
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as cleaned:
        meta = cleaned.metadata or {}
        assert not meta.get("author")
        assert "Inhalt" in cleaned[0].get_text()


# ── Rechteverwaltung ──────────────────────────────────────────


def test_permissions_restrict_copy(client):
    pdf = make_pdf(1, "Geschützt")
    r = client.post(
        "/api/pdf-more/permissions",
        data={
            "owner_password": "Besitzer-123",
            "allow_print": "true",
            "allow_copy": "false",
            "allow_modify": "false",
        },
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        # Ohne Öffnen-Passwort lesbar, aber verschlüsselt mit Rechte-Flags
        assert bool(doc.needs_pass) is False
        assert doc.permissions & fitz.PDF_PERM_PRINT
        assert not (doc.permissions & fitz.PDF_PERM_COPY)


def test_permissions_requires_password(client):
    r = client.post(
        "/api/pdf-more/permissions",
        data={"owner_password": ""},
        files={"file": ("d.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 422  # min_length=1


# ── Signaturprüfung ───────────────────────────────────────────


def test_verify_signatures_unsigned(client):
    r = client.post(
        "/api/pdf-more/verify-signatures",
        files={"file": ("d.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 0


@pytest.mark.skipif(
    not svc.PYHANKO_VALIDATION_AVAILABLE, reason="pyHanko nicht verfügbar"
)
def test_verify_signatures_signed_pdf(client):
    from app.services.pdf_extras_service import get_pdf_extras
    from tests.test_pdf_extras2 import _make_p12

    signed = get_pdf_extras().sign_digital(
        make_pdf(1, "Vertragstext"), _make_p12(b"geheim"), "geheim"
    )
    assert signed.success, signed.error
    r = client.post(
        "/api/pdf-more/verify-signatures",
        files={"file": ("s.pdf", signed.file_content, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1
    sig = body["signatures"][0]
    assert sig["intact"] is True
    assert "Test Signer" in sig["signer"]


# ── Leere Seiten ──────────────────────────────────────────────


def test_insert_blank_pages(client):
    r = client.post(
        "/api/pdf-more/insert-blank",
        data={"after_page": "1", "count": "2"},
        files={"file": ("d.pdf", make_pdf(2, "Seite"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc.page_count == 4
        assert not doc[1].get_text().strip()


# ── Prüfakte ──────────────────────────────────────────────────


def test_pruefakte_toc_and_bates(client):
    files = [
        ("files", ("Antrag.pdf", make_pdf(2, "Antrag"), "application/pdf")),
        ("files", ("Beleg.pdf", make_pdf(1, "Beleg"), "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-more/pruefakte",
        data={"bates_prefix": "AKTE-", "bates_digits": "4"},
        files=files,
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Documents"] == "2"
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc.page_count == 3
        toc = doc.get_toc()
        assert [t[1] for t in toc] == ["Antrag", "Beleg"]
        assert toc[1][2] == 3  # Beleg beginnt auf Seite 3
        assert "AKTE-0003" in doc[2].get_text()


def test_pruefakte_needs_two_files(client):
    r = client.post(
        "/api/pdf-more/pruefakte",
        files=[("files", ("a.pdf", make_pdf(1, "A"), "application/pdf"))],
    )
    assert r.status_code == 400


# ── Qualitätsprüfung ──────────────────────────────────────────


def test_quality_check_reports_empty_and_duplicates(client):
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Inhalt A")
    doc.new_page()  # leer
    doc.new_page().insert_text((72, 72), "Inhalt A")  # Duplikat von Seite 1
    pdf = doc.tobytes()
    doc.close()
    r = client.post(
        "/api/pdf-more/quality-check",
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["empty_pages"] == [2]
    assert [1, 3] in body["duplicate_page_pairs"]
    assert body["ok"] is False


# ── Lokale KI ─────────────────────────────────────────────────


def test_ai_disabled_503(client):
    r = client.post(
        "/api/pdf-more/ai/summarize",
        files={"file": ("d.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 503


def test_ai_ask_with_mocked_llm(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_url", "http://ai-router.test/v1")
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Die Antwort steht auf Seite 1."}}]}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(svc.httpx, "post", fake_post)
    r = client.post(
        "/api/pdf-more/ai/ask",
        data={"question": "Was steht im Dokument?"},
        files={"file": ("d.pdf", make_pdf(1, "Fördermittel 1.000 Euro"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert "Antwort" in r.json()["answer"]
    assert captured["url"] == "http://ai-router.test/v1/chat/completions"
    assert "Fördermittel" in captured["payload"]["messages"][1]["content"]


# ── Neue Batch-Operationen (watermark, clean) ─────────────────


def test_batch_watermark_and_clean(client):
    r = client.post(
        "/api/pdf-extras/batch",
        data={
            "operation": "watermark",
            "params": json.dumps({"text": "ENTWURF", "opacity": 0.4}),
        },
        files=[("files", ("a.pdf", make_pdf(1, "A"), "application/pdf"))],
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert "a_wasserzeichen.pdf" in zf.namelist()

    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "clean", "params": "{}"},
        files=[("files", ("b.pdf", make_pdf(1, "B"), "application/pdf"))],
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert "b_bereinigt.pdf" in zf.namelist()
