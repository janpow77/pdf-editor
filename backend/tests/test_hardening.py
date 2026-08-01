"""Tests der Härtungsmaßnahmen.

Sicherheitsmaßnahmen ohne Test sind Absichtserklärungen: Sie fallen bei der
nächsten Umstellung lautlos weg. Jede Maßnahme aus `app/hardening.py` und den
zugehörigen Grenzen hat deshalb hier einen Fall.
"""

import io

import fitz
import pytest
from fastapi.testclient import TestClient

from app.hardening import CSP
from app.main import app
from app.pdf_backend import MAX_PAGES, open_pdf


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ── Sicherheitskopfzeilen ─────────────────────────────────────

REQUIRED_HEADERS = {
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
}


@pytest.mark.parametrize("path", ["/api/health", "/api/licenses", "/api/pdf-tools/status"])
def test_security_headers_on_every_response(client, path):
    r = client.get(path)
    missing = REQUIRED_HEADERS - {k.lower() for k in r.headers}
    assert not missing, f"{path} ohne Kopfzeilen: {sorted(missing)}"


def test_security_headers_also_on_errors(client):
    """Fehlerantworten sind der häufigste Weg, auf dem Kopfzeilen verloren
    gehen — dort sind sie genauso nötig."""
    r = client.get("/api/gibt-es-nicht")
    assert r.status_code == 404
    assert "content-security-policy" in {k.lower() for k in r.headers}


def test_csp_blocks_the_dangerous_directives():
    """Die CSP muss die Kernpunkte wirklich abdecken — nicht nur vorhanden sein."""
    assert "object-src 'none'" in CSP
    assert "frame-ancestors 'none'" in CSP
    assert "base-uri 'self'" in CSP
    assert "form-action 'self'" in CSP
    # Skripte dürfen weder inline noch per eval laufen: sonst wäre die
    # Richtlinie gegen Cross-Site-Scripting wirkungslos.
    script_src = next(p for p in CSP.split("; ") if p.startswith("script-src"))
    assert "'unsafe-inline'" not in script_src
    assert "'unsafe-eval'" not in script_src


def test_no_sniffing_on_downloads(client):
    """Ein hochgeladenes Dokument darf nie als HTML interpretiert werden."""
    doc = fitz.open()
    doc.new_page().insert_text((72, 100), "Test")
    r = client.post(
        "/api/pdf-extras/to-text",
        files={"file": ("t.pdf", io.BytesIO(doc.tobytes()), "application/pdf")},
    )
    assert r.status_code == 200
    assert r.headers.get("x-content-type-options") == "nosniff"


# ── Größenschranke vor dem Einlesen ───────────────────────────


def test_oversized_request_rejected_before_reading(client):
    """Die Schranke greift anhand von Content-Length, nicht erst nach dem
    vollständigen Einlesen des Körpers."""
    r = client.post(
        "/api/pdf-tools/compress",
        content=b"x",  # Körper winzig …
        headers={"Content-Length": str(2 * 1024 * 1024 * 1024), "Content-Type": "application/octet-stream"},
    )
    assert r.status_code == 413
    assert "MB" in r.json()["detail"]


def test_normal_request_passes_the_limit(client):
    r = client.get("/api/health")
    assert r.status_code == 200


# ── Seitenzahl-Schranke ───────────────────────────────────────


def test_page_limit_enforced_centrally():
    """Die Grenze hängt an open_pdf und gilt damit für jedes Werkzeug."""
    doc = fitz.open()
    for _ in range(3):
        doc.new_page()
    small = doc.tobytes()
    open_pdf(small).close()  # unauffälliges Dokument bleibt zulässig

    class _Fake:
        page_count = MAX_PAGES + 1

        def close(self):
            pass

    import app.pdf_backend as backend

    original = backend.fitz.open
    backend.fitz.open = lambda *a, **k: _Fake()
    try:
        with pytest.raises(ValueError, match="höchstens"):
            backend.open_pdf(small)
    finally:
        backend.fitz.open = original


# ── Bild-Dekompressionsbombe ──────────────────────────────────


def test_pillow_bomb_limit_is_tightened():
    from PIL import Image

    from app import pdf_backend  # noqa: F401  — setzt die Grenze beim Import

    assert Image.MAX_IMAGE_PIXELS is not None
    assert Image.MAX_IMAGE_PIXELS <= 64_000_000


# ── Keine Innereien in Fehlermeldungen ────────────────────────


def test_error_messages_do_not_leak_internals(client):
    """Eine kaputte Datei darf keine Pfade oder Bibliotheksnamen preisgeben."""
    r = client.post(
        "/api/pdf-tools/thumbnails",
        files={"file": ("kaputt.pdf", io.BytesIO(b"%PDF-1.4 nur muell"), "application/pdf")},
    )
    text = r.text.lower()
    for leak in ("/app/", "traceback", "mupdf", "site-packages", "fitz"):
        assert leak not in text, f"Fehlermeldung verrät „{leak}“: {r.text[:200]}"
