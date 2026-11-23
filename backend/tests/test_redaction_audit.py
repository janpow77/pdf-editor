"""Prüfplan Schwärzung (docs/pruefplan-schwaerzung.md) — automatisierte Testfälle.

Kennungen wie F05 oder S03 verweisen auf den Prüfplan, V1 … auf die dort
erfassten Vorbefunde. Neue bekannte Mängel als ``known("Vn", …)`` markieren
(xfail strict): Wird der Mangel behoben, schlägt der Test als XPASS an.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.pdf_extras_service import get_pdf_extras
from tests import redaction_corpus as kc

svc = get_pdf_extras()
SECRET = "erika@example.org"
BACKEND = Path(__file__).resolve().parents[1]


def known(defect: str, reason: str):
    return pytest.mark.xfail(strict=True, reason=f"{defect}: {reason}")


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def page_text(pdf: bytes) -> str:
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        return "\n".join(p.get_text() for p in doc)


def redacted(pdf: bytes, patterns=(), terms=(), **kw) -> bytes:
    result = svc.redact_patterns(pdf, list(patterns), list(terms), **kw)
    assert result.success, result.error
    return result.file_content


def findings(pdf: bytes, patterns=(), terms=(), **kw) -> list[dict]:
    found = svc.find_pattern_matches(pdf, list(patterns), list(terms), **kw)
    assert found is not None
    return found[0]


# ── F: Funktion ─────────────────────────────────────────────────


@pytest.mark.parametrize("case", kc.K02, ids=lambda c: c.expected[0][1])
def test_f01_pattern_finds_supported_format(case):
    pattern, text = case.expected[0]
    hits = {f["text"] for f in findings(kc.pdf_from_lines([case.line]), [pattern])}
    assert text in hits


@pytest.mark.parametrize("case", kc.K03, ids=lambda c: c.line[:30])
def test_f02_standard_patterns_spare_technical_text(case):
    hits = findings(kc.pdf_from_lines([case.line]), kc.STANDARD_PATTERNS)
    assert hits == [], hits


def test_f03_overlapping_patterns_counted_once():
    pdf = kc.pdf_from_lines(["Konto DE89 3704 0044 0532 0130 00 bei der Bank"])
    _, counts = svc.find_pattern_matches(pdf, kc.STANDARD_PATTERNS, [])
    assert counts == {"iban": 1}


def test_f04_term_list_case_and_whole_word():
    pdf = kc.pdf_from_lines(["Herr Meier, Frau MEIER und der Meierhof"])
    insensitive = {f["text"] for f in findings(pdf, terms=["meier"])}
    assert insensitive == {"Meier", "MEIER"}
    sensitive = [f["text"] for f in findings(pdf, terms=["Meier"], case_sensitive=True)]
    assert sensitive == ["Meier"]
    partial = findings(pdf, terms=["Meier"], whole_word=False)
    assert len(partial) == 3


def test_f05_single_term_respects_match_case():
    pdf = kc.pdf_from_lines(["Herr MEIER und Herr Meier"])
    result = svc.redact_search(pdf, "Meier", match_case=True)
    assert result.metadata["redactions"] == 1
    assert "MEIER" in page_text(result.file_content)


def test_f06_term_across_line_break():
    pdf = kc.pdf_from_lines(["Antragstellerin ist Erika", "Musterfrau aus Kassel."])
    assert {f["text"] for f in findings(pdf, terms=["Erika Musterfrau"])} == {"Erika Musterfrau"}


def test_f06_term_with_hyphenation():
    pdf = kc.pdf_from_lines(["Frau Muster-", "frau wohnt dort."])
    assert findings(pdf, terms=["Musterfrau"])


def test_f07_no_match_across_columns():
    """Zwei Spalten dürfen nicht zu einem Treffer verschmelzen."""
    assert findings(kc.two_columns_pdf(), terms=["Erika Musterfrau"]) == []


def test_f08_neighbour_words_stay_readable():
    pdf = kc.pdf_from_lines(["Kontakt: erika@example.org, Telefon folgt"])
    text = page_text(redacted(pdf, ["email"]))
    assert SECRET not in text
    assert "Kontakt:" in text and "Telefon" in text


def test_f08_partial_word_only_redacts_match():
    pdf = kc.pdf_from_lines(["Der Meierhof liegt am Ort"])
    assert "hof" in page_text(redacted(pdf, terms=["Meier"], whole_word=False))


def test_f08_punctuation_survives():
    pdf = kc.pdf_from_lines(["(erika@example.org), weiter"])
    text = page_text(redacted(pdf, ["email"]))
    assert "(" in text and ")," in text


def test_f09_preview_count_matches_redaction(client):
    pdf = kc.pdf_from_lines(
        ["Konto DE89 3704 0044 0532 0130 00", "Mail erika@example.org", "Name Erika Musterfrau"]
    )
    data = {"patterns": json.dumps(["iban", "email"]), "terms": "Erika Musterfrau"}
    files = {"file": ("d.pdf", pdf, "application/pdf")}
    preview = client.post("/api/pdf-extras/redact-patterns", data={**data, "preview": "true"}, files=files)
    applied = client.post("/api/pdf-extras/redact-patterns", data=data, files=files)
    assert preview.status_code == applied.status_code == 200
    assert preview.json()["total"] == int(applied.headers["X-Redactions"]) == 3


def test_f10_regex_characters_in_terms_are_literal():
    pdf = kc.pdf_from_lines(["axb und a.b sowie (x)"])
    assert [f["text"] for f in findings(pdf, terms=["a.b"])] == ["a.b"]
    assert [f["text"] for f in findings(pdf, terms=["(x)"])] == ["(x)"]


def test_f10_term_limit_is_not_silent(client):
    terms = [f"Begriff{i:03d}" for i in range(201)]
    pdf = kc.pdf_from_lines(["Begriff200 steht hier"])
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": "[]", "terms": "\n".join(terms), "preview": "true"},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 400 or r.json()["total"] == 1


def test_f11_result_is_valid_pdf():
    import io

    import pikepdf

    out = redacted(kc.pdf_from_lines(["Mail erika@example.org"] * 3), ["email"])
    with pikepdf.open(io.BytesIO(out)) as pdf:
        assert pdf.check_pdf_syntax() == []
        assert len(pdf.pages) == 1


def test_f12_unrelated_content_preserved():
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page(width=420, height=595)
        page.insert_text((60, 80), f"Seite {i + 1} mit erika@example.org", fontsize=11)
        page.insert_text((60, 120), "Unbeteiligter Sachverhalt", fontsize=11)
        page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(60, 300, 200, 315), "uri": "https://example.org/"})
    doc[1].set_rotation(90)
    src = doc.tobytes()
    doc.close()
    out = redacted(src, ["email"])
    with fitz.open(stream=out, filetype="pdf") as doc:
        assert doc.page_count == 3
        assert doc[1].rotation == 90
        assert doc[0].rect.width == 420
        assert all("Unbeteiligter Sachverhalt" in p.get_text() for p in doc)
        assert all(p.get_links() for p in doc)


# ── S: Sicherheit der Entfernung ────────────────────────────────


def test_s01_s02_page_text_and_raw_bytes_clean():
    out = redacted(kc.pdf_from_lines([f"Kontakt: {SECRET}"]), ["email"])
    assert kc.leaks(out, SECRET) == []


HIDDEN = {
    "metadata": ("V2", "Metadaten werden nicht bereinigt"),
    "annotation": ("V2", "Kommentare werden nicht bereinigt"),
    "toc": ("V2", "Lesezeichen werden nicht bereinigt"),
    "link": ("V2", "mailto-Links bleiben stehen"),
    "widget": ("V1", "Formularfeldwert bleibt trotz Zählung stehen"),
    "attachment": ("V2", "Dateianhänge werden nicht durchsucht"),
}


@pytest.mark.parametrize(
    "where",
    [*HIDDEN, "white_text", "outside_cropbox"],
)
def test_s03_to_s06_hidden_content_removed(where):
    src = kc.single_hidden_pdf(SECRET, where)
    out = redacted(src, ["email"])
    assert kc.leaks(out, SECRET) == []


def test_s07_image_pixels_under_finding_removed():
    src = kc.text_over_image_pdf(SECRET)
    with fitz.open(stream=src, filetype="pdf") as doc:
        box = doc[0].search_for(SECRET)[0]
    out = redacted(src, ["email"])
    with fitz.open(stream=out, filetype="pdf") as doc:
        pix = doc[0].get_pixmap(clip=box, dpi=72)
        red = sum(
            1
            for y in range(pix.height)
            for x in range(pix.width)
            if pix.pixel(x, y)[:3] == (200, 30, 30)
        )
        assert red == 0, f"{red} rote Pixel unter der Schwärzung"
        # Rest des Bildes bleibt erhalten
        assert doc[0].get_images()


def test_s09_old_revision_not_shipped():
    old = "geheim@example.org"
    src = kc.old_revision_pdf(old, f"Kontakt: {SECRET}")
    # Vorbedingung: die erste gespeicherte Fassung enthält den alten Text noch
    assert len(kc.revisions(src)) == 2
    assert old in page_text(kc.revisions(src)[0])
    out = redacted(src, ["email"])
    assert len(kc.revisions(out)) == 1
    assert kc.leaks(out, old) == []


def test_s13_preview_does_not_persist_upload(client, tmp_path):
    uploads = BACKEND.parent / "uploads"
    before = set(uploads.rglob("*")) if uploads.exists() else set()
    client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps(["email"]), "preview": "true"},
        files={"file": ("d.pdf", kc.pdf_from_lines([SECRET]), "application/pdf")},
    )
    after = set(uploads.rglob("*")) if uploads.exists() else set()
    assert after == before


# ── L: Leistung ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "line",
    ["1" * 5000, " " * 5000 + "x", "a@" + "a." * 2500, "+49 " + "1 " * 2500, "DE" + "1" * 5000],
    ids=["ziffern", "leerzeichen", "email", "telefon", "iban"],
)
def test_l07_no_catastrophic_backtracking(line):
    pdf = kc.pdf_from_lines([line[:400]] * 10, fontsize=4)
    start = time.perf_counter()
    findings(pdf, kc.STANDARD_PATTERNS)
    assert time.perf_counter() - start < 2.0


def test_l01_hundred_dense_pages_within_budget():
    pdf = kc.big_pdf(100)
    start = time.perf_counter()
    out = redacted(pdf, ["iban", "email"], ["Erika Musterfrau"])
    elapsed = time.perf_counter() - start
    assert "erika@example.org" not in page_text(out)
    assert elapsed < 30, f"{elapsed:.1f} s für 100 dichte Seiten"


# ── K: KI-Namenserkennung ───────────────────────────────────────

ner = pytest.mark.skipif(not svc.ner_available(), reason="spaCy-Modell nicht installiert")


@ner
def test_k01_ner_recall_on_paragraph():
    text, names = kc.ner_text()
    pdf = kc.wrapped_paragraph_pdf(text, width=480)
    hits = " ".join(f["text"] for f in findings(pdf, ["ki_namen"]))
    surnames = [n.split()[-1] for n in names]
    recall = sum(1 for s in surnames if s in hits) / len(surnames)
    assert recall >= 0.5, f"Trefferquote Nachnamen {recall:.0%}"


# ── B: Batch ────────────────────────────────────────────────────


def test_b01_b02_batch_log_and_untouched_file(client):
    import io
    import zipfile

    with_hit = kc.pdf_from_lines([f"Kontakt: {SECRET}"])
    without = kc.pdf_from_lines(["Nur Sachverhalt"])
    r = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "redact", "params": json.dumps({"patterns": ["email"]})},
        files=[
            ("files", ("a.pdf", with_hit, "application/pdf")),
            ("files", ("b.pdf", without, "application/pdf")),
        ],
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = set(zf.namelist())
        assert {"a_geschwaerzt.pdf", "b.pdf", "schwaerzungen.txt"} <= names
        assert kc.leaks(zf.read("a_geschwaerzt.pdf"), SECRET) == []
        log = zf.read("schwaerzungen.txt").decode()
        assert "a.pdf: 1" in log and "b.pdf: 0" in log


# ── R: Robustheit ───────────────────────────────────────────────


def test_r01_encrypted_pdf_rejected_cleanly(client):
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), SECRET)
    enc = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="geheim", owner_pw="geheim")
    doc.close()
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps(["email"]), "preview": "true"},
        files={"file": ("d.pdf", enc, "application/pdf")},
    )
    assert r.status_code in (400, 422), r.status_code


def test_r03_garbage_rejected_cleanly(client):
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps(["email"]), "preview": "true"},
        files={"file": ("d.pdf", b"kein PDF", "application/pdf")},
    )
    assert r.status_code == 400, r.status_code


def test_v7_scanned_pages_reported(client):
    r = client.post(
        "/api/pdf-extras/redact-patterns",
        data={"patterns": json.dumps(["email"]), "preview": "true"},
        files={"file": ("d.pdf", kc.scanned_pdf(SECRET), "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json().get("pages_without_text") == [1]


def test_v11_broken_spacy_install_does_not_break_backend():
    code = (
        "import sys, importlib.abc\n"
        "class Broken(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name == 'spacy' or name.startswith('spacy.'):\n"
        "            raise ValueError('numpy.dtype size changed')\n"
        "sys.meta_path.insert(0, Broken())\n"
        "import app.pdf_backend as b\n"
        "assert b.SPACY_AVAILABLE is False\n"
    )
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-500:]


# ── G: Pflicht-Vorschau (Plan → Auswahl → Anwendung) ───────────


def plan_of(client, pdf: bytes, patterns=(), terms="", **extra) -> dict:
    r = client.post(
        "/api/pdf-extras/redact/plan",
        data={"patterns": json.dumps(list(patterns)), "terms": terms, **extra},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def apply_with(client, pdf: bytes, plan: dict, selected=None, areas=(), sanitize=True):
    payload = {
        "sha256": plan["sha256"],
        "criteria": plan["criteria"],
        "selected": [c["id"] for c in plan["candidates"]] if selected is None else list(selected),
        "areas": list(areas),
        "sanitize": sanitize,
    }
    return client.post(
        "/api/pdf-extras/redact/apply",
        data={"plan": json.dumps(payload)},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )


def test_g01_plan_lists_text_and_hidden_findings(client):
    plan = plan_of(client, kc.hidden_content_pdf(SECRET), ["email"])
    locations = {c["location"] for c in plan["candidates"]}
    assert "Seitentext" in locations
    assert {"Lesezeichen", "Kommentar", "Link", "XMP-Metadaten"} <= locations
    assert any(loc.startswith("Formularfeld") for loc in locations)
    assert any(loc.startswith("Dateianhang") for loc in locations)
    assert any(loc.startswith("Metadaten") for loc in locations)
    text = [c for c in plan["candidates"] if c["kind"] == "text"][0]
    x0, y0, x1, y1 = text["rects"][0]
    assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
    assert plan["cleanup"]["attachments"] == 1


def test_g02_deselected_finding_stays_readable(client):
    pdf = kc.pdf_from_lines(["Herr Meier schreibt.", "Frau Meier antwortet."])
    plan = plan_of(client, pdf, terms="Meier")
    assert plan["total"] == 2
    first, second = plan["candidates"]
    r = apply_with(client, pdf, plan, selected=[first["id"]])
    assert r.status_code == 200, r.text
    text = page_text(r.content)
    assert "Herr" in text and "Frau Meier" in text
    assert text.count("Meier") == 1
    assert r.headers["X-Redactions"] == "1"


def test_g03_identical_plan_ids_are_stable(client):
    pdf = kc.pdf_from_lines([f"Kontakt {SECRET}", "Konto DE89 3704 0044 0532 0130 00"])
    a = plan_of(client, pdf, ["email", "iban"])
    b = plan_of(client, pdf, ["email", "iban"])
    assert [c["id"] for c in a["candidates"]] == [c["id"] for c in b["candidates"]]


def test_g04_plan_for_other_file_rejected(client):
    pdf = kc.pdf_from_lines([f"Kontakt {SECRET}"])
    plan = plan_of(client, pdf, ["email"])
    other = kc.pdf_from_lines([f"Anderer Kontakt {SECRET}"])
    assert apply_with(client, other, plan).status_code == 409


def test_g05_unknown_id_rejected(client):
    pdf = kc.pdf_from_lines([f"Kontakt {SECRET}"])
    plan = plan_of(client, pdf, ["email"])
    assert apply_with(client, pdf, plan, selected=["0" * 16]).status_code == 409


def test_g06_manual_area_redacts_text(client):
    pdf = kc.pdf_from_lines(["Unterschrift: Max Mustermann", "Rest bleibt"])
    plan = plan_of(client, pdf, terms="nichtvorhanden")
    assert plan["total"] == 0
    page = plan["pages"][0]
    with fitz.open(stream=pdf, filetype="pdf") as doc:
        box = doc[0].search_for("Max Mustermann")[0]
    area = [box.x0 / page["width"], box.y0 / page["height"], box.x1 / page["width"], box.y1 / page["height"]]
    r = apply_with(client, pdf, plan, selected=[], areas=[{"page": 1, "rect": area}])
    assert r.status_code == 200, r.text
    text = page_text(r.content)
    assert "Mustermann" not in text and "Rest bleibt" in text


def test_g07_rotated_page_rects_match_display(client):
    doc = fitz.open()
    page = doc.new_page(width=400, height=600)
    page.insert_text((50, 100), SECRET, fontsize=14)
    page.set_rotation(90)
    pdf = doc.tobytes()
    pix = page.get_pixmap(dpi=72)
    dark = [(x, y) for y in range(pix.height) for x in range(pix.width) if pix.pixel(x, y)[0] < 100]
    doc.close()
    plan = plan_of(client, pdf, ["email"])
    x0, y0, x1, y1 = plan["candidates"][0]["rects"][0]
    info = plan["pages"][0]
    assert (info["width"], info["height"]) == (600, 400)
    cx = sum(x for x, _ in dark) / len(dark) / pix.width
    cy = sum(y for _, y in dark) / len(dark) / pix.height
    assert x0 <= cx <= x1 and y0 <= cy <= y1
    # Bereich in Anzeigekoordinaten auf gedrehter Seite
    r = apply_with(client, pdf, plan, selected=[], areas=[{"page": 1, "rect": [x0, y0, x1, y1]}])
    assert r.status_code == 200, r.text
    assert SECRET not in page_text(r.content)


def test_g08_fail_closed_when_text_survives(client, monkeypatch):
    """Lässt die Schwärzung Text stehen, wird nichts ausgeliefert."""
    monkeypatch.setattr(fitz.Page, "apply_redactions", lambda self, *a, **k: True)
    pdf = kc.pdf_from_lines([f"Kontakt {SECRET}"])
    plan = plan_of(client, pdf, ["email"])
    r = apply_with(client, pdf, plan)
    assert r.status_code == 422
    assert "Nachprüfung" in r.json()["detail"]
    assert SECRET not in r.json()["detail"]


def test_g09_sanitize_removes_metadata_and_attachments(client):
    pdf = kc.hidden_content_pdf(SECRET)
    plan = plan_of(client, pdf, ["email"])
    r = apply_with(client, pdf, plan)
    assert r.status_code == 200, r.text
    assert kc.leaks(r.content, SECRET) == []
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert not doc.embfile_names()
        assert not any((doc.metadata or {}).get(k) for k in ("author", "title", "subject"))


def test_g10_batch_apply_with_individual_plans(client):
    import io
    import zipfile

    a = kc.pdf_from_lines([f"Kontakt {SECRET}", "Herr Meier"])
    b = kc.pdf_from_lines(["Nur Sachverhalt"])
    plan_a = plan_of(client, a, ["email"], terms="Meier")
    plan_b = plan_of(client, b, ["email"], terms="Meier")
    keep_meier = [c["id"] for c in plan_a["candidates"] if c["source"] == "email"]
    payloads = [
        {"sha256": plan_a["sha256"], "criteria": plan_a["criteria"], "selected": keep_meier},
        {"sha256": plan_b["sha256"], "criteria": plan_b["criteria"], "selected": []},
    ]
    r = client.post(
        "/api/pdf-extras/redact/apply-batch",
        data={"plans": json.dumps(payloads)},
        files=[("files", ("a.pdf", a, "application/pdf")), ("files", ("b.pdf", b, "application/pdf"))],
    )
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        out_a = zf.read("a_geschwaerzt.pdf")
        assert SECRET not in page_text(out_a) and "Meier" in page_text(out_a)
        # Ohne Auswahl wird trotzdem bereinigt und nachgeprüft (M2).
        out_b = zf.read("b_bereinigt.pdf")
        assert "Nur Sachverhalt" in page_text(out_b)
        log = zf.read("schwaerzungen.txt").decode()
        assert "1 abgewählt" in log and "nur bereinigt" in log and SECRET not in log


def test_g11_term_limit_rejected_on_plan(client):
    terms = "\n".join(f"Begriff{i}" for i in range(201))
    r = client.post(
        "/api/pdf-extras/redact/plan",
        data={"patterns": "[]", "terms": terms},
        files={"file": ("d.pdf", kc.pdf_from_lines(["x"]), "application/pdf")},
    )
    assert r.status_code == 400 and "200" in r.json()["detail"]


def test_g12_scanned_page_flagged_in_plan(client):
    plan = plan_of(client, kc.scanned_pdf(SECRET), ["email"])
    assert plan["pages_without_text"] == [1]
    assert plan["total"] == 0


def test_g13_outside_cropbox_flagged(client):
    pdf = kc.single_hidden_pdf(SECRET, "outside_cropbox")
    plan = plan_of(client, pdf, ["email"])
    outside = [c for c in plan["candidates"] if c["outside_view"]]
    assert len(outside) == 1
    r = apply_with(client, pdf, plan)
    assert r.status_code == 200, r.text
    assert kc.leaks(r.content, SECRET) == []
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc[0].cropbox == fitz.Rect(0, 0, 595, 700)


@ner
def test_g14_ner_uses_paragraph_context(client):
    text, names = kc.ner_text()
    pdf = kc.wrapped_paragraph_pdf(text, width=260)
    plan = plan_of(client, pdf, ["ki_namen"])
    hits = " ".join(c["text"] for c in plan["candidates"])
    surnames = [n.split()[-1] for n in names]
    recall = sum(1 for s in surnames if s in hits) / len(surnames)
    assert recall >= 0.6, f"Trefferquote Nachnamen bei schmalem Satzspiegel {recall:.0%}"


# ── A: Befunde der Code-Prüfung vom 19.11.2026 ─────────────────


def _pdf(build) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    build(doc, page)
    data = doc.tobytes()
    doc.close()
    return data


def _skip_redaction_below(monkeypatch, y: float):
    """Simulierter Ausfall: Schwärzungen unterhalb von ``y`` greifen nicht."""
    orig = fitz.Page.add_redact_annot

    def patched(self, quad, *a, **k):
        if fitz.Rect(quad).y0 > y:
            return None
        return orig(self, quad, *a, **k)

    monkeypatch.setattr(fitz.Page, "add_redact_annot", patched)


@pytest.mark.parametrize(
    "lines, terms",
    [
        (["Herr Mustermann kam.", "Gez. MUSTERMANN"], "Mustermann"),
        (["Max Mustermann kam.", "Gez. Herr Mustermann"], "Max Mustermann\nMustermann"),
    ],
    ids=["schreibweise", "verschachtelt"],
)
def test_a_k1_variants_and_nesting_fail_closed(client, monkeypatch, lines, terms):
    """K1: Schreibvarianten und verschachtelte Begriffe werden mitgezählt."""
    pdf = kc.pdf_from_lines(lines)
    plan = plan_of(client, pdf, terms=terms)
    first_line = min(c["pdf_rect"][1] for c in plan["candidates"])
    _skip_redaction_below(monkeypatch, first_line + 5)
    r = apply_with(client, pdf, plan)
    assert r.status_code == 422, r.text
    assert "Seite 1" in r.json()["detail"]


def test_a_k1_listbox_option_removed(client):
    """K1: Darstellung eines Auswahlfelds steht im Seitentext — das Feld wird entfernt."""

    def build(doc, page):
        page.insert_text((72, 60), "Akte Krüger", fontsize=11)
        w = fitz.Widget()
        w.field_type = fitz.PDF_WIDGET_TYPE_LISTBOX
        w.field_name = "liste"
        w.rect = fitz.Rect(72, 150, 300, 220)
        w.choice_values = ["Meier", "KRÜGER", "Schmidt"]
        w.field_value = "Meier"
        page.add_widget(w)

    pdf = _pdf(build)
    plan = plan_of(client, pdf, terms="Krüger")
    r = apply_with(client, pdf, plan)
    assert r.status_code == 200, r.text
    assert "krüger" not in page_text(r.content).casefold()
    assert b"KR\xc3\x9cGER" not in r.content


def test_a_h1_hidden_layer_and_outside_mediabox(client):
    """H1: Text auf ausgeblendeter Ebene und außerhalb der MediaBox."""

    def build(doc, page):
        page.insert_text((72, 72), "Sichtbar", fontsize=11)
        ocg = doc.add_ocg("intern", on=False)
        page.insert_text((72, 100), "Krause intern", fontsize=11, oc=ocg)
        xref = page.get_contents()[0]
        page.insert_font("helv")
        doc.update_stream(xref, doc.xref_stream(xref) + b"\nBT /helv 11 Tf 1 0 0 1 72 -200 Tm (Krause unten) Tj ET")

    pdf = _pdf(build)
    plan = plan_of(client, pdf, terms="Krause")
    assert len(plan["candidates"]) == 2
    r = apply_with(client, pdf, plan)
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc.get_layer().get("off"), "Ebene bleibt ausgeblendet"
        raw = b"".join(doc.xref_stream(x) or b"" for x in range(1, doc.xref_length()) if doc.xref_is_stream(x))
    assert b"Krause" not in raw


def test_a_h1_alt_actualtext_pieceinfo_xfa_custom_info(client):
    """H1: Alternativtext, ActualText, PieceInfo, XFA und eigene Info-Schlüssel."""

    def build(doc, page):
        page.insert_text((72, 60), "Bearbeiter Krause", fontsize=11)
        x = page.get_contents()[0]
        s = doc.xref_stream(x).replace(b"BT", b"/Span <</ActualText (Krause)>> BDC BT", 1).replace(b"ET", b"ET EMC", 1)
        doc.update_stream(x, s)
        pi = doc.get_new_xref()
        doc.update_object(pi, "<< /App << /Private (Original Krause) >> >>")
        doc.xref_set_key(page.xref, "PieceInfo", f"{pi} 0 R")
        xfa = doc.get_new_xref()
        doc.update_object(xfa, "<<>>")
        doc.update_stream(xfa, b"<xfa:datasets><name>Krause</name></xfa:datasets>", new=True)
        af = doc.get_new_xref()
        doc.update_object(af, f"<< /Fields [] /XFA {xfa} 0 R >>")
        doc.xref_set_key(doc.pdf_catalog(), "AcroForm", f"{af} 0 R")
        st = doc.get_new_xref()
        doc.update_object(st, "<< /Type /StructTreeRoot /K [<< /S /Figure /Alt (Foto Krause) >>] >>")
        doc.xref_set_key(doc.pdf_catalog(), "StructTreeRoot", f"{st} 0 R")
        doc.set_metadata({"title": "Akte"})
        info = int(doc.xref_get_key(-1, "Info")[1].split()[0])
        doc.xref_set_key(info, "Bearbeiter", "(Krause)")
        mx = doc.get_new_xref()
        doc.update_object(mx, "<< /Type /Metadata /Subtype /XML >>")
        doc.update_stream(mx, b"<x:xmpmeta><dc:creator>Krause</dc:creator></x:xmpmeta>", new=True)
        doc.xref_set_key(page.xref, "Metadata", f"{mx} 0 R")

    pdf = _pdf(build)
    for sanitize in (True, False):
        plan = plan_of(client, pdf, terms="Krause")
        r = apply_with(client, pdf, plan, sanitize=sanitize)
        assert r.status_code == 200, (sanitize, r.text)
        with fitz.open(stream=r.content, filetype="pdf") as doc:
            blobs = [doc.xref_object(x) for x in range(1, doc.xref_length())]
            blobs += [
                (doc.xref_stream(x) or b"").decode("latin-1")
                for x in range(1, doc.xref_length())
                if doc.xref_is_stream(x)
            ]
        assert not any("Krause" in b for b in blobs), sanitize


@pytest.mark.parametrize(
    "mediabox, cropbox, rotate",
    [
        ("[100 100 700 900]", "[100 100 700 900]", 0),
        ("[100 100 700 900]", "[200 200 600 800]", 0),
        ("[0 -800 600 0]", "[50 -700 550 -100]", 90),
    ],
)
def test_a_h2_offset_mediabox(client, mediabox, cropbox, rotate):
    """H2: Versetzte MediaBox führte zu HTTP 500 und falschen Anzeigerechtecken."""

    def build(doc, page):
        page.insert_font("helv")
        c = doc.get_new_xref()
        doc.update_object(c, "<<>>")
        doc.update_stream(c, b"BT /helv 11 Tf 1 0 0 1 300 500 Tm (Krause) Tj ET", new=True)
        doc.xref_set_key(page.xref, "Contents", f"{c} 0 R")
        doc.xref_set_key(page.xref, "MediaBox", mediabox)
        doc.xref_set_key(page.xref, "CropBox", cropbox)
        doc.xref_set_key(page.xref, "Rotate", str(rotate))

    pdf = _pdf(build)
    plan = plan_of(client, pdf, terms="Krause")
    assert len(plan["candidates"]) == 1
    if rotate == 0:
        # Anzeige-Rechteck gegen die Lage bei pdf.js prüfen: x = 300 im Nutzerraum
        crop = [float(v) for v in cropbox.strip("[]").split()]
        x0 = plan["candidates"][0]["rects"][0][0]
        assert abs(x0 - (300 - crop[0]) / (crop[2] - crop[0])) < 0.01
    r = apply_with(client, pdf, plan)
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc.xref_get_key(doc[0].xref, "CropBox")[1] == cropbox
        raw = b"".join(doc.xref_stream(x) or b"" for x in range(1, doc.xref_length()) if doc.xref_is_stream(x))
    assert b"Krause" not in raw


def test_a_h3_area_limits(client):
    pdf = kc.pdf_from_lines(["Text"])
    plan = plan_of(client, pdf, terms="Text")
    many = [{"page": 1, "rect": [0.1, 0.1, 0.2, 0.2]}] * 101
    r = apply_with(client, pdf, plan, areas=many)
    assert r.status_code == 400 and "je Seite" in r.json()["detail"]


@pytest.mark.parametrize(
    "text, term",
    [
        ("Frau \ufb01scher kam", "fischer"),
        ("Herr Mu\u0308ller kam", "Müller"),
        ("Herr Mus\u200btermann kam", "Mustermann"),
        ("Herr STRASSER kam", "Straßer"),
    ],
    ids=["ligatur", "nfd", "nullbreite", "eszett"],
)
def test_a_h4_normalisation(text, term):
    from app.services import redaction as R

    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if not font.exists():
        pytest.skip("DejaVu-Schrift fehlt")

    def build(doc, page):
        page.insert_text((72, 72), text, fontsize=11, fontfile=str(font), fontname="dv")

    plan = R.build_plan(_pdf(build), R.Criteria.from_input([], [term]))
    assert len(plan.candidates) == 1


def test_a_h4_double_name_and_same_baseline():
    from app.services import redaction as R

    wrapped = kc.wrapped_paragraph_pdf("Es erschien Frau Erika Müller-Lüdenscheidt und erklärte sich.", width=150)
    found = R.build_plan(wrapped, R.Criteria.from_input([], ["Müller-Lüdenscheidt"])).candidates
    assert len(found) == 1

    def build(doc, page):
        page.insert_text((72, 100), "Antragsteller: Max", fontsize=11)
        page.insert_text((200, 100), "Mustermann", fontsize=11)

    plan = R.build_plan(_pdf(build), R.Criteria.from_input([], ["Max Mustermann"]))
    assert [c.text for c in plan.candidates] == ["Max Mustermann"]


def test_a_m7_term_inside_deselected_email_stays_own_finding(client):
    pdf = kc.pdf_from_lines(["Kontakt max.mustermann@example.org"])
    plan = plan_of(client, pdf, ["email"], terms="mustermann")
    sources = sorted(c["source"] for c in plan["candidates"])
    assert sources == ["begriff:mustermann", "email"]
    only_term = [c["id"] for c in plan["candidates"] if c["source"].startswith("begriff:")]
    r = apply_with(client, pdf, plan, selected=only_term)
    assert r.status_code == 200, r.text
    assert "mustermann" not in page_text(r.content).casefold()


@pytest.mark.parametrize(
    "criteria",
    ["kaputt", {"patterns": "email"}, {"terms": [1, 2]}],
)
def test_a_m5_malformed_criteria_400(client, criteria):
    pdf = kc.pdf_from_lines(["Text"])
    payload = {"sha256": "x", "criteria": criteria, "selected": []}
    r = client.post(
        "/api/pdf-extras/redact/apply",
        data={"plan": json.dumps(payload)},
        files={"file": ("d.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 400, r.text


def test_a_m4_plan_as_file_part(client):
    """M4: Große Pläne kommen als Datei-Teil, ohne 1-MB-Grenze für Formularfelder."""
    pdf = kc.pdf_from_lines([f"Kontakt {SECRET}"])
    plan = plan_of(client, pdf, ["email"])
    payload = {"sha256": plan["sha256"], "criteria": plan["criteria"], "selected": [c["id"] for c in plan["candidates"]]}
    padded = json.dumps(payload) + " " * (2 * 1024 * 1024)
    r = client.post(
        "/api/pdf-extras/redact/apply",
        files={
            "file": ("d.pdf", pdf, "application/pdf"),
            "plan_file": ("plan.json", padded.encode(), "application/json"),
        },
    )
    assert r.status_code == 200, r.text
    assert SECRET not in page_text(r.content)


def test_a_m1_legacy_endpoints_disabled_by_default(client, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "redact_without_preview", False)
    pdf = kc.pdf_from_lines([f"Kontakt {SECRET}"])
    files = {"file": ("d.pdf", pdf, "application/pdf")}
    assert client.post("/api/pdf-extras/redact", data={"term": "Kontakt"}, files=files).status_code == 410
    r = client.post("/api/pdf-extras/redact-patterns", data={"patterns": '["email"]'}, files=files)
    assert r.status_code == 410
    preview = client.post(
        "/api/pdf-extras/redact-patterns", data={"patterns": '["email"]', "preview": "true"}, files=files
    )
    assert preview.status_code == 200
    batch = client.post(
        "/api/pdf-extras/batch",
        data={"operation": "redact", "params": json.dumps({"patterns": ["email"]})},
        files=[("files", ("a.pdf", pdf, "application/pdf"))],
    )
    assert batch.status_code == 410


def test_a_toc_only_selected_hit_replaced(client):
    def build(doc, page):
        page.insert_text((72, 60), "Text", fontsize=11)
        doc.set_toc([[1, "Anhörung Krause und Meier", 1]])

    pdf = _pdf(build)
    plan = plan_of(client, pdf, terms="Krause\nMeier")
    krause = [c["id"] for c in plan["candidates"] if c["text"] == "Krause"]
    r = apply_with(client, pdf, plan, selected=krause, sanitize=False)
    assert r.status_code == 200, r.text
    with fitz.open(stream=r.content, filetype="pdf") as doc:
        assert doc.get_toc()[0][1] == "Anhörung [geschwärzt] und Meier"


@pytest.mark.parametrize("skip", [False, True], ids=["greift", "ausfall"])
def test_a_m3_area_verified_on_cropped_page(client, monkeypatch, skip):
    """M3: Eigener Bereich auf beschnittener Seite wird nachgeprüft."""

    def build(doc, page):
        page.insert_text((120, 160), "Gutachter Krause", fontsize=11)
        page.set_cropbox(fitz.Rect(50, 50, 545, 792))

    pdf = _pdf(build)
    plan = plan_of(client, pdf, terms="Krause")
    rect = plan["candidates"][0]["rects"][0]
    if skip:
        _skip_redaction_below(monkeypatch, -1)
    r = apply_with(client, pdf, plan, selected=[], areas=[{"page": 1, "rect": rect}])
    if skip:
        assert r.status_code == 422, r.text
        return
    assert r.status_code == 200, r.text
    text = page_text(r.content)
    assert "Krause" not in text and "Gutachter" in text


def test_a_f1_overlapping_selection_counts_once(client):
    """E2E-Befund F1: Begriff in ausgewählter E-Mail-Adresse und derselbe Name
    abgewählt an anderer Stelle — kein falscher 422, Name bleibt lesbar."""
    pdf = kc.pdf_from_lines(["Max Mustermann wohnt hier.", "Kontakt: max.mustermann@example.org"])
    plan = plan_of(client, pdf, ["email"], terms="Mustermann")
    name = min((c for c in plan["candidates"] if c["source"].startswith("begriff:")), key=lambda c: c["pdf_rect"][1])
    keep = [c["id"] for c in plan["candidates"] if c["id"] != name["id"]]
    r = apply_with(client, pdf, plan, selected=keep)
    assert r.status_code == 200, r.text
    text = page_text(r.content)
    assert "Max Mustermann" in text and "example.org" not in text and text.count("Mustermann") == 1


def test_a_f1_area_over_selected_finding_counts_once(client):
    pdf = kc.pdf_from_lines(["Herr Krause kam.", "Gez. Krause"])
    plan = plan_of(client, pdf, terms="Krause")
    first, second = sorted(plan["candidates"], key=lambda c: c["pdf_rect"][1])
    r = apply_with(client, pdf, plan, selected=[first["id"]], areas=[{"page": 1, "rect": first["rects"][0]}])
    assert r.status_code == 200, r.text
    assert page_text(r.content).count("Krause") == 1


# ── Zweite Gegenprüfung (code-audit, 20.11.2026) ─────────────


def _engine():
    from app.services import redaction as R

    return R


def _engine_apply(pdf: bytes, plan, selected=None, areas=(), sanitize=True):
    R = _engine()
    ids = frozenset(c.id for c in plan.candidates) if selected is None else frozenset(selected)
    return R.apply_plan(pdf, R.Selection(plan.sha256, plan.criteria, ids, tuple(areas), sanitize))


def _engine_plan(pdf: bytes, terms=(), patterns=()):
    R = _engine()
    return R.build_plan(pdf, R.Criteria.from_input(list(patterns), list(terms)))


def _raw(pdf: bytes) -> bytes:
    parts = []
    with fitz.open(stream=pdf, filetype="pdf") as d:
        for x in range(1, d.xref_length()):
            try:
                parts.append(d.xref_object(x).encode("latin-1", "replace"))
                if d.xref_is_stream(x):
                    parts.append(d.xref_stream(x) or b"")
            except Exception:
                pass
    return b"\n".join(parts)


@pytest.mark.parametrize("extra", [None, "Anschrift: Krausestr. 5", "Herr Krausen kam"])
@pytest.mark.parametrize("sanitize", [True, False])
def test_a_hn1_alt_text_not_excused_by_longer_word(extra, sanitize):
    """H-N1: „Krausestr.“ darf einen lesbaren Alternativtext „Foto Krause“
    nicht entschuldigen."""

    def build(doc, page):
        page.insert_text((72, 60), "Bearbeiter Krause", fontsize=11)
        if extra:
            page.insert_text((72, 90), extra, fontsize=11)
        st = doc.get_new_xref()
        doc.update_object(st, "<< /Type /StructTreeRoot /K [<< /S /Figure /Alt (Foto Krause) >>] >>")
        doc.xref_set_key(doc.pdf_catalog(), "StructTreeRoot", f"{st} 0 R")
        x = page.get_contents()[0]
        s = doc.xref_stream(x).replace(b"BT", b"/Span <</ActualText (Krause)>> BDC BT", 1).replace(b"ET", b"ET EMC", 1)
        doc.update_stream(x, s)

    pdf = _pdf(build)
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["Krause"]), sanitize=sanitize)
    raw = _raw(out)
    assert b"Foto Krause" not in raw and b"(Krause)" not in raw


def test_a_mn1_deselected_bookmark_kept_despite_term_in_selected_email():
    """M-N1: Begriff steckt in einer ausgewählten E-Mail; das abgewählte
    Lesezeichen mit demselben Namen bleibt unverändert."""

    def build(doc, page):
        page.insert_text((72, 100), "Kontakt max.mustermann@example.org", fontsize=11)
        doc.set_toc([[1, "Akte Mustermann", 1]])

    pdf = _pdf(build)
    plan = _engine_plan(pdf, ["Mustermann"], ["email"])
    keep = [c.id for c in plan.candidates if c.kind == "text"]
    out, _ = _engine_apply(pdf, plan, keep, sanitize=False)
    with fitz.open(stream=out, filetype="pdf") as d:
        assert d.get_toc()[0][1] == "Akte Mustermann"
        assert "example.org" not in d[0].get_text()


@pytest.mark.parametrize(
    "lines, terms, patterns",
    [
        (["Es erschien Max", "Mustermann und sagte aus."], ["Max Mustermann"], []),
        (["IBAN DE89 3704 0044", "0532 0130 00 bitte"], [], ["iban"]),
    ],
)
def test_a_mn2_partial_failure_of_multiline_finding(monkeypatch, lines, terms, patterns):
    """M-N2: Greift die Schwärzung nur in der ersten Zeile einer
    mehrzeiligen Fundstelle, muss die Nachprüfung das melden."""

    def build(doc, page):
        for k, line in enumerate(lines):
            page.insert_text((72, 72 + 14 * k), line, fontsize=11)

    pdf = _pdf(build)
    plan = _engine_plan(pdf, terms, patterns)
    assert len(plan.candidates) == 1 and len(plan.candidates[0].rects) == 2
    _skip_redaction_below(monkeypatch, 70)
    with pytest.raises(_engine().RedactionVerificationError):
        _engine_apply(pdf, plan)


@pytest.mark.parametrize("sep", ["​", "­"])
def test_a_mn3_bookmark_with_invisible_characters(sep):
    def build(doc, page):
        page.insert_text((72, 60), "Text", fontsize=11)
        doc.set_toc([[1, f"Krause und Kra{sep}use", 1]])

    pdf = _pdf(build)
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["Krause"]), sanitize=False)
    with fitz.open(stream=out, filetype="pdf") as d:
        assert d.get_toc()[0][1] == "[geschwärzt]"


def test_a_mn4_embedded_font_names_no_false_alarm():
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if not font.exists():
        pytest.skip("DejaVu-Schrift fehlt")

    def build(doc, page):
        page.insert_text((72, 72), "Frau Vera Schmidt", fontsize=11, fontfile=str(font), fontname="dv")

    pdf = _pdf(build)
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["Vera"]))
    assert "Vera" not in page_text(out)


def test_a_mn6_ocmd_all_off_layer_found_and_removed():
    def build(doc, page):
        page.insert_text((72, 72), "Sichtbar Krause", fontsize=11)
        g = doc.add_ocg("an", on=True)
        md = doc.get_new_xref()
        doc.update_object(md, f"<< /Type /OCMD /OCGs [{g} 0 R] /P /AllOff >>")
        page.insert_font("helv")
        res = page.get_contents()[0]
        kind, val = doc.xref_get_key(page.xref, "Resources")
        rx = int(val.split()[0]) if kind == "xref" else page.xref
        pre = "" if kind == "xref" else "Resources/"
        doc.xref_set_key(rx, pre + "Properties", f"<< /MD1 {md} 0 R >>")
        doc.update_stream(
            res,
            doc.xref_stream(res) + b"\n/OC /MD1 BDC BT /helv 11 Tf 1 0 0 1 72 600 Tm (Krause verborgen) Tj ET EMC",
        )

    pdf = _pdf(build)
    plan = _engine_plan(pdf, ["Krause"])
    assert len(plan.candidates) == 2
    out, _ = _engine_apply(pdf, plan)
    assert b"Krause verborgen" not in _raw(out)
    with fitz.open(stream=out, filetype="pdf") as d:
        assert d.xref_get_key([x for x in range(1, d.xref_length()) if d.xref_get_key(x, "Type")[1] == "/OCMD"][0], "P")[1] == "/AllOff"


@pytest.mark.parametrize(
    "plan_text",
    [
        '{"sha256": "x", "selected": [], "areas": [{"page": Infinity, "rect": [0, 0, 1, 1]}]}',
        '{"sha256": "x", "selected": [], "areas": [{"page": 1e400, "rect": [0, 0, 1, 1]}]}',
        '{"sha256": "x", "selected": [], "areas": [{"page": 1, "rect": [NaN, 0, 1, 1]}]}',
        '{"sha256": "x", "selected": [], "areas": [{"page": 1.5, "rect": [0, 0, 1, 1]}]}',
        "[" * 100000 + "]" * 100000,
    ],
)
def test_a_mn7_malicious_plan_is_400(client, plan_text):
    pdf = kc.pdf_from_lines(["Herr Krause kam."])
    r = client.post(
        "/api/pdf-extras/redact/apply",
        files={"file": ("a.pdf", pdf, "application/pdf"), "plan_file": ("plan.json", plan_text.encode(), "application/json")},
    )
    assert r.status_code == 400, r.text


def test_a_mn5_raw_scanner_matches_flat_alternation():
    """M-N5: Die Vorauswahl über Präfixe findet dasselbe wie eine flache
    Alternative mit Wortgrenzen."""
    import random
    import re

    R = _engine()
    rnd = random.Random(7)
    forms = sorted({"".join(rnd.choice("abc.@") for _ in range(rnd.randint(1, 6))).encode() for _ in range(300)})
    flat = re.compile(
        rb"(?<![A-Za-z0-9/])(" + b"|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True)) + rb")(?![A-Za-z0-9])",
        re.IGNORECASE,
    )
    scanner = R._RawScanner({f: f.decode() for f in forms}, True)
    for _ in range(2000):
        blob = "".join(rnd.choice("abcABC.@ x/") for _ in range(40)).encode()
        hits: set[str] = set()
        scanner.scan(blob.lower(), hits)
        expected = {m.group(1).lower().decode() for m in flat.finditer(blob)}
        assert expected <= hits
        # Mehr Treffer nur durch überlappende Fundorte, die finditer überspringt.
        for h in hits - expected:
            assert re.search(rb"(?<![A-Za-z0-9/])" + re.escape(h.encode()) + rb"(?![A-Za-z0-9])", blob, re.IGNORECASE)


def test_a_mn5_short_term_still_replaced_in_alt_text():
    """Der Begriffsindex darf kurze Begriffe (unter drei Zeichen) nicht verlieren."""

    def build(doc, page):
        page.insert_text((72, 60), "Herr Li kam", fontsize=11)
        st = doc.get_new_xref()
        doc.update_object(st, "<< /Type /StructTreeRoot /K [<< /S /Figure /Alt (Foto Li) >>] >>")
        doc.xref_set_key(doc.pdf_catalog(), "StructTreeRoot", f"{st} 0 R")

    pdf = _pdf(build)
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["Li"]), sanitize=False)
    assert b"Foto Li" not in _raw(out)


# ── Dritte Gegenprüfung (code-audit, 20.11.2026) ─────────────


def _raw_pages(contents: list[bytes], extra=None) -> bytes:
    doc = fitz.open()
    for content in contents:
        page = doc.new_page()
        c = doc.get_new_xref()
        doc.update_object(c, "<<>>")
        doc.update_stream(c, content, new=True)
        doc.xref_set_key(page.xref, "Contents", f"{c} 0 R")
        doc.xref_set_key(
            page.xref,
            "Resources",
            "<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >> >> >>",
        )
    if extra:
        extra(doc)
    data = doc.tobytes()
    doc.close()
    return data


def test_a_n3_1_layer_hidden_by_usage_viewstate():
    """Ebene mit /Usage/View/ViewState /OFF: MuPDF blendet sie aus. Der Text
    muss trotzdem gefunden und geschwärzt werden."""
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if not font.exists():
        pytest.skip("DejaVu-Schrift fehlt")

    def build(doc, page):
        ocg = doc.add_ocg("Notizen", on=True)
        doc.xref_set_key(ocg, "Usage", "<< /View << /ViewState /OFF >> >>")
        page.insert_text((72, 72), "Herr Krause", fontsize=11, fontname="dv", fontfile=str(font))
        page.insert_text((72, 300), "Krause wohnt Hauptstr. 1", fontsize=11, fontname="dv", fontfile=str(font), oc=ocg)

    pdf = _pdf(build)
    plan = _engine_plan(pdf, ["Krause"])
    assert len(plan.candidates) == 2
    out, _ = _engine_apply(pdf, plan, sanitize=False)
    with fitz.open(stream=out, filetype="pdf") as d:
        ocgs = [x for x in range(1, d.xref_length()) if d.xref_get_key(x, "Type")[1] == "/OCG"]
        assert d.xref_get_key(ocgs[0], "Usage/View/ViewState")[1] == "/OFF"  # wiederhergestellt
        for x in ocgs:
            d.xref_set_key(x, "Usage", "null")
        assert "Krause" not in "".join(p.get_text() for p in d)


def test_a_n3_2_word_split_in_content_stream_no_false_422():
    pdf = _raw_pages([
        b"BT /F1 12 Tf 72 700 Td (Herr Krause) Tj ET",
        b"BT /F1 12 Tf 72 700 Td (Krause) Tj (stra\\337e 5) Tj ET",
    ])
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["Krause"]), [c.id for c in _engine_plan(pdf, ["Krause"]).candidates], sanitize=False)
    assert "Krausestraße" in page_text(out).replace("\n", "")


def test_a_n3_3_indirect_alt_text_replaced():
    def extra(doc):
        s = doc.get_new_xref()
        doc.update_object(s, "(Foto: Herr Krause, geb. 03.04.1961)")
        x = doc.get_new_xref()
        doc.update_object(x, f"<< /Type /StructElem /S /Figure /Alt {s} 0 R >>")
        doc.xref_set_key(doc.pdf_catalog(), "StructTreeRoot", f"<< /Type /StructTreeRoot /K [{x} 0 R] >>")

    pdf = _raw_pages([
        b"BT /F1 12 Tf 72 700 Td (Herr Krause) Tj ET",
        b"BT /F1 12 Tf 72 700 Td (Ansprechpartner Krause) Tj ET",
    ], extra)
    plan = _engine_plan(pdf, ["Krause"])
    out, _ = _engine_apply(pdf, plan, [c.id for c in plan.candidates if c.page == 1], sanitize=False)
    assert b"03.04.1961" not in _raw(out)
    assert "Ansprechpartner Krause" in page_text(out)


def test_a_n3_5_short_key_leaves_foreign_alt_text():
    def extra(doc):
        x = doc.get_new_xref()
        doc.update_object(x, "<< /Type /StructElem /S /Figure /Alt (Abbildung: Lageplan) >>")
        doc.xref_set_key(doc.pdf_catalog(), "StructTreeRoot", f"<< /Type /StructTreeRoot /K {x} 0 R >>")

    pdf = _raw_pages([b"BT /F1 12 Tf 72 700 Td (Kennung AB) Tj ET"], extra)
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["AB"]), sanitize=False)
    assert b"Abbildung: Lageplan" in _raw(out)
    assert "AB" not in page_text(out)


def test_a_n3_4_scanner_short_form_does_not_slow_long_forms():
    R = _engine()
    table = {f"+49 6{i:07d}".encode(): f"n{i}" for i in range(5000)}
    table[b"anna"] = "Anna"
    scanner = R._RawScanner(table, True)
    blob = (b"+49 " * 20000) + b" +49 60000042 anna "
    t = time.time()
    hits: set[str] = set()
    scanner.scan(blob.lower(), hits)
    assert hits == {"n42", "Anna"}
    assert time.time() - t < 2


@pytest.mark.parametrize("ocmd", ["<< /Type /OCMD /OCGs [{g} 0 R] /P /AllOff >>", "<< /Type /OCMD /VE [/Not {g} 0 R] >>"])
def test_a_n3_6_direct_ocmd_in_properties(ocmd):
    def build(doc, page):
        page.insert_text((72, 72), "Herr Krause", fontsize=11)
        g = doc.add_ocg("an", on=True)
        page.insert_font("helv")
        kind, val = doc.xref_get_key(page.xref, "Resources")
        rx = int(val.split()[0]) if kind == "xref" else page.xref
        pre = "" if kind == "xref" else "Resources/"
        doc.xref_set_key(rx, pre + "Properties", "<< /MD1 " + ocmd.format(g=g) + " >>")
        res = page.get_contents()[0]
        doc.update_stream(res, doc.xref_stream(res) + b"\n/OC /MD1 BDC BT /helv 11 Tf 1 0 0 1 72 600 Tm (Krause Geheim) Tj ET EMC")

    pdf = _pdf(build)
    plan = _engine_plan(pdf, ["Krause"])
    assert len(plan.candidates) == 2
    out, _ = _engine_apply(pdf, plan)
    assert b"Krause Geheim" not in _raw(out)


def test_a_n3_7_layer_state_restored_exactly():
    def build(doc, page):
        page.insert_text((72, 72), "Herr Krause", fontsize=11)
        g = doc.add_ocg("an", on=True)
        md = doc.get_new_xref()
        doc.update_object(md, f"<< /Type /OCMD /OCGs [{g} 0 R] /P (AllOff) >>")
        kind, val = doc.xref_get_key(page.xref, "Resources")
        rx = int(val.split()[0]) if kind == "xref" else page.xref
        pre = "" if kind == "xref" else "Resources/"
        doc.xref_set_key(rx, pre + "Properties", f"<< /MD1 {md} 0 R >>")
        page.insert_font("helv")
        res = page.get_contents()[0]
        doc.update_stream(res, doc.xref_stream(res) + b"\n/OC /MD1 BDC BT /helv 11 Tf 1 0 0 1 72 600 Tm (Anlage) Tj ET EMC")

    pdf = _pdf(build)
    with fitz.open(stream=pdf, filetype="pdf") as d:
        before = [d.xref_object(x, compressed=True) for x in range(1, d.xref_length()) if "OCMD" in d.xref_object(x)]
        cat_before = d.xref_get_key(d.pdf_catalog(), "OCProperties/D")[1]
    out, _ = _engine_apply(pdf, _engine_plan(pdf, ["Krause"]), sanitize=False)
    with fitz.open(stream=out, filetype="pdf") as d:
        after = [d.xref_object(x, compressed=True) for x in range(1, d.xref_length()) if "OCMD" in d.xref_object(x)]
        import re

        def norm(objs):
            return [re.sub(r"\d+ 0 R", "N 0 R", o) for o in objs]

        assert norm(after) == norm(before) and len(after) == 1
        assert norm([d.xref_get_key(d.pdf_catalog(), "OCProperties/D")[1]]) == norm([cat_before])


# ── KI-Namen in Tabellen (Anwesenheitsliste, 20.11.2026) ───────

_TABLE_ROWS = [
    ["KW 45", "Montag, 02.11.", "Dienstag, 03.11.", "Mittwoch, 04.11."],
    ["Z", "Atreides, Paul", "Atreides, Paul", "Atreides, Paul"],
    ["Z 6", "Rabenstich (VG Z 9)", "Rabenstich, Romina", "Heide, Erika (NM)"],
    ["", "Prof. Dr. Rainer Zufall, Z 6", "Gruber, Toni", "Rabenstich, Romina"],
    ["", "Heide, Erika", "Heide, Erika", "Stahl, Armin (LÜKEX)"],
    ["", "Gruber, Toni", "Reiter", "Reiter"],
    ["Z 7", "Reiter, Jan", "", ""],
]
_TABLE_NAMES = "Atreides Paul Rabenstich Romina Heide Erika Rainer Zufall Gruber Toni Stahl Armin Reiter Jan".split()


def _table_pdf() -> bytes:
    """Zellen zeilenweise wie in einer aus Excel erzeugten PDF."""

    def build(doc, page):
        for r, row in enumerate(_TABLE_ROWS):
            for c, cell in enumerate(row):
                if cell:
                    page.insert_text((30 + c * 140, 80 + r * 16), cell, fontsize=8)

    return _pdf(build)


@ner
def test_ner_table_finds_every_name(client):
    """Anwesenheitsliste: Namen als „Nachname, Vorname“, allein stehende
    Nachnamen und Namen mit Zusätzen werden alle gefunden, Kopfzeile und
    Zusätze bleiben stehen; Namen benachbarter Zellen werden nicht zu einem
    zusammengezogen. Der allein stehende Nachname „Reiter“ wird über
    „Reiter, Jan“ gefunden."""
    plan = plan_of(client, _table_pdf(), ["ki_namen"])
    texts = [c["text"] for c in plan["candidates"]]
    covered = " ".join(texts)
    assert [n for n in _TABLE_NAMES if not re.search(rf"\b{n}\b", covered)] == []
    for kept in ("Montag", "Dienstag", "KW 45", "LÜKEX", "Prof", "Z 6"):
        assert kept not in covered, kept
    assert all(len(t.split()) <= 3 for t in texts), texts


@ner
def test_ner_no_false_positives_in_narrow_paragraph():
    """Kurze Abschnitte prüft die KI einzeln, Zeilen eines Absatzes nicht:
    Sonst meldete sie im schmalen Satzspiegel „Förderantrag“ als Namen."""
    text, names = kc.ner_text()
    parts = {p for n in names for p in n.split()}
    for width in (480, 260, 160):
        found = [f["text"] for f in findings(kc.wrapped_paragraph_pdf(text, width=width), ["ki_namen"])]
        assert [t for t in found if not any(p in t for p in parts)] == [], width


def test_ner_name_found_once_is_searched_everywhere():
    """Ein belegter Name (zwei Bestandteile) wird auf allen Seiten nachgesucht,
    auch wo die KI ihn allein nicht erkennt; die Treffer bilden eine eigene,
    gesammelt abwählbare Gruppe. Nicht nachgesucht wird nach einem Artikel,
    in längeren Wörtern und beim Monatskürzel im Datum („15. Jan.“)."""
    import re

    from app.services import redaction as R

    def fake_ner(texts):
        # erkennt „Jan Reiter“ nur im Satzzusammenhang
        return [[m.span() for m in re.finditer("Jan Reiter", t)] if "sagte" in t else [] for t in texts]

    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Das sagte Jan Reiter gestern.", fontsize=11)
    page = doc.new_page()
    for y, line in enumerate(("Reiter", "Reitergruppe", "Der Reiter kam.", "am 15. Jan. 2026")):
        page.insert_text((72, 72 + 20 * y), line, fontsize=11)
    pdf = doc.tobytes()
    crit = R.Criteria(patterns=("ki_namen",), terms=(), case_sensitive=False, whole_word=True)
    plan = R.build_plan(pdf, crit, fake_ner)
    found = sorted((c.page, c.source, c.text) for c in plan.candidates)
    assert found == [(1, "ki_namen", "Jan Reiter"), (2, R.NER_PROPAGATED_ID, "Reiter")]
    assert R.source_label(R.NER_PROPAGATED_ID) == "Namen (im Dokument nachgesucht)"


def _fake_ner(*persons):
    """KI-Attrappe: meldet die genannten Texte überall als Person."""

    def run(texts):
        return [sorted({m.span() for p in persons for m in re.finditer(re.escape(p), t)}) for t in texts]

    return run


def _plan_texts(pdf, ner_fn):
    from app.services import redaction as R

    plan = R.build_plan(pdf, R.Criteria(("ki_namen",), (), False, True), ner_fn)
    return sorted((c.page, c.source, c.text) for c in plan.candidates)


def _lines_pdf(*pages) -> bytes:
    doc = fitz.open()
    for lines in pages:
        page = doc.new_page()
        for y, line in enumerate(lines):
            page.insert_text((72, 72 + 16 * y), line, fontsize=9)
    return doc.tobytes()


def _cell_ner(*persons):
    """KI-Attrappe: meldet die Texte nur, wenn sie allein stehen (eine Zelle),
    nicht im Seitentext und nicht im Mustersatz."""

    def run(texts):
        return [[(0, len(t))] if t in persons else [] for t in texts]

    return run


def _count(found, source, text):
    return sum(1 for _p, s, t in found if s == source and t == text)


def test_ner_cell_false_positive_is_not_multiplied():
    """Meldet die KI eine Zelle „Summe Netto“ als Person und bestätigt sie im
    Mustersatz nicht, wird „Summe“ nicht im ganzen Dokument geschwärzt –
    auch nicht, wenn der Spaltenkopf auf jeder Seite wiederkehrt."""
    from app.services import redaction as R

    pages = [["Summe Netto"]] * 6 + [["Summe und Belege stimmen."] * 3] * 6
    found = _plan_texts(_lines_pdf(*pages), _cell_ner("Summe Netto"))
    assert _count(found, "ki_namen", "Summe Netto") == 6
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID]


def test_ner_cap_boundary():
    """Grenze bei unbestätigtem Zellbeleg: bis max(10, 4 × direkt) wird
    nachgesucht, darüber nur mit Anrede."""
    from app.services import redaction as R

    def pdf(n, addressed=0):
        return _lines_pdf(["Jan Reiter"], ["Reiter kam."] * n + ["Herr Reiter kam."] * addressed)

    assert _count(_plan_texts(pdf(10), _cell_ner("Jan Reiter")), R.NER_PROPAGATED_ID, "Reiter") == 10
    assert _count(_plan_texts(pdf(11), _cell_ner("Jan Reiter")), R.NER_PROPAGATED_ID, "Reiter") == 0
    assert _count(_plan_texts(pdf(11, 3), _cell_ner("Jan Reiter")), R.NER_PROPAGATED_ID, "Reiter") == 3


def test_ner_frequent_name_from_sentence_or_list_has_no_cap():
    """Ein Name aus dem Satzzusammenhang, der Listenform oder einer im
    Mustersatz bestätigten Zelle wird ohne Grenze nachgesucht: spaCy erkennt
    einen allein stehenden Nachnamen fast nie."""
    from app.services import redaction as R

    prose = [["Berger legte die Belege vor."] * 8 for _ in range(4)]
    cases = [
        (["Projektleiter ist Thomas Berger."], _fake_ner("Thomas Berger")),
        (["Berger, Thomas"], _cell_ner("Thomas Berger")),
        (["Thomas Berger"], _fake_ner("Thomas Berger")),  # Zelle, Mustersatz bestätigt
    ]
    for head, ner_fn in cases:
        found = _plan_texts(_lines_pdf(head, *prose), ner_fn)
        assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 32, head


def test_ner_cross_cell_header_is_capped():
    """Zieht die KI zwei Spaltenköpfe über die Zellgrenze zu einer Person
    zusammen, gilt die Grenze, auch wenn der Mustersatz das Paar bestätigt."""
    from app.services import redaction as R

    def build(doc, page):
        page.insert_text((40, 60), "Telefon", fontsize=8)
        page.insert_text((300, 60), "Begünstigter", fontsize=8)
        for i in range(2):
            q = doc.new_page()
            for y in range(6):
                q.insert_text((72, 72 + 16 * y), "Begünstigter ist die Stadt.", fontsize=9)

    def ner_fn(texts):
        out = []
        for t in texts:
            m = re.search(r"Telefon\s+Begünstigter", t)
            out.append([m.span()] if m else [])
        return out

    found = _plan_texts(_pdf(build), ner_fn)
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID], found


def _no_frame(ner_fn):
    """KI-Attrappe ohne Bestätigung im Mustersatz."""

    def run(texts):
        return [[] if t.startswith("Gestern habe ich") else r for t, r in zip(texts, ner_fn(texts))]

    return run


def test_ner_frame_only_where_cap_matters():
    """Den Mustersatz bekommt die KI nur für Wörter, die sonst an der Grenze
    scheitern (Laufzeit bei dichten Tabellen)."""
    framed = []
    base = _cell_ner("Jan Reiter", "Eva Stahl")

    def ner_fn(texts):
        framed.extend(t for t in texts if t.startswith("Gestern habe ich"))
        return base(texts)

    _plan_texts(_lines_pdf(["Jan Reiter"], ["Eva Stahl"], ["Reiter kam."] * 11 + ["Stahl kam."] * 3), ner_fn)
    assert framed == ["Gestern habe ich Jan Reiter getroffen."]


def test_ner_header_row_is_no_sentence_context():
    """Eine Kopfzeile aus Großwörtern, die MuPDF als eine Zeile liest, ist
    kein Satz: Ein Fehltreffer darin wird nicht ohne Grenze nachgesucht."""
    from app.services import redaction as R

    pdf = _lines_pdf(["Ort Telefon Begünstigter Betrag"], *[["Betrag wurde gezahlt."] * 6] * 2)
    found = _plan_texts(pdf, _no_frame(_fake_ner("Begünstigter Betrag")))
    assert _count(found, "ki_namen", "Begünstigter Betrag") == 1
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID], found


def test_ner_sentence_context_needs_no_frame():
    """Steht ein kleingeschriebenes Wort daneben, gilt der Treffer als Satz
    und wird ohne Grenze und ohne Mustersatz nachgesucht."""
    from app.services import redaction as R

    prose = [["Berger legte die Belege vor."] * 8 for _ in range(4)]
    for head in ("Projektleiter ist Thomas Berger.", "Thomas Berger ist Projektleiter."):
        found = _plan_texts(_lines_pdf([head], *prose), _no_frame(_fake_ner("Thomas Berger")))
        assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 32, head


@pytest.mark.parametrize(
    "header", ["Vorhaben Träger inkl. Anschrift", "Vorhaben Träger einschl. Anschrift", "Vorhaben Träger in EUR", "Vorhaben Träger je Ort"]
)
def test_ner_header_function_words_are_no_sentence(header):
    """Abkürzungen und Präpositionen stehen auch in Kopfzeilen („inkl. USt“,
    „in EUR“); sie machen aus der Kopfzeile keinen Satz."""
    from app.services import redaction as R

    pdf = _lines_pdf([header], *[["Träger wurde benannt."] * 6] * 2)
    found = _plan_texts(pdf, _no_frame(_fake_ner("Vorhaben Träger")))
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID], found


@pytest.mark.parametrize("mentions, expected", [(30, 30), (50, 50), (51, 0)])
def test_ner_label_before_name_is_confirmed_in_part(mentions, expected):
    """Meldet die KI das Etikett mit („Auftragnehmer Thomas Berger“) und
    bestätigt der Mustersatz nur den Namen, wird der Name bis zur höheren
    Untergrenze nachgesucht, das Etikett nicht. Ohne Grenze nicht, weil der
    Mustersatz so auch Spaltenköpfe bestätigt."""
    from app.services import redaction as R

    def ner_fn(texts):
        out = []
        for t in texts:
            if t.startswith("Gestern habe ich"):
                m = re.search("Thomas Berger", t)
                out.append([m.span()] if m else [])
            else:
                out.append([(0, len(t))] if t == "Auftragnehmer Thomas Berger" else [])
        return out

    prose = [["Berger legte die Belege vor."] * min(40, mentions - i) for i in range(0, mentions, 40)]
    pdf = _lines_pdf(["Auftragnehmer Thomas Berger"], *prose, ["Auftragnehmer kam."] * 12)
    found = _plan_texts(pdf, ner_fn)
    assert _count(found, R.NER_PROPAGATED_ID, "Berger") == expected
    assert _count(found, R.NER_PROPAGATED_ID, "Auftragnehmer") == 0


def test_ner_whole_cell_confirmed_in_several_parts():
    """Bestätigt der Mustersatz alle Namen einer Zelle in mehreren Teilen,
    gilt die Zelle als ganz bestätigt (ohne Grenze)."""
    from app.services import redaction as R

    def ner_fn(texts):
        out = []
        for t in texts:
            if t.startswith("Gestern habe ich"):
                out.append([m.span() for m in re.finditer("Thomas Berger|Anna Schmidt", t)])
            else:
                out.append([(0, len(t))] if t == "Thomas Berger Anna Schmidt" else [])
        return out

    pdf = _lines_pdf(["Thomas Berger Anna Schmidt"], ["Schmidt legte die Belege vor."] * 30)
    assert _count(_plan_texts(pdf, ner_fn), R.NER_PROPAGATED_ID, "Schmidt") == 30


def test_ner_frame_span_is_clamped_to_the_cell():
    """Reicht der Treffer im Mustersatz in den Vorspann („ich Thomas
    Berger“), zählt nur der Teil in der Zelle."""
    from app.services import redaction as R

    def ner_fn(texts):
        out = []
        for t in texts:
            if t.startswith("Gestern habe ich"):
                out.append([(t.index("ich"), t.index(" getroffen") + 4)])
            else:
                out.append([(0, len(t))] if t == "Thomas Berger" else [])
        return out

    pdf = _lines_pdf(["Thomas Berger"], ["Berger legte die Belege vor."] * 30)
    assert _count(_plan_texts(pdf, ner_fn), R.NER_PROPAGATED_ID, "Berger") == 30


@pytest.mark.parametrize(
    "head, line",
    [
        ("Projektleiterin ist Petra Preis.", "Frau Preis legte die Belege vor."),
        ("Projektleiterin ist Petra Preis.", "Preis legte die Belege vor."),
        ("Projektleiter ist Wolfgang Menge.", "Herr Menge legte die Belege vor."),
        ("Projektleiterin ist Anna Schmidt-Mai.", "Frau Schmidt-Mai legte die Belege vor."),
        ("Projektleiterin ist Anna Schmidt-Mai.", "Schmidt-Mai legte die Belege vor."),
    ],
)
def test_ner_surnames_like_table_or_month_words(head, line):
    """Nachnamen wie „Preis“, „Menge“ oder „Schmidt-Mai“ aus einem Satz
    werden wie jeder andere Name nachgesucht."""
    from app.services import redaction as R

    person = head.split(" ist ")[1].rstrip(".")
    found = _plan_texts(_lines_pdf([head], [line] * 20), _no_frame(_fake_ner(person)))
    word = line.split()[1] if line.startswith(("Frau", "Herr")) else line.split()[0]
    assert _count(found, R.NER_PROPAGATED_ID, word) == 20


@pytest.mark.parametrize("person", ["Dr. Menge", "Frau Menge", "Prof. Dr. Rabatt"])
def test_ner_table_word_surname_after_title(person):
    """„Die Prüfung führte Frau Dr. Menge durch.“: Meldet die KI nur Titel
    und Nachnamen, ist der Spaltenkopf trotzdem ein Nachname."""
    from app.services import redaction as R

    word = person.split()[-1]
    pdf = _lines_pdf([f"Die Prüfung führte {person} durch."], [f"Rückfrage bei {word} ist erledigt."] * 30)
    found = _plan_texts(pdf, _no_frame(_fake_ner(person)))
    assert _count(found, R.NER_PROPAGATED_ID, word) == 30


def test_ner_list_form_with_table_word_surname():
    """„Preis, Petra“ in der Listenform: Der ganze Eintrag ist Fundstelle."""
    found = _plan_texts(_lines_pdf(["Preis, Petra"]), _fake_ner("Petra Preis"))
    assert _count(found, "ki_namen", "Preis, Petra") == 1


def test_ner_confirmed_cell_does_not_free_table_words():
    """Bestätigt der Mustersatz eine Zelle mit Spaltenkopf ganz („Menge
    Thomas Berger“), wird der Name ohne Grenze nachgesucht, der Spaltenkopf
    nicht."""
    from app.services import redaction as R

    pdf = _lines_pdf(["Menge Thomas Berger"], ["Berger kam."] * 12 + ["Menge kam."] * 12)
    found = _plan_texts(pdf, _fake_ner("Menge Thomas Berger"))
    assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 12
    assert _count(found, R.NER_PROPAGATED_ID, "Menge") == 0


def test_ner_table_word_from_cell_kept_with_salutation():
    """Ein Spaltenkopf-Wort aus einem Zellbeleg wird nur mit Anrede nachgesucht."""
    from app.services import redaction as R

    pdf = _lines_pdf(["Wolfgang Menge"], ["Herr Menge kam."] * 3 + ["Menge kam."] * 3)
    assert _count(_plan_texts(pdf, _cell_ner("Wolfgang Menge")), R.NER_PROPAGATED_ID, "Menge") == 3


@pytest.mark.parametrize("head", ["Lukas Fischer unterschreibt.", "Antrag von Lukas Fischer", "Rechnung an Lukas Fischer"])
def test_ner_short_sentences_are_context(head):
    """Ein Verb am Satzende und Präpositionen wie „von“, „an“ machen eine
    Zeile zum Satz."""
    from app.services import redaction as R

    found = _plan_texts(_lines_pdf([head], ["Fischer legte die Belege vor."] * 30), _no_frame(_fake_ner("Lukas Fischer")))
    assert _count(found, R.NER_PROPAGATED_ID, "Fischer") == 30


def test_ner_sentence_context_only_from_neighbouring_lines():
    """Ein kleingeschriebenes Wort in der Zeile davor oder danach zählt
    (umbrochener Satz), eines drei Zeilen tiefer im selben Block nicht."""
    from app.services import redaction as R

    prose = [["Berger legte die Belege vor."] * 30]
    wrapped = _lines_pdf(["Projektleiter ist", "Thomas Berger."], *prose)
    found = _plan_texts(wrapped, _no_frame(_fake_ner("Thomas Berger")))
    assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 30
    after = _lines_pdf(["Thomas Berger", "hat die Belege geprüft."], *prose)
    found = _plan_texts(after, _no_frame(_fake_ner("Thomas Berger")))
    assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 30
    for form in (
        ["Auftragnehmer Thomas Berger", "Kundennummer", "Belegart", "Die Belege liegen vor."],
        ["Auftragnehmer Thomas Berger", "Kundennummer", "die Belege liegen vor."],
        ["die Belege liegen vor.", "Kundennummer", "Auftragnehmer Thomas Berger"],
    ):
        found = _plan_texts(_lines_pdf(form, *prose), _no_frame(_fake_ner("Thomas Berger")))
        assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 0, form


def test_ner_sentence_context_across_wide_word_gaps():
    """Zerlegt MuPDF eine Zeile wegen großer Wortabstände (Blocksatz), zählt
    sie trotzdem als eine Zeile."""
    from app.services import redaction as R

    def build(doc, page):
        x = 72
        for w in "Thomas Berger Referat Recht prüfte die Unterlagen".split():
            page.insert_text((x, 72), w, fontsize=9)
            x += fitz.get_text_length(w, fontsize=9) + 14
        doc.new_page().insert_textbox(fitz.Rect(50, 50, 545, 800), "Berger legte die Belege vor. " * 30, fontsize=9)

    pt = R._page_text(fitz.open(stream=_pdf(build), filetype="pdf")[0])
    assert len(set(n for n in pt.lines if n >= 0)) > 1  # mehrere Fragmente
    found = _plan_texts(_pdf(build), _no_frame(_fake_ner("Thomas Berger")))
    assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 30


@pytest.mark.parametrize("head", ["Summe Netto nach Skonto", "Rabatt Skonto bei Zahlung", "Netto, Brutto"])
def test_ner_header_of_table_words_is_no_name(head):
    """Besteht ein Satz- oder Listenbeleg nur aus Spaltenköpfen, gilt er als
    Zellbeleg: kein Nachsuche-Treffer ohne Anrede."""
    from app.services import redaction as R

    words = head.replace(",", "").split()
    pdf = _lines_pdf([head], *[[f"{w} wurde geprüft." for w in words] * 10] * 3)
    found = _plan_texts(pdf, _fake_ner(" ".join(words[:2]), " ".join(reversed(words[:2]))))
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID], found


def test_ner_table_word_as_label_is_partial_confirmation():
    """„Summe Thomas Berger“: Bestätigt der Mustersatz nur „Thomas Berger“,
    gilt die Untergrenze 50 wie bei jedem Etikett (Entscheidung 23.11.2026)."""
    from app.services import redaction as R

    def ner_fn(texts):
        out = []
        for t in texts:
            if t.startswith("Gestern habe ich"):
                m = re.search("Thomas Berger", t)
                out.append([m.span()] if m else [])
            else:
                out.append([(0, len(t))] if t == "Summe Thomas Berger" else [])
        return out

    for n, expected in ((40, 40), (60, 0)):
        prose = [["Berger legte die Belege vor."] * min(40, n - i) for i in range(0, n, 40)]
        found = _plan_texts(_lines_pdf(["Summe Thomas Berger"], *prose), ner_fn)
        assert _count(found, R.NER_PROPAGATED_ID, "Berger") == expected, n


def test_ner_table_header_words_are_never_propagated():
    """Bestätigt der Mustersatz einen Spaltenkopf („Pos Menge“), wird er
    trotzdem nicht nachgesucht."""
    from app.services import redaction as R

    pdf = _lines_pdf(["Pos Menge"], ["Menge und Preis stimmen."] * 30)
    found = _plan_texts(pdf, _fake_ner("Pos Menge"))
    assert _count(found, "ki_namen", "Pos Menge") == 1
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID], found


def test_ner_partial_frame_hit_is_no_confirmation():
    """Bestätigt der Mustersatz nur einen Teil des Zellbelegs, gilt die Grenze."""
    from app.services import redaction as R

    def ner_fn(texts):
        return [
            [(m.start(), m.end())] if (m := re.search("Thomas", t)) and t.startswith("Gestern") else
            ([(0, len(t))] if t == "Thomas Berger" else [])
            for t in texts
        ]

    found = _plan_texts(_lines_pdf(["Thomas Berger"], ["Berger kam."] * 11, ["Thomas kam."] * 11), ner_fn)
    assert _count(found, R.NER_PROPAGATED_ID, "Berger") == 0
    assert _count(found, R.NER_PROPAGATED_ID, "Thomas") == 0


@pytest.mark.parametrize(
    "title", ["Herr", "Frau", "Hr.", "Fr.", "Dr.", "Prof.", "Dr. med.", "Dr.-Ing.", "Dipl.-Ing.", "Prof. Dr.-Ing. Dr. h. c.", "Dr. rer. nat. habil.", "Dipl.-Ing. (FH)", "Dipl.-Ök."]
)
def test_ner_salutation_kept_above_cap(title):
    from app.services import redaction as R

    pdf = _lines_pdf(["Jan Reiter"], ["Reiter kam."] * 11 + [f"Laut {title} Reiter fehlt nichts."])
    assert _count(_plan_texts(pdf, _cell_ner("Jan Reiter")), R.NER_PROPAGATED_ID, "Reiter") == 1


def test_ner_cap_grows_with_distinct_direct_hits():
    """Drei verschiedene direkte Belege heben die Grenze auf 4 × 3 = 12."""
    from app.services import redaction as R

    heads = [["Jan Reiter"], ["Eva Reiter"], ["Max Reiter"]]
    ner_fn = _cell_ner("Jan Reiter", "Eva Reiter", "Max Reiter")
    assert _count(_plan_texts(_lines_pdf(*heads, ["Reiter kam."] * 12), ner_fn), R.NER_PROPAGATED_ID, "Reiter") == 12
    assert _count(_plan_texts(_lines_pdf(*heads, ["Reiter kam."] * 13), ner_fn), R.NER_PROPAGATED_ID, "Reiter") == 0


def _columns_pdf(mentions: int) -> bytes:
    """Teilnehmerliste mit getrennten Spalten Vorname | Nachname, danach
    ein Protokoll, das den Nachnamen ohne Anrede nennt."""

    def build(doc, page):
        page.insert_text((40, 60), "Klaus", fontsize=8)
        page.insert_text((300, 60), "Wagner", fontsize=8)
        q = doc.new_page()
        q.insert_textbox(fitz.Rect(50, 50, 545, 800), "Wagner legte die Belege vor. " * mentions, fontsize=9)

    return _pdf(build)


def _columns_ner(confirm: bool):
    def run(texts):
        out = []
        for t in texts:
            m = re.search(r"Klaus\s+Wagner", t)
            framed = t.startswith("Gestern habe ich")
            out.append([m.span()] if m and (confirm or not framed) else [])
        return out

    return run


def test_ner_column_split_name_confirmed_has_higher_floor():
    """Ein Name aus zwei Spalten, den der Mustersatz bestätigt, wird bis 50
    Mal nachgesucht; ohne Bestätigung gilt die Grenze von 10; darüber bleibt
    es bei der Grenze, weil der Mustersatz auch Spaltenköpfe bestätigt."""
    from app.services import redaction as R

    def hits(n, confirm):
        return _count(_plan_texts(_columns_pdf(n), _columns_ner(confirm)), R.NER_PROPAGATED_ID, "Wagner")

    assert hits(30, True) == 30
    assert hits(50, True) == 50
    assert hits(51, True) == 0
    assert hits(30, False) == 0
    assert hits(10, False) == 10


def test_ner_column_split_confirmation_per_word():
    """Über Zellgrenzen bestätigt, gilt die Untergrenze je Wort: „Klaus“ mit
    20 Nennungen wird nachgesucht, „Wagner“ mit 200 nicht."""
    from app.services import redaction as R

    def build(doc, page):
        page.insert_text((40, 60), "Klaus", fontsize=8)
        page.insert_text((300, 60), "Wagner", fontsize=8)
        for text in ["Klaus legte die Belege vor. " * 20] + ["Wagner legte die Belege vor. " * 50] * 4:
            doc.new_page().insert_textbox(fitz.Rect(50, 50, 545, 800), text, fontsize=9)

    found = _plan_texts(_pdf(build), _columns_ner(True))
    assert _count(found, R.NER_PROPAGATED_ID, "Klaus") == 20
    assert _count(found, R.NER_PROPAGATED_ID, "Wagner") == 0


def test_ner_contact_words_are_no_name_parts():
    """„Telefon“ und „Fax“ gelten nie als Namensteil, auch nicht in der Listenform."""
    from app.services import redaction as R

    pdf = _lines_pdf(["Telefon, Telefax"], ["Telefon und Telefax sind besetzt."] * 4)
    found = _plan_texts(pdf, _fake_ner("Telefon Telefax", "Telefax Telefon"))
    assert not [t for t in found if t[1] == R.NER_PROPAGATED_ID], found
    assert _count(found, "ki_namen", "Telefon, Telefax") == 0
    # Zusammengesetzt: Der Mustersatz bekommt nur den Namen.
    framed = []
    base = _cell_ner("Telefon-Nr Thomas Berger", "Telefon/Fax Thomas Berger", "Telefon: Thomas Berger")

    def ner_fn(texts):
        framed.extend(t for t in texts if t.startswith("Gestern"))
        return base(texts)

    found = _plan_texts(
        _lines_pdf(
            ["Telefon-Nr Thomas Berger"],
            ["Telefon/Fax Thomas Berger"],
            ["Telefon: Thomas Berger"],
            ["Berger kam."] * 13,
            ["Telefon-Nr fehlt."] * 3,
        ),
        ner_fn,
    )
    assert framed == ["Gestern habe ich Thomas Berger getroffen."]
    assert _count(found, R.NER_PROPAGATED_ID, "Telefon-Nr") == 0


def test_ner_failure_is_http_502(client, monkeypatch):
    """Wirft die KI-Funktion, ist das ein Fehler auf der Serverseite (502)."""
    from app.services import pdf_extras_service as svc

    def broken(texts):
        raise RuntimeError("Modell nicht geladen")

    monkeypatch.setattr(svc.PdfExtrasService, "ner_function", lambda self: broken, raising=False)
    r = client.post(
        "/api/pdf-extras/redact/plan",
        data={"patterns": json.dumps(["ki_namen"]), "terms": ""},
        files={"file": ("d.pdf", _lines_pdf(["Antrag der Stadt Ulm"]), "application/pdf")},
    )
    assert r.status_code == 502, r.text
    assert "KI-Namenserkennung" in r.json()["detail"]


def test_ner_failure_on_apply_is_http_502(client, monkeypatch):
    """Auch beim Anwenden, das die Suche wiederholt, ergibt ein KI-Fehler 502."""
    from app.services import pdf_extras_service as svc

    pdf = _lines_pdf(["Antrag der Stadt Ulm"])
    monkeypatch.setattr(svc.PdfExtrasService, "ner_function", lambda self: _fake_ner("Stadt Ulm"), raising=False)
    plan = plan_of(client, pdf, ["ki_namen"])
    monkeypatch.setattr(svc.PdfExtrasService, "ner_function", lambda self: _raise, raising=False)
    r = apply_with(client, pdf, plan)
    assert r.status_code == 502, r.text
    assert "KI-Namenserkennung" in r.json()["detail"]


def test_ner_double_names_are_propagated():
    from app.services import redaction as R

    pdf = _lines_pdf(["Anna Meyer-Lüdenscheidt", "Hans-Peter Schulze"], ["Meyer-Lüdenscheidt", "Hans-Peter"])
    found = [t for t in _plan_texts(pdf, _fake_ner("Anna Meyer-Lüdenscheidt", "Hans-Peter Schulze")) if t[0] == 2]
    assert sorted(t for _p, _s, t in found) == ["Hans-Peter", "Meyer-Lüdenscheidt"]
    assert {s for _p, s, _t in found} == {R.NER_PROPAGATED_ID}


def _raise(texts):
    raise RuntimeError("Modell nicht geladen")


def _raise_value(texts):
    raise ValueError("Text zu lang")


def _raise_lazy(texts):
    yield []
    raise RuntimeError("Modell nicht geladen")


def _raise_inner(texts):
    def spans():
        yield (0, 1)
        raise RuntimeError("Modell nicht geladen")

    return [spans() for _ in texts]


@pytest.mark.parametrize(
    "bad, error",
    [
        (lambda texts: [[(0, -1)] for _ in texts], None),  # leerer Span: verworfen
        (lambda texts: [[] for _ in texts[1:]], "ungültiges Ergebnis"),
        (lambda texts: [None for _ in texts], "ungültiges Ergebnis"),
        (lambda texts: None, "ungültiges Ergebnis"),
        (_raise, "fehlgeschlagen"),
        (_raise_value, "fehlgeschlagen"),
        (_raise_lazy, "fehlgeschlagen"),
        (_raise_inner, "fehlgeschlagen"),
        (lambda texts: 5, "ungültiges Ergebnis"),
    ],
)
def test_ner_malformed_result(bad, error):
    """Eine fehlerhafte KI-Funktion belegt nicht die ganze Seite. Ein Ergebnis
    in falscher Form oder ein Absturz bricht ab; still leere Treffer gibt es
    nicht, sonst blieben alle Namen lesbar."""
    from app.services import redaction as R

    pdf = _lines_pdf(["Antrag der Stadt Ulm", "Kosten und Belege"], ["Kosten", "Belege"])
    if error is None:
        assert _plan_texts(pdf, bad) == []
    else:
        with pytest.raises(R.RedactionNerError, match=error):
            _plan_texts(pdf, bad)


def test_ner_keeps_initials_and_foreign_letters():
    """Was die KI meldet, bleibt Fundstelle, auch mit Initiale oder
    Buchstaben außerhalb des deutschen Alphabets; zwei solche Bestandteile
    belegen den Namen für die Nachsuche."""
    pdf = _lines_pdf(["i. A. Stahl", "Ömer Çelik", "Atreides"], ["Stahl", "Çelik"])
    found = _plan_texts(pdf, _fake_ner("A. Stahl", "Ömer Çelik", "Atreides"))
    assert [t for _p, _s, t in found] == ["A. Stahl", "Atreides", "Ömer Çelik", "Stahl", "Çelik"]


def test_ner_propagation_exceptions():
    """Nicht nachgesucht wird nach einem Artikel und beim Monatskürzel im
    Datum; nachgesucht wird bei Namenszusätzen und „Jan.“ am Satzende."""
    pdf = _lines_pdf(
        ["Jan Heide"],
        ["Der Heide blühte.", "am 15. Jan. 2026", "Jan. 2027", "Protokoll: Jan.", "Herr von der Heide"],
    )
    found = [t for t in _plan_texts(pdf, _fake_ner("Jan Heide")) if t[0] == 2]
    assert [t for _p, _s, t in found] == ["Heide", "Jan"], found


def test_ner_spans_beyond_segment_are_clamped():
    """Eine fehlerhafte KI-Funktion mit zu langen oder negativen Spans darf
    nicht in Nachbarzellen überlaufen und nicht abstürzen."""
    from app.services import redaction as R

    def bad_ner(texts):
        return [[(-3, len(t) + 50)] if t == "Reiter" else [] for t in texts]

    def build(doc, page):
        page.insert_text((40, 80), "Reiter", fontsize=9)
        page.insert_text((300, 80), "Kostenstelle", fontsize=9)

    plan = R.build_plan(_pdf(build), R.Criteria(("ki_namen",), (), False, True), bad_ner)
    assert [c.text for c in plan.candidates] == ["Reiter"]


def test_ner_span_split_at_cell_borders():
    from app.services import redaction as R

    text = "Jan\x00Reiter\x00Stahl, Armin"
    parts = [text[a:b] for a, b in R._hard_parts(text, 0, len(text))]
    assert parts == ["Jan", "Reiter", "Stahl, Armin"]


def test_ner_keeps_cropbox_for_page_geometry():
    """Die KI-Erkennung legt die CropBox nur vorübergehend auf die MediaBox;
    Seitengröße und Koordinaten des Plans bleiben dieselben wie ohne KI."""
    from app.services import redaction as R

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((100, 200), "Das sagte Reiter gestern.", fontsize=11)
    page.set_cropbox(fitz.Rect(50, 100, 545, 742))
    pdf = doc.tobytes()

    def fake_ner(texts):
        return [[(m.start(), m.end()) for m in __import__("re").finditer("Reiter", t)] for t in texts]

    with_ner = R.build_plan(pdf, R.Criteria(patterns=("ki_namen",), terms=(), case_sensitive=False, whole_word=True), fake_ner)
    plain = R.build_plan(pdf, R.Criteria(patterns=(), terms=("Reiter",), case_sensitive=False, whole_word=True))
    assert (with_ner.pages[0].width, with_ner.pages[0].height) == (plain.pages[0].width, plain.pages[0].height) == (495, 642)
    assert [(c.rects, c.view_rects) for c in with_ner.candidates] == [(c.rects, c.view_rects) for c in plain.candidates]


@pytest.mark.parametrize("box", [(-20, -20, 700, 900), (300, -50, 700, 400)])
@pytest.mark.parametrize("patterns", [(), ("ki_namen",)])
def test_cropbox_beyond_mediabox_plan_and_apply(box, patterns):
    """Eine CropBox darf über die MediaBox hinausragen. Vorschau und
    Anwendung laufen dann durch, und die CropBox bleibt unverändert."""
    from app.services import redaction as R

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((320, 100), "Das sagte Jan Reiter gestern.", fontsize=11)
    doc.xref_set_key(page.xref, "CropBox", "[%d %d %d %d]" % box)
    pdf = doc.tobytes()

    def fake_ner(texts):
        return [[m.span() for m in re.finditer("Jan Reiter", t)] for t in texts]

    crit = R.Criteria(patterns, () if patterns else ("Jan Reiter",), False, True)
    plan = R.build_plan(pdf, crit, fake_ner)
    assert [c.text for c in plan.candidates] == ["Jan Reiter"]
    sel = R.Selection(plan.sha256, crit, frozenset(c.id for c in plan.candidates), (), True)
    out, _ = R.apply_plan(pdf, sel, fake_ner)
    with fitz.open(stream=out) as res:
        assert res.xref_get_key(res[0].xref, "CropBox") == ("array", "[%d %d %d %d]" % box)
        assert "Reiter" not in res[0].get_text(clip=fitz.INFINITE_RECT())


def test_short_segments_edges():
    from app.services import redaction as R

    assert R._short_segments("") == []
    assert R._short_segments("\x00") == []
    text = "Prof. Dr. Rainer Zufall\x00 \x00Heide, Erika\x00"
    assert [text[a:b] for a, b in R._short_segments(text)] == ["Rainer Zufall", "Heide, Erika"]
    assert R._short_segments("eins zwei drei vier fünf sechs sieben") == []
    assert R._hard_parts("Jan", -5, 99) == [(0, 3)]


@ner
def test_ner_table_apply_roundtrip(client):
    """Vorschau → alles auswählen → Anwenden mit echter KI auf der Tabelle:
    gleiche Kandidaten, Nachprüfung ohne Befund, kein Name mehr lesbar."""
    from app.services import redaction as R

    pdf = _table_pdf()
    ner_fn = get_pdf_extras().ner_function()
    crit = R.Criteria(("ki_namen",), (), False, True)
    plan = R.build_plan(pdf, crit, ner_fn)
    sel = R.Selection(plan.sha256, crit, frozenset(c.id for c in plan.candidates), (), True)
    out, _ = R.apply_plan(pdf, sel, ner_fn)
    text = page_text(out)
    assert [n for n in _TABLE_NAMES if re.search(rf"\b{n}\b", text)] == []
    for kept in ("Montag", "KW 45", "LÜKEX", "Prof. Dr."):
        assert kept in text
