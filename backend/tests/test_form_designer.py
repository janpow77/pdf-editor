"""Tests für den Formular-Designer (Felder anlegen, Import-Daten, Prüflauf)."""

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


def _create(client, fields, dry_run=False, pdf=None, pages=1):
    return client.post(
        "/api/pdf-extras/form/create",
        data={"fields": json.dumps(fields), "dry_run": str(dry_run).lower()},
        files={"file": ("f.pdf", pdf or make_pdf(pages, "Antragsformular"), "application/pdf")},
    )


ALL_TYPES = [
    {"page": 1, "type": "text", "name": "vorname", "x0": 0.1, "y0": 0.1, "x1": 0.5, "y1": 0.14, "value": "Max", "tooltip": "Bitte Vornamen eingeben", "required": True},
    {"page": 1, "type": "textarea", "name": "bemerkung", "x0": 0.1, "y0": 0.2, "x1": 0.8, "y1": 0.32, "font_size": 9},
    {"page": 1, "type": "checkbox", "name": "gelesen", "x0": 0.1, "y0": 0.4, "x1": 0.14, "y1": 0.43, "value": True},
    {"page": 1, "type": "dropdown", "name": "anrede", "x0": 0.1, "y0": 0.5, "x1": 0.4, "y1": 0.54, "options": ["Frau", "Herr", "keine Angabe"], "value": "Herr"},
    {"page": 1, "type": "listbox", "name": "themen", "x0": 0.1, "y0": 0.6, "x1": 0.4, "y1": 0.7, "options": ["EFRE", "ESF"]},
    {"page": 1, "type": "signature", "name": "unterschrift", "x0": 0.5, "y0": 0.8, "x1": 0.9, "y1": 0.88},
]


def test_create_all_field_types(client):
    r = _create(client, ALL_TYPES)
    assert r.status_code == 200, r.text
    assert r.headers["X-Fields-Created"] == "6"
    assert r.headers["X-Fields-Skipped"] == "0"

    with fitz.open(stream=r.content, filetype="pdf") as doc:
        widgets = {w.field_name: w for w in doc[0].widgets()}
        assert set(widgets) == {
            "vorname",
            "bemerkung",
            "gelesen",
            "anrede",
            "themen",
            "unterschrift",
        }
        assert widgets["vorname"].field_type_string == "Text"
        assert widgets["vorname"].field_value == "Max"
        assert widgets["vorname"].field_label == "Bitte Vornamen eingeben"
        assert widgets["vorname"].field_flags & fitz.PDF_FIELD_IS_REQUIRED
        assert widgets["bemerkung"].field_flags & fitz.PDF_TX_FIELD_IS_MULTILINE
        assert widgets["gelesen"].field_type_string == "CheckBox"
        assert widgets["gelesen"].field_value in (True, "Yes")
        assert widgets["anrede"].field_type_string == "ComboBox"
        assert widgets["anrede"].choice_values == ["Frau", "Herr", "keine Angabe"]
        assert widgets["anrede"].field_value == "Herr"
        assert widgets["themen"].field_type_string == "ListBox"
        assert widgets["unterschrift"].field_type_string == "Signature"


