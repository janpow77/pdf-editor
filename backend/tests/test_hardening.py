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


def test_no_duplicate_headers(client):
    """Kein Name darf zweimal in einer Antwort stehen.

    Doppelte Kopfzeilen entstehen leicht, wenn Proxy und Anwendung dieselbe
    Angabe setzen. Der Browser wendet zwei CSP-Kopfzeilen als Schnittmenge an —
    das ist nicht unsicher, macht aber jede Fehlersuche zäh, und bei
    Cache-Control führt es zu widersprüchlichen Angaben.
    """
    r = client.get("/api/health")
    names = [k.lower() for k in r.headers.keys()]
    doppelt = {n for n in names if names.count(n) > 1}
    assert not doppelt, f"Doppelte Kopfzeilen: {sorted(doppelt)}"


def test_api_responses_are_not_cacheable(client):
    """Jede Antwort dieses Dienstes ist eine Nutzerdatei oder eine Auskunft
    über den Anfragenden. Nichts davon darf in einem Cache landen — das ist
    die Kopfzeilen-Entsprechung des Versprechens „keine Datenspeicherung"."""
    r = client.get("/api/health")
    assert r.headers.get("cache-control") == "no-store"


def test_nginx_and_backend_headers_stay_in_sync():
    """Die Kopfzeilen stehen an zwei Orten — sie dürfen nicht auseinanderlaufen.

    nginx bedient die Oberfläche, das Backend die API und den Fall ohne Proxy.
    Wird eine Kopfzeile nur an einer Stelle ergänzt, entsteht genau die Lücke,
    die niemand bemerkt. Deshalb vergleicht dieser Test beide Listen.
    """
    import pathlib
    import re

    from app.hardening import _STATIC_HEADERS

    conf = (
        pathlib.Path(__file__).parents[2] / "frontend" / "security-headers.conf"
    ).read_text(encoding="utf-8")
    nginx_names = {
        m.group(1).lower() for m in re.finditer(r"^add_header\s+(\S+)", conf, re.M)
    }
    backend_names = {name.lower() for name, _ in _STATIC_HEADERS}

    # Cache-Control setzt nginx pro Ort unterschiedlich (Assets lange, API gar
    # nicht) und steht deshalb bewusst nicht im gemeinsamen Schnipsel.
    backend_names.discard("cache-control")

    assert nginx_names == backend_names, (
        f"Nur in nginx: {sorted(nginx_names - backend_names)} · "
        f"nur im Backend: {sorted(backend_names - nginx_names)}"
    )


def test_nginx_config_includes_headers_in_every_location():
    """Jeder location-Block muss das Schnipsel einbinden.

    In nginx ersetzt ein `add_header` im Block alle geerbten Kopfzeilen. Ein
    Block ohne `include` liefert daher **keine** Sicherheitskopfzeilen — auch
    dann nicht, wenn sie weiter oben stehen.
    """
    import pathlib
    import re

    conf = (
        pathlib.Path(__file__).parents[2] / "frontend" / "nginx.conf"
    ).read_text(encoding="utf-8")
    blocks = re.findall(r"location\s+([^\s{]+(?:\s+[^\s{]+)?)\s*\{(.*?)\n    \}", conf, re.S)
    assert blocks, "Keine location-Blöcke gefunden — Test greift ins Leere"
    ohne = [name for name, body in blocks if "security-headers.conf" not in body]
    assert not ohne, f"location-Block ohne Sicherheitskopfzeilen: {ohne}"


def test_nginx_serves_mjs_as_javascript():
    """`.mjs` braucht einen ausdrücklichen Typ — sonst bricht die Vorschau.

    nginx' mitgelieferte `mime.types` kennt die Endung nicht und antwortet mit
    `application/octet-stream`. Zusammen mit `X-Content-Type-Options: nosniff`
    verweigert der Browser die Ausführung; der pdf.js-Worker ist genau so eine
    Datei. Ohne nosniff fiel das nicht auf, weil der Browser den Typ erraten
    hat — die Härtung machte den Fehler erst sichtbar, und zwar in Produktion.

    Der Test greift nur, solange der Build wirklich `.mjs`-Dateien erzeugt.
    """
    import pathlib

    frontend = pathlib.Path(__file__).parents[2] / "frontend"
    dist = frontend / "dist"
    if dist.is_dir() and not any(dist.rglob("*.mjs")):
        pytest.skip("Build enthält keine .mjs-Dateien")

    conf = (frontend / "nginx.conf").read_text(encoding="utf-8")
    assert "\\.mjs$" in conf, "Kein location-Block für .mjs in nginx.conf"
    mjs_block = conf.split("\\.mjs$")[1].split("location")[0]
    assert "default_type text/javascript" in mjs_block
    assert "types { }" in mjs_block, "Ohne leere types-Tabelle greift default_type nicht"


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
