"""Tests für die Werkbank: /api/pdf-tools/compose stellt Seiten aus mehreren
Dokumenten in freier Reihenfolge zusammen (mischen, löschen, drehen, Leerseiten)."""

import io
import json

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _compose(client, files, plan):
    return client.post(
        "/api/pdf-tools/compose",
        files=[("files", (name, io.BytesIO(data), "application/pdf")) for name, data in files],
        data={"plan": json.dumps(plan)},
    )


def _page_texts(pdf_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texts = [page.get_text().strip() for page in doc]
    doc.close()
    return texts


def test_compose_mischt_dokumentuebergreifend(client):
    a = make_pdf(3, "Akte-A")
    b = make_pdf(2, "Akte-B")
    # B2, A1, A3 — Seite A2 und B1 bewusst weggelassen (= gelöscht)
    plan = [
        {"file": 1, "page": 2},
        {"file": 0, "page": 1},
        {"file": 0, "page": 3},
    ]
    r = _compose(client, [("a.pdf", a), ("b.pdf", b)], plan)
    assert r.status_code == 200
    texts = _page_texts(r.content)
    assert len(texts) == 3
    assert "Akte-B Seite 2" in texts[0]
    assert "Akte-A Seite 1" in texts[1]
    assert "Akte-A Seite 3" in texts[2]


def test_compose_dreht_und_fuegt_leerseite_ein(client):
    a = make_pdf(2, "Drehtest")
    plan = [
        {"file": 0, "page": 1, "rotate": 90},
        {"blank": True, "width": 595.28, "height": 841.89},
        {"file": 0, "page": 2},
    ]
    r = _compose(client, [("a.pdf", a)], plan)
    assert r.status_code == 200
    doc = fitz.open(stream=r.content, filetype="pdf")
    assert doc.page_count == 3
    assert doc[0].rotation == 90
    assert doc[1].get_text().strip() == ""
    assert round(doc[1].rect.width) == 595 and round(doc[1].rect.height) == 842
    assert "Drehtest Seite 2" in doc[2].get_text()
    doc.close()


def test_compose_dupliziert_seiten(client):
    a = make_pdf(1, "Doppelt")
    r = _compose(client, [("a.pdf", a)], [{"file": 0, "page": 1}, {"file": 0, "page": 1}])
    assert r.status_code == 200
    texts = _page_texts(r.content)
    assert len(texts) == 2
    assert all("Doppelt Seite 1" in t for t in texts)


def test_compose_meldet_seiten_ausser_bereich(client):
    a = make_pdf(1, "Kurz")
    r = _compose(client, [("a.pdf", a)], [{"file": 0, "page": 5}])
    assert r.status_code == 400
    assert "Seite 5" in r.json()["detail"]


def test_compose_meldet_unbekannte_datei(client):
    a = make_pdf(1, "Solo")
    r = _compose(client, [("a.pdf", a)], [{"file": 3, "page": 1}])
    assert r.status_code == 400
    assert "unbekannte Datei" in r.json()["detail"]


def test_compose_lehnt_kaputtes_plan_json_ab(client):
    a = make_pdf(1, "Kaputt")
    r = client.post(
        "/api/pdf-tools/compose",
        files=[("files", ("a.pdf", io.BytesIO(a), "application/pdf"))],
        data={"plan": "kein json"},
    )
    assert r.status_code == 400


def test_compose_lehnt_leeren_plan_ab(client):
    a = make_pdf(1, "Leer")
    r = _compose(client, [("a.pdf", a)], [])
    assert r.status_code == 400