def test_geometry_is_normalized_to_page(client):
    """0–1-Koordinaten landen maßstabsgetreu auf der Seite."""
    r = _create(
        client,
        [{"page": 1, "type": "text", "name": "feld", "x0": 0.25, "y0": 0.5, "x1": 0.75, "y1": 0.55}],
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        prect = doc[0].rect
        rect = list(doc[0].widgets())[0].rect
        assert rect.x0 == pytest.approx(prect.width * 0.25, abs=1.0)
        assert rect.x1 == pytest.approx(prect.width * 0.75, abs=1.0)
        assert rect.y0 == pytest.approx(prect.height * 0.5, abs=1.0)


def test_created_fields_are_fillable(client):
    """Designer-Felder lassen sich mit dem Ausfüllen-Werkzeug befüllen."""
    created = _create(client, ALL_TYPES)
    assert created.status_code == 200
    r = client.post(
        "/api/pdf-extras/form/fill",
        data={"values": json.dumps({"vorname": "Erika", "anrede": "Frau"}), "flatten": "false"},
        files={"file": ("f.pdf", created.content, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        values = {w.field_name: w.field_value for w in doc[0].widgets()}
        assert values["vorname"] == "Erika"
        assert values["anrede"] == "Frau"


def test_fields_endpoint_returns_designer_geometry(client):
    """Vorhandene Felder kommen mit normierter Geometrie zurück (Import)."""
    created = _create(client, ALL_TYPES)
    r = client.post(
        "/api/pdf-extras/form/fields",
        files={"file": ("f.pdf", created.content, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    fields = {f["name"]: f for f in r.json()["fields"]}
    assert fields["vorname"]["designer_type"] == "text"
    assert fields["bemerkung"]["designer_type"] == "textarea"
    assert fields["anrede"]["designer_type"] == "dropdown"
    assert fields["unterschrift"]["designer_type"] == "signature"
    assert fields["vorname"]["required"] is True
    assert fields["vorname"]["tooltip"] == "Bitte Vornamen eingeben"
    # Roundtrip: importierte Geometrie ergibt wieder dieselbe Position
    assert fields["vorname"]["x0"] == pytest.approx(0.1, abs=0.01)
    assert fields["vorname"]["y1"] == pytest.approx(0.14, abs=0.01)


def test_duplicate_names_get_suffix(client):
    r = _create(
        client,
        [
            {"page": 1, "type": "text", "name": "feld", "x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.14},
            {"page": 1, "type": "text", "name": "feld", "x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.24},
        ],
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Fields-Created"] == "2"
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert {w.field_name for w in doc[0].widgets()} == {"feld", "feld_2"}


def test_field_name_sanitizing(client):
    r = _create(
        client,
        [{"page": 1, "type": "text", "name": "an.trag[1]", "x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.14}],
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert list(doc[0].widgets())[0].field_name == "an_trag_1_"


def test_dry_run_reports_warnings_without_pdf(client):
    r = _create(
        client,
        [
            {"page": 1, "type": "text", "name": "ok", "x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.14},
            {"page": 9, "type": "text", "name": "falscheseite", "x0": 0.1, "y0": 0.2, "x1": 0.4, "y1": 0.24},
            {"page": 1, "type": "text", "name": "winzig", "x0": 0.1, "y0": 0.3, "x1": 0.101, "y1": 0.301},
            {"page": 1, "type": "dropdown", "name": "leer", "x0": 0.1, "y0": 0.4, "x1": 0.4, "y1": 0.44, "options": []},
            {"page": 1, "type": "quatsch", "name": "unbekannt", "x0": 0.1, "y0": 0.5, "x1": 0.4, "y1": 0.54},
        ],
        dry_run=True,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["created"] == 1
    assert body["skipped"] == 4
    assert len(body["warnings"]) == 4
    joined = " ".join(body["warnings"])
    assert "Seite 9" in joined and "zu klein" in joined and "Auswahlwerte" in joined


def test_empty_and_invalid_payload(client):
    r = _create(client, [])
    assert r.status_code == 422

    r = client.post(
        "/api/pdf-extras/form/create",
        data={"fields": "kein-json"},
        files={"file": ("f.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 400

    r = client.post(
        "/api/pdf-extras/form/create",
        data={"fields": json.dumps(["string-statt-objekt"])},
        files={"file": ("f.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 400


def test_too_many_fields(client):
    many = [
        {"page": 1, "type": "text", "name": f"f{i}", "x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.14}
        for i in range(201)
    ]
    r = _create(client, many)
    assert r.status_code == 422
    assert "200" in r.json()["detail"]


def test_multipage_and_status_flag(client):
    r = _create(
        client,
        [
            {"page": 1, "type": "text", "name": "s1", "x0": 0.1, "y0": 0.1, "x1": 0.4, "y1": 0.14},
            {"page": 3, "type": "checkbox", "name": "s3", "x0": 0.1, "y0": 0.1, "x1": 0.14, "y1": 0.13},
        ],
        pages=3,
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert [w.field_name for w in doc[0].widgets()] == ["s1"]
        assert [w.field_name for w in doc[2].widgets()] == ["s3"]

    assert client.get("/api/pdf-extras/status").json()["form_design"] is True
