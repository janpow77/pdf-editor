"""Smoke-Tests für den PDF→Word/Excel-Konverter."""

import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pdf_converter_service as svc
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_converter_status(client):
    r = client.get("/api/pdf-convert/status")
    assert r.status_code == 200
    body = r.json()
    assert "pymupdf" in body


@pytest.mark.skipif(not svc.PYMUPDF_AVAILABLE, reason="PyMuPDF nicht verfügbar")
def test_to_word_produces_valid_docx(client):
    pdf = make_pdf(2, "Konvertierungs-Test")
    r = client.post(
        "/api/pdf-convert/to-word",
        files={"file": ("doc.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text

    import docx

    d = docx.Document(io.BytesIO(r.content))
    text = "\n".join(p.text for p in d.paragraphs)
    assert "Konvertierungs-Test" in text


@pytest.mark.skipif(
    not (svc.TABULA_AVAILABLE and svc.PANDAS_AVAILABLE),
    reason="tabula/pandas nicht verfügbar (Java erforderlich)",
)
def test_to_excel_smoke(client):
    pdf = make_pdf(1, "Tabelle 1 2 3")
    r = client.post(
        "/api/pdf-convert/to-excel",
        files={"file": ("doc.pdf", pdf, "application/pdf")},
    )
    # Ohne echte Tabellen liefert der Endpoint (Quell-Verhalten) einen
    # strukturierten Fehler mit tables_found=0 — kein Crash, keine Traceback-Antwort.
    if r.status_code != 200:
        detail = r.json()["detail"]
        assert "Tabellen" in str(detail), r.text


@pytest.mark.skipif(
    not (svc.TABULA_AVAILABLE and svc.PANDAS_AVAILABLE),
    reason="tabula/pandas nicht verfügbar (Java erforderlich)",
)
def test_to_excel_preview_zeigt_tabelleninhalt(client):
    from tests.test_pdf_more import make_table_pdf

    r = client.post(
        "/api/pdf-convert/to-excel/preview",
        files={"file": ("tabelle.pdf", make_table_pdf(), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["total_tables"] >= 1
    assert body["pages_processed"] == [1]
    tabelle = body["tables"][0]
    assert tabelle["page"] == 1
    assert tabelle["total_columns"] == 3
    zellen = [zelle for zeile in tabelle["preview_rows"] for zelle in zeile]
    assert "Posten" in zellen and "Miete" in zellen and "1.000,00" in zellen


def test_to_excel_preview_nur_pdf_erlaubt_400(client):
    r = client.post(
        "/api/pdf-convert/to-excel/preview",
        files={"file": ("notiz.txt", b"kein pdf", "text/plain")},
    )
    assert r.status_code == 400
