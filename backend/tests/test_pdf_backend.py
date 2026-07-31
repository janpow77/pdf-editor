"""Tests der Kapselung: ein Importpunkt, ein Register, keine Umgehung.

Der Wert der Kapselung liegt darin, dass sie eingehalten wird. Diese Tests
schlagen fehl, sobald ein Service wieder direkt `import fitz` schreibt oder
eine Komponente ohne Lizenzangabe ins Register wandert.
"""

import pathlib
import re

import pytest
from fastapi.testclient import TestClient

from app import pdf_backend
from app.main import app
from app.pdf_backend import DEPENDENCIES, dependency_report, requires_source_disclosure

from tests.test_smoke import make_pdf

APP_DIR = pathlib.Path(pdf_backend.__file__).parent


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _python_files() -> list[pathlib.Path]:
    return [
        p
        for p in APP_DIR.rglob("*.py")
        if p.name != "pdf_backend.py" and "__pycache__" not in p.parts
    ]


# ── Ein Importpunkt ───────────────────────────────────────────


@pytest.mark.parametrize("library", ["fitz", "pikepdf", "pymupdf"])
def test_no_direct_library_import_outside_backend(library: str):
    """Fremdbibliotheken werden nur in app/pdf_backend.py importiert.

    Fängt auch lokale Importe innerhalb von Funktionen (`import fitz as _f`),
    die sich sonst still einschleichen.
    """
    pattern = re.compile(rf"^\s*(import {library}\b|from {library}\b)", re.M)
    offenders = [
        str(p.relative_to(APP_DIR))
        for p in _python_files()
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        f"{library} wird direkt importiert in: {offenders}. "
        "Bitte über app/pdf_backend.py beziehen."
    )


def test_no_duplicate_availability_flags():
    """Verfügbarkeits-Flags werden nicht mehr je Service neu ermittelt."""
    pattern = re.compile(r"^\s*(PYMUPDF|PIKEPDF|PILLOW|DOCX|OPENPYXL)_AVAILABLE\s*=", re.M)
    offenders = [
        str(p.relative_to(APP_DIR))
        for p in _python_files()
        if pattern.search(p.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"Eigene Verfügbarkeitserkennung in: {offenders}"


def test_open_pdf_reads_from_memory():
    doc = pdf_backend.open_pdf(make_pdf(2, "Kapselungstest"))
    try:
        assert doc.page_count >= 1
    finally:
        doc.close()


# ── Register ──────────────────────────────────────────────────


def test_every_dependency_has_license_and_purpose():
    for d in DEPENDENCIES:
        assert d.name, d.key
        assert d.license, f"{d.key} ohne Lizenzangabe"
        assert d.purpose, f"{d.key} ohne Zweckangabe"
        assert d.url.startswith("https://"), f"{d.key} ohne Quellenangabe"
        assert d.kind in {"bibliothek", "programm", "rahmenwerk"}, d.kind


def test_dependency_keys_unique():
    keys = [d.key for d in DEPENDENCIES]
    assert len(keys) == len(set(keys))


def test_core_libraries_are_registered():
    """Was der Code lädt, muss im Register stehen — sonst fehlt es auf der
    Lizenzseite und die AGPL-Pflichtangabe wäre unvollständig."""
    keys = {d.key for d in DEPENDENCIES}
    assert {"pymupdf", "pikepdf", "pyhanko", "ghostscript", "libreoffice"} <= keys


def test_agpl_components_marked_as_network_copyleft():
    """PyMuPDF und Ghostscript stehen unter AGPL — das muss am Eintrag hängen,
    weil davon der Quelltext-Hinweis der Anwendung abhängt."""
    by_key = {d.key: d for d in DEPENDENCIES}
    for key in ("pymupdf", "ghostscript"):
        assert "AGPL" in by_key[key].license
        assert by_key[key].copyleft_network is True


def test_source_disclosure_follows_actual_usage():
    """Der Hinweis erscheint genau dann, wenn eine AGPL-Komponente wirklich
    verfügbar ist — nicht als fest verdrahteter Text."""
    expected = any(d.copyleft_network and d.available for d in DEPENDENCIES)
    assert requires_source_disclosure() is expected


def test_report_is_json_serialisable():
    import json

    json.dumps(dependency_report())


# ── Endpunkt ──────────────────────────────────────────────────


def test_licenses_endpoint(client):
    r = client.get("/api/licenses")
    assert r.status_code == 200
    body = r.json()
    assert len(body["components"]) == len(DEPENDENCIES)
    assert "source_disclosure_required" in body
    pymupdf = next(c for c in body["components"] if c["key"] == "pymupdf")
    assert "AGPL" in pymupdf["license"]
