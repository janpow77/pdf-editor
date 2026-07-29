"""Tests für Restpunkte: Async-Jobs, E-Mail-Verifikation, Passwort-Reset,
Turnstile und Alembic."""

import json
import re
import time

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from tests.test_auth import GOOD_PW, _auth_headers, _login, _register
from tests.test_smoke import make_pdf


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def captured_mails(monkeypatch):
    """SMTP-Flows aktivieren und Mails abfangen statt versenden."""
    mails: list[dict] = []

    async def _capture(to: str, subject: str, body: str) -> None:
        mails.append({"to": to, "subject": subject, "body": body})

    import app.api.auth as auth_mod

    monkeypatch.setattr(settings, "smtp_host", "mail.test.invalid")
    monkeypatch.setattr(settings, "public_base_url", "https://pdf.example.org")
    monkeypatch.setattr(auth_mod, "send_plain_mail", _capture)
    return mails


def _token_from(body: str) -> str:
    m = re.search(r"token=([A-Za-z0-9_\-]+)", body)
    assert m, body
    return m.group(1)


# ── E-Mail-Verifikation ───────────────────────────────────────


def test_email_verification_flow(client, captured_mails):
    r = _register(client, "verify-flow@beispiel-firma.de")
    assert r.status_code == 201
    token_auth = r.json()["access_token"]
    assert r.json()["user"]["is_verified"] is False

    assert len(captured_mails) == 1
    assert captured_mails[0]["to"] == "verify-flow@beispiel-firma.de"
    verify_token = _token_from(captured_mails[0]["body"])

    r = client.post("/api/auth/verify-email", json={"token": verify_token})
    assert r.status_code == 200

    r = client.get("/api/auth/me", headers=_auth_headers(token_auth))
    assert r.json()["is_verified"] is True

    # Token ist verbraucht
    r = client.post("/api/auth/verify-email", json={"token": verify_token})
    assert r.status_code == 400


def test_verification_not_sent_without_smtp(client):
    r = _register(client, "ohne-smtp@beispiel-firma.de")
    assert r.status_code == 201  # Registrierung läuft ohne SMTP normal weiter


# ── Passwort-Reset ────────────────────────────────────────────


def test_password_reset_flow(client, captured_mails):
    _register(client, "reset-flow@beispiel-firma.de")
    captured_mails.clear()

    r = client.post(
        "/api/auth/request-password-reset",
        json={"email": "reset-flow@beispiel-firma.de"},
    )
    assert r.status_code == 202
    reset_token = _token_from(captured_mails[0]["body"])

    new_pw = "Neues-Passwort-99!"
    r = client.post(
        "/api/auth/reset-password", json={"token": reset_token, "password": new_pw}
    )
    assert r.status_code == 200

    assert _login(client, "reset-flow@beispiel-firma.de", new_pw).status_code == 200
    assert _login(client, "reset-flow@beispiel-firma.de", GOOD_PW).status_code == 401
    # Token verbraucht
    r = client.post(
        "/api/auth/reset-password", json={"token": reset_token, "password": new_pw}
    )
    assert r.status_code == 400


def test_password_reset_no_enumeration(client, captured_mails):
    r1 = client.post(
        "/api/auth/request-password-reset",
        json={"email": "gibtsnicht@beispiel-firma.de"},
    )
    assert r1.status_code == 202
    assert captured_mails == []  # keine Mail, aber gleiche Antwort

    r = client.post(
        "/api/auth/reset-password",
        json={"token": "erfunden", "password": "Neues-Passwort-99!"},
    )
    assert r.status_code == 400


# ── Turnstile (optional) ──────────────────────────────────────


def test_turnstile_enforced_when_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "turnstile_secret", "test-secret")

    r = _register(client, "turnstile@beispiel-firma.de")
    assert r.status_code == 403  # ohne Token abgelehnt

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"success": True}

    import app.api.auth as auth_mod

    monkeypatch.setattr(auth_mod.httpx, "post", lambda *a, **k: _Resp())
    r = client.post(
        "/api/auth/register",
        json={
            "email": "turnstile@beispiel-firma.de",
            "password": GOOD_PW,
            "turnstile_token": "dummy",
        },
    )
    assert r.status_code == 201


# ── Async-Jobs ────────────────────────────────────────────────


def _wait_terminal(client, job_id: str, timeout: float = 30.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = client.get(f"/api/pdf-extras/jobs/{job_id}")
        assert r.status_code == 200
        status = r.json()["status"]
        if status in ("done", "error"):
            return status
        time.sleep(0.2)
    raise AssertionError("Job nicht terminal")


def test_compare_job_roundtrip(client):
    r = client.post(
        "/api/pdf-extras/jobs/compare",
        data={"include_visual": "false"},
        files={
            "file_a": ("a.pdf", make_pdf(1, "Version A"), "application/pdf"),
            "file_b": ("b.pdf", make_pdf(1, "Version B"), "application/pdf"),
        },
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]

    assert _wait_terminal(client, job_id) == "done"

    r = client.get(f"/api/pdf-extras/jobs/{job_id}/result")
    assert r.status_code == 200
    data = json.loads(r.content)
    assert isinstance(data, dict) and data  # Vergleichsdaten vorhanden

    # Ergebnis ist einmalig — zweiter Abruf 404
    assert client.get(f"/api/pdf-extras/jobs/{job_id}/result").status_code == 404


def test_ocr_job_reaches_terminal_state(client):
    r = client.post(
        "/api/pdf-extras/jobs/ocr",
        data={"language": "deu"},
        files={"file": ("s.pdf", make_pdf(1, "Scan"), "application/pdf")},
    )
    assert r.status_code == 202
    # Ohne lokales Tesseract endet der Job als error — beides ist terminal ok
    assert _wait_terminal(client, r.json()["job_id"]) in ("done", "error")


def test_job_ownership():
    from app import jobs as job_store

    job_id = job_store.submit("owner-a", "x.pdf", "application/pdf", lambda: (b"x", {}))
    for _ in range(50):
        if job_store.get(job_id, "owner-a") and job_store.get(job_id, "owner-a").status == "done":
            break
        time.sleep(0.05)
    assert job_store.get(job_id, "owner-b") is None
    assert job_store.take_result(job_id, "owner-b") is None
    assert job_store.take_result(job_id, "owner-a") is not None


def test_unknown_job_404(client):
    assert client.get("/api/pdf-extras/jobs/gibtsnicht").status_code == 404


# ── Alembic ───────────────────────────────────────────────────


def test_alembic_upgrade_head_on_fresh_db(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect

    db_path = tmp_path / "migrationstest.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert {"email", "is_verified", "reset_token_hash", "verify_token_hash"} <= cols
    engine.dispose()
