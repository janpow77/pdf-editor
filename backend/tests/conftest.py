"""Test-Setup: SQLite-in-memory statt Postgres, Admin-Seed per Env.

Muss vor dem Import von app.* laufen (conftest wird von pytest zuerst
importiert): Env setzen, dann Engine auf StaticPool-SQLite tauschen.
"""

import os

os.environ.setdefault("PDFAPP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("PDFAPP_ADMIN_EMAIL", "admin@beispiel-firma.de")
os.environ.setdefault("PDFAPP_ADMIN_PASSWORD", "Admin-Passwort-123!")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db as app_db  # noqa: E402
from app.ratelimit import limiter  # noqa: E402

# Alle Tests teilen sich eine Client-IP — Rate-Limiting würde testübergreifend
# 429 auslösen. Wird hier deaktiviert; das Tier-Verhalten deckt der manuelle
# Prüfschritt (Soll-Kriterium F7) ab.
limiter.enabled = False

_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
app_db.set_engine(_test_engine)


import pytest  # noqa: E402

from app.config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def _legacy_redaction(monkeypatch):
    """Die alten Schwärzungs-Endpunkte (ohne Vorschau) sind im Betrieb
    abgeschaltet; ihre Tests laufen mit eingeschaltetem Schalter.
    test_redaction_audit prüft die Abschaltung (HTTP 410) gesondert."""
    monkeypatch.setattr(settings, "redact_without_preview", True)
