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
