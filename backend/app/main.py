"""PDF-Editor-App — öffentliches, zustandsloses Backend.

Alle Verarbeitungen laufen vollständig im Arbeitsspeicher; es gibt keine
Datenbank und keine persistente Ablage von Nutzerdateien. Schutz vor
Missbrauch über Rate-Limiting pro IP und Dateigrößen-Limits (app/config.py).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import OperationalError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api import (
    admin,
    auth,
    mail,
    me,
    pdf_converter,
    pdf_editor,
    pdf_extras,
    pdf_more,
    pdf_tools,
)
from app.api.deps import attach_upload_limits
from app.config import settings
from app.ratelimit import RateTierMiddleware, limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_admin() -> None:
    """Ersten Admin aus Env anlegen — idempotent."""
    from app.db import SessionLocal
    from app.models import User, UserRole
    from app.security import get_password_hash

    if not settings.admin_email or not settings.admin_password:
        return
    email = settings.admin_email.strip().lower()
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash(settings.admin_password),
                role=UserRole.ADMIN,
                is_active=True,
                preferences={},
            )
        )
        db.commit()
        logger.info("Admin-Konto angelegt")
    finally:
        db.close()


def _ensure_user_columns(engine) -> None:
    """Fehlende users-Spalten auf Bestands-DBs nachziehen (idempotent).

    create_all legt nur fehlende Tabellen an, keine Spalten — ohne diesen
    Schritt würde eine vor der Verifikations-Erweiterung angelegte DB die
    Konten deaktivieren. Entspricht Alembic-Migration 0001.
    """
    import sqlalchemy as sa

    inspector = sa.inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("users")}
    wanted = {
        "is_verified": "BOOLEAN",
        "verify_token_hash": "VARCHAR(64)",
        "verify_token_expires": "TIMESTAMP",
        "reset_token_hash": "VARCHAR(64)",
        "reset_token_expires": "TIMESTAMP",
    }
    with engine.begin() as conn:
        for name, ddl_type in wanted.items():
            if name not in existing:
                conn.execute(sa.text(f"ALTER TABLE users ADD COLUMN {name} {ddl_type}"))
        if "is_verified" not in existing:
            conn.execute(sa.text("UPDATE users SET is_verified = false WHERE is_verified IS NULL"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Konten sind optional: ohne erreichbare DB läuft die App anonym weiter.
    from app import db as app_db
    from app import models  # noqa: F401  — registriert Tabellen an Base

    if settings.secret_key == "dev-only-nicht-fuer-produktion":
        logger.critical(
            "PDFAPP_SECRET_KEY ist nicht gesetzt — Benutzerkonten sind deaktiviert "
            "(JWT wäre fälschbar). Anonyme Nutzung läuft weiter."
        )
        app.state.db_available = False
        yield
        return

    try:
        app_db.Base.metadata.create_all(bind=app_db.engine)
        _ensure_user_columns(app_db.engine)
        seed_admin()
        app.state.db_available = True
    except OperationalError:
        logger.warning(
            "Datenbank nicht erreichbar — Benutzerkonten deaktiviert, anonyme Nutzung läuft weiter"
        )
        app.state.db_available = False
    yield


app = FastAPI(
    title="PDF-Editor",
    description="Kostenlose PDF-, Word- und Excel-Werkzeuge — ohne Datenspeicherung.",
    version="0.2.0",
    lifespan=lifespan,
)

# Default-Limits laufen in RateTierMiddleware (siehe app/ratelimit.py);
# der slowapi-Limiter bedient nur die per-Route-Dekoratoren.
app.state.limiter = limiter
app.add_middleware(RateTierMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Zu viele Anfragen — bitte kurz warten und erneut versuchen. "
                f"(Limit: {exc.detail})"
            )
        },
    )


@app.get("/api/health")
async def health(request: Request):
    from app.services.pdf_extras_service import get_pdf_extras
    from app.services.pdf_more_service import get_pdf_more
    from app.services.pdf_tools_service import get_pdf_tools

    return {
        "status": "ok",
        "accounts": bool(getattr(request.app.state, "db_available", False)),
        "turnstile_site_key": settings.turnstile_site_key or None,
        "account_flows": bool(settings.smtp_host and settings.public_base_url),
        "features": {
            **get_pdf_tools().check_features(),
            **get_pdf_extras().check_features(),
            **get_pdf_more().check_features(),
        },
    }


# Datei-Router bekommen die gestuften Upload-Limits (anonym vs. angemeldet)
_limit_deps = [Depends(attach_upload_limits)]
app.include_router(pdf_tools.router, prefix="/api", dependencies=_limit_deps)
app.include_router(pdf_editor.router, prefix="/api", dependencies=_limit_deps)
app.include_router(pdf_converter.router, prefix="/api", dependencies=_limit_deps)
app.include_router(pdf_extras.router, prefix="/api", dependencies=_limit_deps)
app.include_router(pdf_more.router, prefix="/api", dependencies=_limit_deps)
app.include_router(mail.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
