"""Tests für PDF schützen/entsperren (pikepdf)."""

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_protect_then_unlock_roundtrip(client):
    original = make_pdf(2, "Vertraulich")

    r = client.post(
        "/api/pdf-tools/protect",
        data={"password": "geheim-123"},
        files={"file": ("doc.pdf", original, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    protected = r.content

    with fitz.open(stream=protected, filetype="pdf") as doc:
        assert bool(doc.needs_pass) is True

    r = client.post(
        "/api/pdf-tools/unlock",
        data={"password": "geheim-123"},
        files={"file": ("doc_geschuetzt.pdf", protected, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert bool(doc.needs_pass) is False
        assert doc.page_count == 2


def test_unlock_wrong_password_400(client):
    original = make_pdf(1, "x")
    r = client.post(
        "/api/pdf-tools/protect",
        data={"password": "richtig-123"},
        files={"file": ("doc.pdf", original, "application/pdf")},
    )
    protected = r.content

    r = client.post(
        "/api/pdf-tools/unlock",
        data={"password": "falsch"},
        files={"file": ("doc.pdf", protected, "application/pdf")},
    )
    assert r.status_code == 400
    assert "Falsches Passwort" in r.json()["detail"]


def test_protect_already_protected_400(client):
    original = make_pdf(1, "x")
    protected = client.post(
        "/api/pdf-tools/protect",
        data={"password": "pw-123456789"},
        files={"file": ("doc.pdf", original, "application/pdf")},
    ).content

    r = client.post(
        "/api/pdf-tools/protect",
        data={"password": "neues-pw"},
        files={"file": ("doc.pdf", protected, "application/pdf")},
    )
    assert r.status_code == 400
