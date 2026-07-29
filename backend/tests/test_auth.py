"""Tests für Registrierung, Login, Lockout, Admin, Preferences und Limits."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.test_smoke import make_pdf

GOOD_PW = "Sicheres-Passwort-1!"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _register(client, email, password=GOOD_PW):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def _login(client, email, password=GOOD_PW):
    return client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_me_roundtrip(client):
    r = _register(client, "nutzer1@beispiel-firma.de")
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]

    r = _login(client, "nutzer1@beispiel-firma.de")
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/auth/me", headers=_auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "nutzer1@beispiel-firma.de"
    assert r.json()["role"] == "USER"


def test_register_duplicate_409(client):
    _register(client, "doppelt@beispiel-firma.de")
    r = _register(client, "doppelt@beispiel-firma.de")
    assert r.status_code == 409


def test_register_weak_password_422(client):
    r = _register(client, "schwach@beispiel-firma.de", password="kurz")
    assert r.status_code == 422


def test_login_identical_error_for_unknown_and_wrong(client):
    _register(client, "enum@beispiel-firma.de")
    r1 = _login(client, "existiert-nicht@beispiel-firma.de", "Irgendwas-123!")
    r2 = _login(client, "enum@beispiel-firma.de", "Falsches-Passwort-1!")
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"]


def test_lockout_after_10_failed_attempts(client):
    _register(client, "lockout@beispiel-firma.de")
    for _ in range(10):
        r = _login(client, "lockout@beispiel-firma.de", "Falsch-123456!")
        assert r.status_code == 401
    r = _login(client, "lockout@beispiel-firma.de")  # richtiges Passwort, aber gesperrt
    assert r.status_code == 423


def test_invalid_token_401_no_silent_downgrade(client):
    r = client.get("/api/auth/me", headers=_auth_headers("kaputt.token.xyz"))
    assert r.status_code == 401
    # Auch Tool-Endpoints: ungültiger Token → 401 statt anonymer Limits
    r = client.post(
        "/api/pdf-tools/merge",
        headers=_auth_headers("kaputt.token.xyz"),
        files=[
            ("files", ("a.pdf", make_pdf(1, "a"), "application/pdf")),
            ("files", ("b.pdf", make_pdf(1, "b"), "application/pdf")),
        ],
    )
    assert r.status_code == 401


def test_admin_seed_and_user_management(client):
    r = _login(client, "admin@beispiel-firma.de", "Admin-Passwort-123!")
    assert r.status_code == 200, r.text
    admin_token = r.json()["access_token"]
    admin_h = _auth_headers(admin_token)
    admin_id = r.json()["user"]["id"]

    _register(client, "verwaltet@beispiel-firma.de")

    r = client.get("/api/admin/users", headers=admin_h)
    assert r.status_code == 200
    users = {u["email"]: u for u in r.json()}
    assert "verwaltet@beispiel-firma.de" in users
    target_id = users["verwaltet@beispiel-firma.de"]["id"]

    # USER darf nicht in den Admin-Bereich
    user_token = _login(client, "verwaltet@beispiel-firma.de").json()["access_token"]
    r = client.get("/api/admin/users", headers=_auth_headers(user_token))
    assert r.status_code == 403
    # Ohne Login: 401
    assert client.get("/api/admin/users").status_code == 401

    # Deaktivieren → Login 400
    r = client.patch(
        f"/api/admin/users/{target_id}", json={"is_active": False}, headers=admin_h
    )
    assert r.status_code == 200
    assert _login(client, "verwaltet@beispiel-firma.de").status_code == 400

    # Selbst-Deaktivierung verboten
    r = client.patch(
        f"/api/admin/users/{admin_id}", json={"is_active": False}, headers=admin_h
    )
    assert r.status_code == 400

    # Löschen
    r = client.delete(f"/api/admin/users/{target_id}", headers=admin_h)
    assert r.status_code == 204

    # Config-Endpoint
    r = client.get("/api/admin/config", headers=admin_h)
    assert r.status_code == 200
    assert r.json()["max_file_size_mb_authed"] == settings.max_file_size_mb_authed


def test_preferences_roundtrip_and_size_cap(client):
    token = _register(client, "prefs@beispiel-firma.de").json()["access_token"]
    h = _auth_headers(token)

    r = client.get("/api/me/preferences", headers=h)
    assert r.status_code == 200 and r.json() == {}

    r = client.put(
        "/api/me/preferences",
        json={"ocr_language": "eng", "watermark_text": "ENTWURF"},
        headers=h,
    )
    assert r.status_code == 200
    assert client.get("/api/me/preferences", headers=h).json()["ocr_language"] == "eng"

    r = client.put(
        "/api/me/preferences", json={"blob": "x" * 20000}, headers=h
    )
    assert r.status_code == 413


def test_account_self_delete(client):
    token = _register(client, "loeschen@beispiel-firma.de").json()["access_token"]
    h = _auth_headers(token)

    r = client.request("DELETE", "/api/me", json={"password": "falsch"}, headers=h)
    assert r.status_code == 401

    r = client.request("DELETE", "/api/me", json={"password": GOOD_PW}, headers=h)
    assert r.status_code == 204
    assert _login(client, "loeschen@beispiel-firma.de").status_code == 401


def test_tiered_upload_limits(client, monkeypatch):
    monkeypatch.setattr(settings, "max_file_size_mb", 1)
    monkeypatch.setattr(settings, "max_file_size_mb_authed", 2)

    payload = b"%PDF-1.4" + b"0" * (1024 * 1024 + 1024)  # ~1,001 MB

    r = client.post(
        "/api/pdf-tools/split",
        data={"mode": "every_n", "every_n": "1"},
        files={"file": ("gross.pdf", payload, "application/pdf")},
    )
    assert r.status_code == 400  # anonym: über 1-MB-Limit

    token = _register(client, "limits@beispiel-firma.de").json()["access_token"]
    r = client.post(
        "/api/pdf-tools/split",
        data={"mode": "every_n", "every_n": "1"},
        files={"file": ("gross.pdf", payload, "application/pdf")},
        headers=_auth_headers(token),
    )
    # Angemeldet: Größen-Check passiert (kein 400 wegen Limit) — die Datei ist
    # kein valides PDF, daher Verarbeitungsfehler 500 statt Limit-Fehler.
    assert r.status_code != 400 or "zu groß" not in r.json().get("detail", "")


def test_default_rate_limit_tiers(client, monkeypatch):
    """Regressionstest: Default-Limits greifen auch auf include_router-Routen
    (slowapi-Middleware tat das nicht — eigene Prüfung in RateTierMiddleware)."""
    from app import ratelimit

    monkeypatch.setattr(settings, "rate_limit_default", "3/minute")
    monkeypatch.setattr(settings, "rate_limit_authed", "50/minute")
    monkeypatch.setattr(ratelimit.limiter, "enabled", True)
    # frische Zähler für diesen Test
    monkeypatch.setattr(ratelimit, "_storage", ratelimit.MemoryStorage())
    monkeypatch.setattr(
        ratelimit, "_checker", ratelimit.MovingWindowRateLimiter(ratelimit._storage)
    )

    # Token holen, BEVOR das anonyme Kontingent aufgebraucht ist
    token = _register(client, "ratelimit@beispiel-firma.de").json()["access_token"]

    codes = [client.get("/api/pdf-tools/status").status_code for _ in range(5)]
    assert codes.count(200) >= 2 and 429 in codes, codes

    # Health bleibt exempt
    assert client.get("/api/health").status_code == 200

    # Angemeldet: eigener Key + höheres Limit → weiter 200 trotz anonymer Sperre
    authed = [
        client.get("/api/pdf-tools/status", headers=_auth_headers(token)).status_code
        for _ in range(5)
    ]
    assert all(c == 200 for c in authed), authed
