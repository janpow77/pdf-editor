"""Tests für musterbasierte Schwärzung und Schrifteinbettung."""

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


def pdf_with_lines(lines: list[str], fontsize: float = 11) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 90
    for line in lines:
        page.insert_text((60, y), line, fontsize=fontsize)
        y += 26
    out = doc.tobytes()
    doc.close()
    return out


SENSIBLE = [
    "Kontoverbindung: DE02 1203 0000 0000 2020 51",
    "Kontakt: max.muster@beispiel-firma.de, Tel. +49 611 32-1234",
    "Bearbeiter: Erika Musterfrau, geboren am 14.03.1978",
    "Vorgang AZ-1234/26, Betrag 1.500,00 EUR",
]


def preview(client, pdf, patterns=(), terms="", **extra):
    return client.post(
        "/api/pdf-extras/redact-patterns",
        data={
            "patterns": json.dumps(list(patterns)),
            "terms": terms,
            "preview": "true",
            **extra,
        },
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )


def redact(client, pdf, patterns=(), terms="", **extra):
    return client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps(list(patterns)), "terms": terms, **extra},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )


# ── Musterkatalog ─────────────────────────────────────────────


def test_pattern_catalog(client):
    r = client.get("/api/pdf-extras/redact/patterns")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["patterns"]}
    assert {"iban", "email", "telefon", "steuer_id", "aktenzeichen"} <= ids
    assert all(p["label"] and p["hint"] for p in r.json()["patterns"])


def test_preview_finds_patterns_across_spaces(client):
    """Die IBAN steht in Vierergruppen — Wortgrenzen dürfen nicht stören."""
    r = preview(client, pdf_with_lines(SENSIBLE), ["iban", "email", "telefon"])
    assert r.status_code == 200, r.text
    body = r.json()
    texts = {f["text"] for f in body["findings"]}
    assert "DE02 1203 0000 0000 2020 51" in texts
    assert "max.muster@beispiel-firma.de" in texts
    assert body["by_pattern"]["iban"] == 1
    assert all(f["page"] == 1 and len(f["rect"]) == 4 for f in body["findings"])


def test_preview_does_not_change_document(client):
    """Vorschau ist rein lesend — Schwärzen ist unumkehrbar."""
    pdf = pdf_with_lines(SENSIBLE)
    r = preview(client, pdf, ["iban"])
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        assert "DE02" in doc[0].get_text()


def test_redaction_removes_text(client):
    pdf = pdf_with_lines(SENSIBLE)
    r = redact(client, pdf, ["iban", "email"])
    assert r.status_code == 200, r.text
    assert int(r.headers["X-Redactions"]) >= 2
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        text = doc[0].get_text()
    assert "DE02" not in text
    assert "max.muster@" not in text
    assert "Kontoverbindung" in text  # Umfeld bleibt erhalten


def test_name_list_redaction(client):
    """Namensliste: mehrere Begriffe, einer pro Zeile."""
    pdf = pdf_with_lines(SENSIBLE)
    r = redact(client, pdf, terms="Erika Musterfrau\nMusterhausen")
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        text = doc[0].get_text()
    assert "Musterfrau" not in text
    assert "Bearbeiter" in text


def test_whole_word_option(client):
    pdf = pdf_with_lines(["Musterfrau und Muster GmbH"])
    body = preview(client, pdf, terms="Muster", whole_word="true").json()
    assert body["total"] == 1  # nur das eigenständige "Muster"
    body = preview(client, pdf, terms="Muster", whole_word="false").json()
    assert body["total"] == 2


def test_case_sensitivity(client):
    pdf = pdf_with_lines(["Vorgang muster und Muster"])
    assert preview(client, pdf, terms="Muster").json()["total"] == 2
    assert preview(client, pdf, terms="Muster", case_sensitive="true").json()["total"] == 1


def test_date_and_aktenzeichen(client):
    body = preview(client, pdf_with_lines(SENSIBLE), ["geburtsdatum", "aktenzeichen"]).json()
    texts = {f["text"] for f in body["findings"]}
    assert "14.03.1978" in texts
    assert "AZ-1234/26" in texts


