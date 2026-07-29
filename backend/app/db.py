"""Datenbank-Anbindung für optionale Benutzerkonten.

Die App bleibt ohne erreichbare Datenbank voll funktionsfähig (anonym) —
main.py fängt Verbindungsfehler im Lifespan ab. Die Engine ist über
``set_engine`` austauschbar (Test-Fixture mit SQLite-in-memory).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def set_engine(new_engine) -> None:
    """Engine austauschen (Tests)."""
    global engine
    engine = new_engine
    SessionLocal.configure(bind=new_engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
