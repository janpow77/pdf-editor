"""Tests der Admin-gesteuerten Werkzeug-Freigabe.

Kern: die Sperre wird serverseitig durchgesetzt (nicht nur in der Oberfläche),
gemeinsame Vorschau-Endpunkte bleiben offen, und ohne Datenbank sperrt nichts.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import tool_access
from app.main import app
from app.tool_catalog import TOOL_CATALOG, TOOL_IDS, resolve_tool
from tests.test_smoke import make_pdf

ADMIN = {"username": "admin@beispiel-firma.de", "password": "Admin-Passwort-123!"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_state(client):
    """Nach jedem Test alle Sperren aufheben."""
    yield
    token = client.post("/api/auth/login", data=ADMIN).json()["access_token"]
    client.put(
        "/api/admin/tool-access",
        json={"login_required": []},
        headers={"Authorization": f"Bearer {token}"},
    )


def admin_token(client) -> str:
    return client.post("/api/auth/login", data=ADMIN).json()["access_token"]


def restrict(client, tools: list[str]):
    return client.put(
        "/api/admin/tool-access",
        json={"login_required": tools},
        headers={"Authorization": f"Bearer {admin_token(client)}"},
    )


# ── Katalog-Konsistenz ────────────────────────────────────────


def test_catalog_paths_exist_in_app():
    """Jeder Katalog-Pfad muss einer echten Route entsprechen (kein Tippfehler)."""
    real: set[str] = set()
    for route in app.routes:
        if type(route).__name__ == "_IncludedRouter":
            for sub in route.original_router.routes:
                if getattr(sub, "methods", None):
                    real.add("/api" + sub.path)
        elif getattr(route, "methods", None):
            real.add(route.path)

    for tool in TOOL_CATALOG:
        for path in tool.paths:
            if path.endswith("/"):
                assert any(r.startswith(path) for r in real), f"{tool.id}: {path}"
            else:
                assert path in real, f"{tool.id}: {path} existiert nicht"


def test_catalog_matches_frontend_tiles():
    """Backend-Katalog und Kacheln der Oberfläche dürfen nicht auseinanderlaufen.

    Die Werkzeug-Definitionen liegen seit dem Apple-UI-Refactoring zentral in
    lib/toolCatalog.ts (vorher in ToolGrid.vue).
    """
    grid = Path(__file__).resolve().parents[2] / "frontend/src/lib/toolCatalog.ts"
    source = grid.read_text(encoding="utf-8")
    tile_ids = set(re.findall(r"\{ id: '([A-Za-z]+)'", source))
    assert tile_ids, "keine Werkzeuge in toolCatalog.ts gefunden"
    assert tile_ids == set(TOOL_IDS), (
        f"nur im Frontend: {sorted(tile_ids - set(TOOL_IDS))} | "
        f"nur im Katalog: {sorted(set(TOOL_IDS) - tile_ids)}"
    )


def test_resolve_tool_ignores_shared_endpoints():
    """Gemeinsame Vorschau-/Lese-Endpunkte gehören zu keinem Werkzeug."""
    for shared in (
        "/api/pdf-tools/thumbnails",
        "/api/pdf-tools/metadata/read",
        "/api/pdf-extras/form/fields",
        "/api/pdf-editor/toc/read",
        "/api/pdf-more/images/list",
        "/api/health",
    ):
        assert resolve_tool(shared) is None, shared
    assert resolve_tool("/api/pdf-tools/merge") == "merge"
    assert resolve_tool("/api/pdf-more/export/markdown") == "pdfExport"
    assert resolve_tool("/api/pdf-more/ai/translate") == "aiAssistant"


# ── Admin-Verwaltung ──────────────────────────────────────────


def test_admin_lists_all_tools(client):
    r = client.get(
        "/api/admin/tool-access", headers={"Authorization": f"Bearer {admin_token(client)}"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["tools"]) == len(TOOL_CATALOG)
    assert body["login_required"] == []
    assert {t["group"] for t in body["tools"]} == {"PDF", "Word & Excel"}


def test_admin_only(client):
    assert client.get("/api/admin/tool-access").status_code == 401
    client.post(
        "/api/auth/register",
        json={"email": "normal-tools@beispiel-firma.de", "password": "Sicher-Passwort-123!"},
    )
    token = client.post(
        "/api/auth/login",
        data={"username": "normal-tools@beispiel-firma.de", "password": "Sicher-Passwort-123!"},
    ).json()["access_token"]
    r = client.get("/api/admin/tool-access", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_unknown_ids_ignored(client):
    r = restrict(client, ["merge", "gibtsnicht"])
    assert r.status_code == 200, r.text
    assert r.json()["login_required"] == ["merge"]
    assert r.json()["ignored"] == ["gibtsnicht"]


# ── Durchsetzung ──────────────────────────────────────────────


def test_restricted_tool_blocked_for_anonymous(client):
    restrict(client, ["merge"])
    files = [
        ("files", ("a.pdf", make_pdf(1, "A"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(1, "B"), "application/pdf")),
    ]
    r = client.post("/api/pdf-tools/merge", files=files)
    assert r.status_code == 403
    assert "angemeldeten Nutzern" in r.json()["detail"]


def test_restricted_tool_allowed_when_logged_in(client):
    restrict(client, ["merge"])
    files = [
        ("files", ("a.pdf", make_pdf(1, "A"), "application/pdf")),
        ("files", ("b.pdf", make_pdf(1, "B"), "application/pdf")),
    ]
    r = client.post(
        "/api/pdf-tools/merge",
        files=files,
        headers={"Authorization": f"Bearer {admin_token(client)}"},
    )
    assert r.status_code == 200, r.text


def test_other_tools_stay_open(client):
    restrict(client, ["merge"])
    r = client.post(
        "/api/pdf-tools/split",
        data={"mode": "every_n", "every_n": "1"},
        files={"file": ("a.pdf", make_pdf(2, "A"), "application/pdf")},
    )
    assert r.status_code == 200, r.text


def test_shared_preview_endpoint_stays_open(client):
    """Vorschau-Endpunkte dürfen nicht mitgesperrt werden."""
    restrict(client, ["textEditor", "annotate"])
    r = client.post(
        "/api/pdf-tools/thumbnails?pages=1",
        files={"file": ("a.pdf", make_pdf(1, "A"), "application/pdf")},
    )
    assert r.status_code == 200, r.text


def test_multi_path_tool_blocked_on_all_paths(client):
    """Werkzeuge mit mehreren Endpunkten sind vollständig gesperrt."""
    restrict(client, ["protect", "aiAssistant"])
    pdf = make_pdf(1, "A")
    for path, data in (
        ("/api/pdf-tools/protect", {"password": "Geheim-123456"}),
        ("/api/pdf-tools/unlock", {"password": "Geheim-123456"}),
        ("/api/pdf-more/ai/summarize", {}),
        ("/api/pdf-more/ai/keywords", {}),
    ):
        r = client.post(path, data=data, files={"file": ("a.pdf", pdf, "application/pdf")})
        assert r.status_code == 403, f"{path}: {r.status_code}"


def test_health_reports_restrictions(client):
    restrict(client, ["ocr", "batch"])
    body = client.get("/api/health").json()
    assert body["login_required_tools"] == ["batch", "ocr"]


def test_lifting_restriction_takes_effect_immediately(client):
    restrict(client, ["split"])
    args = {
        "data": {"mode": "every_n", "every_n": "1"},
        "files": {"file": ("a.pdf", make_pdf(2, "A"), "application/pdf")},
    }
    assert client.post("/api/pdf-tools/split", **args).status_code == 403
    restrict(client, [])
    assert client.post("/api/pdf-tools/split", **args).status_code == 200


def test_without_database_nothing_is_restricted(client):
    """Ohne Datenbank kann sich niemand anmelden — dann darf nichts sperren."""
    restrict(client, ["merge"])
    tool_access.set_db_available(False)
    try:
        files = [
            ("files", ("a.pdf", make_pdf(1, "A"), "application/pdf")),
            ("files", ("b.pdf", make_pdf(1, "B"), "application/pdf")),
        ]
        r = client.post("/api/pdf-tools/merge", files=files)
        assert r.status_code == 200, r.text
        assert client.get("/api/health").json()["login_required_tools"] == []
    finally:
        tool_access.set_db_available(True)
        tool_access.reset_cache()


def test_db_error_keeps_last_known_state(client, monkeypatch):
    """Fällt die DB später aus, gilt der letzte bekannte Stand (fail-open)."""
    restrict(client, ["merge"])
    tool_access.reset_cache()

    def boom():
        raise RuntimeError("DB weg")

    monkeypatch.setattr(tool_access, "_read_from_db", boom)
    assert tool_access.get_login_required_tools(force=True) == frozenset()
