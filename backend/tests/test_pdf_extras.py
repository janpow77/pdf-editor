"""Tests für die erweiterten PDF-Werkzeuge (Extras)."""

import io
import json

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pdf_extras_service as svc
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_extras_status(client):
    r = client.get("/api/pdf-extras/status")
    assert r.status_code == 200
    assert r.json()["pdf_to_text"] is True


def test_pdf_to_text(client):
    pdf = make_pdf(2, "Extraktions-Test")
    r = client.post(
        "/api/pdf-extras/to-text", files={"file": ("d.pdf", pdf, "application/pdf")}
    )
    assert r.status_code == 200
    text = r.content.decode("utf-8")
    assert "Extraktions-Test" in text and "Seite 2" in text


def test_bates_numbers(client):
    pdf = make_pdf(3, "Beleg")
    r = client.post(
        "/api/pdf-extras/bates",
        data={"prefix": "AKTE-", "start": "100", "digits": "5"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Bates-First"] == "AKTE-00100"
    assert r.headers["X-Bates-Last"] == "AKTE-00102"
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert "AKTE-00101" in doc[1].get_text()


def test_redact_by_search(client):
    pdf = make_pdf(1, "Geheimwort sichtbar")
    r = client.post(
        "/api/pdf-extras/redact",
        data={"term": "Geheimwort"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert int(r.headers["X-Redactions"]) >= 1
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        text = doc[0].get_text()
        assert "Geheimwort" not in text  # echte Redaction, nicht nur Abdeckung
        assert "sichtbar" in text


def test_form_fields_and_fill(client):
    # PDF mit Textfeld erzeugen
    doc = fitz.open()
    page = doc.new_page()
    widget = fitz.Widget()
    widget.field_name = "name"
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = fitz.Rect(72, 72, 300, 96)
    page.add_widget(widget)
    pdf = doc.tobytes()
    doc.close()

    r = client.post(
        "/api/pdf-extras/form/fields", files={"file": ("f.pdf", pdf, "application/pdf")}
    )
    assert r.status_code == 200, r.text
    assert r.json()["count"] == 1
    assert r.json()["fields"][0]["name"] == "name"

    r = client.post(
        "/api/pdf-extras/form/fill",
        data={"values": json.dumps({"name": "Erika Musterfrau"})},
        files={"file": ("f.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Fields-Filled"] == "1"
    with fitz.open(stream=r.content, filetype="pdf") as out:
        w = next(iter(out[0].widgets()))
        assert w.field_value == "Erika Musterfrau"


def test_sign_image(client):
    pdf = make_pdf(1, "Vertrag")
    # kleines PNG erzeugen
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (120, 40), (10, 10, 120)).save(buf, format="PNG")
    r = client.post(
        "/api/pdf-extras/sign-image",
        data={"page": "1", "x": "0.6", "y": "0.8", "width": "0.25"},
        files={
            "file": ("d.pdf", pdf, "application/pdf"),
            "image": ("sig.png", buf.getvalue(), "image/png"),
        },
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert len(doc[0].get_images(full=True)) == 1


def test_edit_text_blocks_wysiwyg(client):
    pdf = make_pdf(1, "Alter Inhalt")
    # Blockposition über den bestehenden text-blocks-Endpoint holen
    r = client.post(
        "/api/pdf-editor/text-blocks",
        data={"page": "1"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    blocks = r.json()["blocks"]
    assert blocks and "Alter Inhalt" in blocks[0]["text"]

    edits = [
        {
            "page": 1,
            "bbox": blocks[0]["bbox"],
            "text": "Neuer Inhalt nach Bearbeitung",
            "font_size": blocks[0]["font_size"],
            "color": "#000000",
        }
    ]
    r = client.post(
        "/api/pdf-extras/edit-text-blocks",
        data={"edits": json.dumps(edits)},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        text = doc[0].get_text()
        assert "Neuer Inhalt" in text
        assert "Alter Inhalt" not in text


@pytest.mark.skipif(not svc.GHOSTSCRIPT_BIN, reason="Ghostscript nicht installiert")
def test_to_pdfa(client):
    pdf = make_pdf(1, "Archiv")
    r = client.post(
        "/api/pdf-extras/to-pdfa",
        data={"level": "2b"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text


def test_to_pdfa_unavailable_503(client, monkeypatch):
    monkeypatch.setattr(svc, "GHOSTSCRIPT_BIN", None)
    pdf = make_pdf(1, "x")
    r = client.post(
        "/api/pdf-extras/to-pdfa", files={"file": ("d.pdf", pdf, "application/pdf")}
    )
    assert r.status_code == 503
