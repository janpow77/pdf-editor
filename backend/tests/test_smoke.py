"""Smoke-Tests: Merge/Split-Roundtrip komplett in-memory, Health, Mail-Gate."""

import io
import zipfile

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def make_pdf(pages: int, text: str) -> bytes:
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"{text} Seite {i + 1}")
    data = doc.tobytes()
    doc.close()
    return data


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["features"]["pdf_merge"] is True


def test_merge_then_split_roundtrip(client):
    pdf_a = make_pdf(2, "Dokument A")
    pdf_b = make_pdf(3, "Dokument B")

    r = client.post(
        "/api/pdf-tools/merge",
        files=[
            ("files", ("a.pdf", pdf_a, "application/pdf")),
            ("files", ("b.pdf", pdf_b, "application/pdf")),
        ],
    )
    assert r.status_code == 200, r.text
    merged = r.content
    with fitz.open(stream=merged, filetype="pdf") as doc:
        assert doc.page_count == 5

    r = client.post(
        "/api/pdf-tools/split",
        data={"mode": "every_n", "every_n": "1"},
        files={"file": ("merged.pdf", merged, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert len(zf.namelist()) == 5


def test_file_size_limit(client):
    # 1 Byte über dem konfigurierten Limit → 400, kein Serverfehler
    from app.config import settings

    oversized = b"%PDF-1.4" + b"0" * (settings.max_file_size_mb * 1024 * 1024)
    r = client.post(
        "/api/pdf-tools/split",
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert r.status_code == 400


def test_mail_unconfigured_returns_503(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "smtp_host", "")
    r = client.post(
        "/api/mail/send",
        data={"to": "test@example.org"},
        files={"files": ("a.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 503
