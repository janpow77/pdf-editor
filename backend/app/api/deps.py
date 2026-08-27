"""Auth-Dependencies: Pflicht-Login, optionaler Login, Admin, Upload-Limits."""

from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.clock import utc_now
from app.config import settings
from app.db import SessionLocal, get_db
from app.models import User, UserRole
from app.security import decode_token, oauth2_scheme
from app.tool_access import get_login_required_tools
from app.tool_catalog import resolve_tool


def _resolve_user(token: str, db: Session) -> User:
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige oder abgelaufene Anmeldung",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Ungültiges Token") from None

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Benutzer existiert nicht mehr")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzer ist deaktiviert")
    if user.locked_until and user.locked_until > utc_now():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail="Konto ist temporär gesperrt"
        )
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht angemeldet",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _resolve_user(token, db)


def get_optional_user(token: str | None = Depends(oauth2_scheme)) -> User | None:
    """Optionaler Login: ohne Token None — OHNE DB-Zugriff (anonymer Pfad
    bleibt komplett DB-frei). Ein vorhandener, aber ungültiger Token führt zu
    401 statt stillem Downgrade auf anonyme Limits."""
    if token is None:
        return None
    db = SessionLocal()
    try:
        return _resolve_user(token, db)
    finally:
        db.close()


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Nur für Administratoren")
    return user


async def enforce_tool_access(
    request: Request, user: User | None = Depends(get_optional_user)
) -> None:
    """Router-Dependency: vom Administrator gesperrte Werkzeuge sind ohne
    Anmeldung nicht nutzbar.

    Die Sperre wird hier serverseitig durchgesetzt — das Ausgrauen in der
    Oberfläche ist nur Komfort und ließe sich umgehen. Gemeinsame Vorschau-
    Endpunkte (Thumbnails, Metadaten lesen …) gehören zu keinem Werkzeug und
    bleiben offen.
    """
    if user is not None:
        return
    tool_id = resolve_tool(request.url.path)
    if tool_id and tool_id in get_login_required_tools():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Dieses Werkzeug steht nur angemeldeten Nutzern zur Verfügung. "
                "Bitte melden Sie sich an — ein Konto ist kostenlos."
            ),
        )


@dataclass
class UploadLimits:
    max_file: int
    max_total: int
    user: User | None

    @property
    def max_file_mb(self) -> int:
        return self.max_file // (1024 * 1024)

    @property
    def max_total_mb(self) -> int:
        return self.max_total // (1024 * 1024)


def _anon_limits() -> UploadLimits:
    return UploadLimits(
        max_file=settings.max_file_size_mb * 1024 * 1024,
        max_total=settings.max_total_size_mb * 1024 * 1024,
        user=None,
    )


def get_upload_limits(user: User | None = Depends(get_optional_user)) -> UploadLimits:
    if user is not None:
        return UploadLimits(
            max_file=settings.max_file_size_mb_authed * 1024 * 1024,
            max_total=settings.max_total_size_mb_authed * 1024 * 1024,
            user=user,
        )
    return _anon_limits()


_current_limits: ContextVar[UploadLimits | None] = ContextVar(
    "upload_limits", default=None
)


async def attach_upload_limits(limits: UploadLimits = Depends(get_upload_limits)):
    """Router-Dependency: stellt die Limits des Requests per ContextVar bereit,
    ohne jede Endpoint-Signatur zu ändern."""
    token = _current_limits.set(limits)
    try:
        yield limits
    finally:
        _current_limits.reset(token)


def current_limits() -> UploadLimits:
    """Limits des laufenden Requests (Fallback: anonyme Limits)."""
    return _current_limits.get() or _anon_limits()