def test_no_findings_is_422(client):
    r = redact(client, pdf_with_lines(["Nur harmloser Text"]), ["iban"])
    assert r.status_code == 422
    assert "Keine Fundstellen" in r.json()["detail"]


def test_unknown_pattern_400(client):
    r = preview(client, pdf_with_lines(SENSIBLE), ["gibtsnicht"])
    assert r.status_code == 400


def test_requires_pattern_or_term(client):
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": "[]", "terms": ""},
        files={"file": ("d.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 400


# ── Schrifteinbettung ─────────────────────────────────────────


def test_font_classification():
    assert svc.classify_font("Arial-BoldMT") == ("sans", True, False)
    assert svc.classify_font("TimesNewRomanPS-ItalicMT") == ("serif", False, True)
    assert svc.classify_font("CourierNewPSMT") == ("mono", False, False)
    assert svc.classify_font("") == ("sans", False, False)


@pytest.mark.skipif(
    svc.select_font_file("Arial", "Test") is None, reason="keine TTF-Schriften im System"
)
def test_text_edit_keeps_unicode(client):
    """Umlaute, Gedankenstrich, Euro und Anführungszeichen überleben die Bearbeitung."""
    text = "Fördermaßnahme — „Größe“ 30 m² · 1.234,56 €"
    edits = [
        {
            "page": 1,
            "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.2},
            "text": text,
            "font_size": 12,
            "font": "Arial",
        }
    ]
    r = client.post(
        "/api/pdf-extras/edit-text-blocks",
        data={"edits": json.dumps(edits)},
        files={"file": ("d.pdf", make_pdf(1, "Original"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        result = doc[0].get_text()
        fonts = [f[3] for f in doc[0].get_fonts(full=True)]
    for part in ("Fördermaßnahme", "—", "„Größe“", "m²", "€"):
        assert part in result, f"{part!r} fehlt im Ergebnis: {result!r}"
    assert any("Liberation" in f or "DejaVu" in f for f in fonts), fonts


@pytest.mark.skipif(
    svc.select_font_file("Arial", "Test") is None, reason="keine TTF-Schriften im System"
)
def test_font_style_is_carried_over(client):
    """Fett/kursiv des Originalblocks werden fortgeführt."""
    edits = [
        {
            "page": 1,
            "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.18},
            "text": "Fetter Text",
            "font_size": 12,
            "font": "Arial-BoldMT",
        }
    ]
    r = client.post(
        "/api/pdf-extras/edit-text-blocks",
        data={"edits": json.dumps(edits)},
        files={"file": ("d.pdf", make_pdf(1, "Original"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        fonts = [f[3] for f in doc[0].get_fonts(full=True)]
    assert any("Bold" in f for f in fonts), fonts


def test_glyph_fallback_selects_broader_font():
    """Zeichen außerhalb von Liberation führen zur breiteren Schrift."""
    liberation = svc.select_font_file("Arial", "Normaler Text")
    broad = svc.select_font_file("Arial", "Haken ✓")
    if liberation is None or broad is None:
        pytest.skip("keine TTF-Schriften im System")
    assert "Liberation" in liberation
    assert "DejaVu" in broad


def test_fallback_to_base14_without_fonts(client, monkeypatch):
    """Ohne Schriftdateien bleibt die Bearbeitung möglich (Latin-1-Ersatz)."""
    monkeypatch.setattr(svc, "select_font_file", lambda *a, **k: None)
    edits = [
        {
            "page": 1,
            "bbox": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.2},
            "text": "Text mit — Gedankenstrich",
            "font_size": 12,
            "font": "Arial",
        }
    ]
    r = client.post(
        "/api/pdf-extras/edit-text-blocks",
        data={"edits": json.dumps(edits)},
        files={"file": ("d.pdf", make_pdf(1, "Original"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert int(r.headers["X-Warnings"]) >= 1
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert "Gedankenstrich" in doc[0].get_text()
