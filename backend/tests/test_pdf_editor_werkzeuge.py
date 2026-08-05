"""Tests für bisher ungetestete pdf-editor-Endpunkte.

Abgedeckt: Seitenzahlen, Kopf-/Fußzeilen, Textsuche und -ersetzung,
Flatten sowie Inhaltsverzeichnis (schreiben/lesen, automatische Erkennung).
"""

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


# ── Seitenzahlen ──────────────────────────────────────────────


def test_page_numbers_ab_startseite(client):
    pdf = make_pdf(3, "Inhalt")
    r = client.post(
        "/api/pdf-editor/page-numbers",
        data={
            "format_str": "Nummer {page} von {total}",
            "position": "bottom-center",
            "start_page": "2",
            "start_number": "1",
        },
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert "d_nummeriert.pdf" in r.headers["content-disposition"]
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert "Nummer" not in doc[0].get_text()  # vor start_page keine Nummer
        assert "Nummer 1 von 3" in doc[1].get_text()
        assert "Nummer 2 von 3" in doc[2].get_text()
        assert "Inhalt Seite 2" in doc[1].get_text()  # Original bleibt erhalten


# ── Kopf- und Fußzeile ────────────────────────────────────────


def test_header_footer_mit_platzhaltern(client):
    pdf = make_pdf(2, "Inhalt")
    r = client.post(
        "/api/pdf-editor/header-footer",
        data={
            "header_left": "Aktenzeichen 12/34",
            "footer_right": "Blatt {page}/{total}",
        },
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text()
            assert "Aktenzeichen 12/34" in text
            assert f"Blatt {i}/2" in text


# ── Textsuche ─────────────────────────────────────────────────


def test_text_search_findet_alle_treffer(client):
    pdf = make_pdf(2, "Fundstelle Alpha")
    r = client.post(
        "/api/pdf-editor/text/search",
        data={"search": "Fundstelle"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == "Fundstelle"
    assert body["total_found"] == 2
    assert [t["page"] for t in body["results"]] == [1, 2]
    # Koordinaten sind auf 0..1 normalisiert
    bbox = body["results"][0]["bbox"]
    assert 0 <= bbox["x0"] < bbox["x1"] <= 1
    assert 0 <= bbox["y0"] < bbox["y1"] <= 1


def test_text_search_ohne_treffer(client):
    r = client.post(
        "/api/pdf-editor/text/search",
        data={"search": "Nichtvorhandenes"},
        files={"file": ("d.pdf", make_pdf(1, "Inhalt"), "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["total_found"] == 0


def test_text_search_beachtet_grossschreibung(client):
    """Sollverhalten: match_case=True liefert nur Treffer in exakter Schreibung."""
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "klein alt und gross ALT")
    pdf = doc.tobytes()
    doc.close()

    r = client.post(
        "/api/pdf-editor/text/search",
        data={"search": "ALT", "match_case": "true"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["total_found"] == 1  # nur das exakt geschriebene "ALT"


# ── Text ersetzen ─────────────────────────────────────────────


def test_text_replace_nur_auf_gewaehlter_seite(client):
    """Sollverhalten: Ersatz erscheint, Suchtext verschwindet, übrige
    Seiten bleiben unangetastet. Funktioniert, solange der Ersatztext in
    die Fläche des Suchtreffers passt."""
    pdf = make_pdf(3, "Kennwort Alpha")
    r = client.post(
        "/api/pdf-editor/text/replace",
        data={"search": "Alpha", "replace": "Beta", "pages": json.dumps([1])},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    assert r.headers["X-Replacements"] == "1"
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        text1 = doc[0].get_text()
        assert "Beta" in text1
        assert "Alpha" not in text1
        assert "Kennwort" in text1  # Nachbartext bleibt stehen
        for i in (1, 2):  # nicht gewählte Seiten unversehrt
            assert "Alpha" in doc[i].get_text()
            assert "Beta" not in doc[i].get_text()


def test_text_replace_laengerer_ersatztext(client):
    """Sollverhalten: auch ein längerer Ersatztext muss im Ergebnis stehen."""
    pdf = make_pdf(1, "Betrag: ALT Ende")
    r = client.post(
        "/api/pdf-editor/text/replace",
        data={"search": "ALT", "replace": "Ersatztext-deutlich-laenger-als-vorher"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        text = doc[0].get_text()
        assert "Ersatztext-deutlich-laenger-als-vorher" in text
        assert "ALT" not in text
        assert "Ende" in text  # Nachbartext bleibt stehen


# ── Flatten ───────────────────────────────────────────────────


def test_flatten_entfernt_annotationen(client):
    # PDF mit Highlight-Annotation auf Seite 1
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Markierter Inhalt")
    annot = page.add_highlight_annot(fitz.Rect(70, 60, 160, 76))
    annot.update()
    doc.new_page().insert_text((72, 72), "Seite zwei")
    pdf = doc.tobytes()
    doc.close()

    r = client.post(
        "/api/pdf-editor/flatten", files={"file": ("d.pdf", pdf, "application/pdf")}
    )
    assert r.status_code == 200, r.text
    assert "d_flatten.pdf" in r.headers["content-disposition"]
    with fitz.open(stream=r.content, filetype="pdf") as out:
        assert out.page_count == 2
        # Keine Annotationen mehr; Seiten sind eingebrannt (gerendert)
        for page in out:
            assert list(page.annots() or []) == []
        assert len(out[0].get_images(full=True)) >= 1


# ── Inhaltsverzeichnis ────────────────────────────────────────


def test_toc_schreiben_und_lesen(client):
    pdf = make_pdf(3, "Kapiteltext")
    entries = [
        {"level": 1, "title": "Kapitel Eins", "page": 1},
        {"level": 2, "title": "Unterkapitel", "page": 2},
        {"level": 1, "title": "Anhang", "page": 99},  # wird auf letzte Seite begrenzt
    ]
    r = client.post(
        "/api/pdf-editor/toc/write",
        data={"entries": json.dumps(entries)},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    mit_toc = r.content
    with fitz.open(stream=mit_toc, filetype="pdf") as doc:
        assert doc.get_toc() == [
            [1, "Kapitel Eins", 1],
            [2, "Unterkapitel", 2],
            [1, "Anhang", 3],
        ]

    # Rückweg über den Lese-Endpunkt
    r = client.post(
        "/api/pdf-editor/toc/read",
        files={"file": ("d.pdf", mit_toc, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["page_count"] == 3
    assert [(e["level"], e["title"], e["page"]) for e in body["entries"]] == [
        (1, "Kapitel Eins", 1),
        (2, "Unterkapitel", 2),
        (1, "Anhang", 3),
    ]


def test_toc_write_ungueltiges_json_400(client):
    r = client.post(
        "/api/pdf-editor/toc/write",
        data={"entries": "kein json"},
        files={"file": ("d.pdf", make_pdf(1, "x"), "application/pdf")},
    )
    assert r.status_code == 400


def test_toc_auto_detect_nach_schriftgroesse(client):
    # Überschriften über Schriftgröße: 24 pt → H1, 15 pt → H2, 11 pt → Fließtext
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Hauptueberschrift", fontsize=24)
    page.insert_text((72, 150), "Unterueberschrift", fontsize=15)
    page.insert_text((72, 200), "Fliesstext in normaler Groesse", fontsize=11)
    pdf = doc.tobytes()
    doc.close()

    r = client.post(
        "/api/pdf-editor/toc/auto-detect",
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    entries = r.json()["entries"]
    assert [(e["level"], e["title"], e["page"]) for e in entries] == [
        (1, "Hauptueberschrift", 1),
        (2, "Unterueberschrift", 1),
    ]
