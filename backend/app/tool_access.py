"""Werkzeug-Freigabe: welche Werkzeuge nur angemeldeten Nutzern offenstehen.

Die Liste pflegt der Administrator; gespeichert wird sie als einzelner
Einstellungssatz in der Datenbank. Zwei Eigenschaften der App bleiben dabei
erhalten:

1. **Der anonyme Pfad bleibt praktisch DB-frei**: die Liste liegt im
   Prozess-Cache und wird höchstens alle 30 Sekunden einmal nachgeladen —
   nicht pro Anfrage. Ohne Datenbank (Konten deaktiviert) wird gar nicht
   gelesen.
2. **Fail-open**: ist die Datenbank nicht erreichbar, gilt der letzte bekannte
   Stand. Eine nicht lesbare Einstellung darf die App nicht lahmlegen — ohne
   DB kann sich ohnehin niemand anmelden, eine Sperre wäre dann eine Sperre
   für alle.
"""

import logging
import time

from app.tool_catalog import TOOL_IDS

logger = logging.getLogger(__name__)

SETTING_KEY = "login_required_tools"
_CACHE_TTL_SECONDS = 30.0

_cached: frozenset[str] = frozenset()
_loaded_at: float = 0.0
_db_available = False


def set_db_available(available: bool) -> None:
    """Vom Lifespan gesetzt: ohne DB wird nie gelesen."""
    global _db_available, _cached, _loaded_at
    _db_available = available
    if not available:
        _cached = frozenset()
        _loaded_at = 0.0


def _read_from_db() -> frozenset[str]:
    from app.db import SessionLocal
    from app.models import AppSetting

    db = SessionLocal()
    try:
        row = db.get(AppSetting, SETTING_KEY)
        if row is None or not isinstance(row.value, dict):
            return frozenset()
        tools = row.value.get("tools", [])
        if not isinstance(tools, list):
            return frozenset()
        return frozenset(str(t) for t in tools if str(t) in TOOL_IDS)
    finally:
        db.close()


def get_login_required_tools(force: bool = False) -> frozenset[str]:
    global _cached, _loaded_at
    if not _db_available:
        return frozenset()
    now = time.monotonic()
    if not force and _loaded_at and (now - _loaded_at) < _CACHE_TTL_SECONDS:
        return _cached
    try:
        _cached = _read_from_db()
    except Exception as e:  # DB weg: letzter bekannter Stand, App läuft weiter
        logger.warning(
            "Werkzeug-Freigabe nicht lesbar (%s) — letzter bekannter Stand gilt",
            type(e).__name__,
        )
    finally:
        _loaded_at = now
    return _cached


def set_login_required_tools(tools: list[str]) -> frozenset[str]:
    """Neue Liste speichern (nur gültige Werkzeug-IDs) und Cache erneuern."""
    from app.db import SessionLocal
    from app.models import AppSetting

    global _cached, _loaded_at
    valid = sorted({t for t in tools if t in TOOL_IDS})
    db = SessionLocal()
    try:
        row = db.get(AppSetting, SETTING_KEY)
        if row is None:
            row = AppSetting(key=SETTING_KEY, value={"tools": valid})
            db.add(row)
        else:
            row.value = {"tools": valid}
        db.commit()
    finally:
        db.close()
    _cached = frozenset(valid)
    _loaded_at = time.monotonic()
    return _cached


def reset_cache() -> None:
    """Nur für Tests: Cache verwerfen."""
    global _cached, _loaded_at
    _cached = frozenset()
    _loaded_at = 0.0
