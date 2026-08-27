"""Einheitliche UTC-Zeit für die weiterhin zeitzonenlosen DB-Spalten."""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Aktuelle UTC-Zeit ohne tzinfo für bestehende ``DateTime``-Spalten.

    PostgreSQL und SQLite speichern die Konten-Zeitstempel derzeit als
    ``timestamp without time zone``. Der moderne, nicht abgekündigte Ersatz
    für ``datetime.utcnow()`` wird deshalb an dieser Grenze wieder naiv.
    """

    return datetime.now(UTC).replace(tzinfo=None)
