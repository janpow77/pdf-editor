"""Registrierung, Login und Profil.

Datenschutz: Fehlgeschlagene Logins werden NICHT mit E-Mail-Adresse geloggt.
Die Login-Fehlermeldung ist für „Konto existiert nicht" und „Passwort falsch"
identisch (kein User-Enumeration-Kanal).
"""

import hashlib
import logging
import secrets
from datetime import timedelta

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.clock import utc_now
from app.config import settings
from app.db import get_db
from app.models import User, UserRole
from app.ratelimit import limiter
from app.mailer import mail_configured, send_plain_mail
from app.schemas_auth import (
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    Token,
    UserResponse,
    VerifyEmailRequest,
)
from app.security import create_access_token, get_password_hash, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

LOGIN_ERROR = "E-Mail-Adresse oder Passwort ist falsch"

# Dummy-Hash für konstante Login-Dauer bei unbekannter Adresse (Timing-Kanal)
_DUMMY_HASH = get_password_hash("timing-dummy-passwort")


def _require_db(request: Request) -> None:
    if not getattr(request.app.state, "db_available", False):
        raise HTTPException(
            status_code=503,
            detail="Benutzerkonten sind auf diesem Server derzeit nicht verfügbar",
        )


def _token_for(user: User) -> Token:
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return Token(access_token=access_token, user=UserResponse.model_validate(user))


@router.post("/register", response_model=Token, status_code=201)
@limiter.limit("10/hour")
def register(
    request: Request,
    payload: RegisterRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Offene Registrierung: E-Mail + Passwort, Konto sofort aktiv."""
    _require_db(request)
    verify_turnstile_or_403(
        payload.turnstile_token, request.client.host if request.client else None
    )
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409,
            detail="Für diese E-Mail-Adresse existiert bereits ein Konto",
        )
    user = User(
        email=email,
        hashed_password=get_password_hash(payload.password),
        role=UserRole.USER,
        is_active=True,
        preferences={},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    issue_verification(db, user, background)
    return _token_for(user)


@router.post("/login", response_model=Token)
@limiter.limit("10/15minutes")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login mit E-Mail + Passwort (OAuth2-Form, username = E-Mail)."""
    _require_db(request)
    email = form_data.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if user and user.locked_until and user.locked_until > utc_now():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Konto ist temporär gesperrt — bitte in 30 Minuten erneut versuchen",
        )

    if user:
        password_ok = verify_password(form_data.password, user.hashed_password)
    else:
        verify_password(form_data.password, _DUMMY_HASH)  # konstante Dauer
        password_ok = False
    if not password_ok:
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 10:
                user.locked_until = utc_now() + timedelta(minutes=30)
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_ERROR,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Benutzer ist deaktiviert")

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = utc_now()
    db.commit()

    return _token_for(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)


# ── E-Mail-Verifikation & Passwort-Reset ──────────────────────
# Es werden nur Token-Hashes gespeichert; Mails gehen nur raus, wenn SMTP und
# PDFAPP_PUBLIC_BASE_URL konfiguriert sind. Antworten verraten nie, ob eine
# Adresse existiert.


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _flows_enabled() -> bool:
    return mail_configured() and bool(settings.public_base_url)


async def _send_flow_mail(to: str, subject: str, body: str) -> None:
    try:
        await send_plain_mail(to, subject, body)
    except Exception:
        # Kein Adress-Log, keine SMTP-Details
        logger.warning("Konto-Mailversand fehlgeschlagen (%s)", subject)


def issue_verification(db: Session, user: User, background: BackgroundTasks) -> None:
    """Verifikations-Mail anstoßen (best effort, idempotent aufrufbar)."""
    if not _flows_enabled() or user.is_verified:
        return
    token = secrets.token_urlsafe(32)
    user.verify_token_hash = _hash_token(token)
    user.verify_token_expires = utc_now() + timedelta(hours=24)
    db.commit()
    link = f"{settings.public_base_url.rstrip('/')}/email-bestaetigen?token={token}"
    background.add_task(
        _send_flow_mail,
        user.email,
        "E-Mail-Adresse bestätigen — PDF-Editor",
        "Guten Tag,\n\n"
        "bitte bestätigen Sie Ihre E-Mail-Adresse für Ihr PDF-Editor-Konto:\n\n"
        f"{link}\n\n"
        "Der Link ist 24 Stunden gültig. Falls Sie kein Konto erstellt haben, "
        "ignorieren Sie diese Nachricht.\n",
    )


@router.post("/request-verification", status_code=202)
@limiter.limit("5/hour")
def request_verification(
    request: Request,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.is_verified:
        return {"detail": "E-Mail-Adresse ist bereits bestätigt"}
    if not _flows_enabled():
        raise HTTPException(
            status_code=503,
            detail="Mailversand ist auf diesem Server nicht konfiguriert",
        )
    db_user = db.get(User, user.id)
    issue_verification(db, db_user, background)
    return {"detail": "Bestätigungs-Mail wurde versendet"}


@router.post("/verify-email")
def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    _require_db(request)
    token_hash = _hash_token(payload.token)
    user = db.query(User).filter(User.verify_token_hash == token_hash).first()
    if (
        not user
        or not user.verify_token_expires
        or user.verify_token_expires < utc_now()
    ):
        raise HTTPException(status_code=400, detail="Link ist ungültig oder abgelaufen")
    user.is_verified = True
    user.verify_token_hash = None
    user.verify_token_expires = None
    db.commit()
    return {"detail": "E-Mail-Adresse bestätigt"}


@router.post("/request-password-reset", status_code=202)
@limiter.limit("5/hour")
def request_password_reset(
    request: Request,
    payload: PasswordResetRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Antwortet immer 202 — keine Auskunft, ob die Adresse existiert."""
    _require_db(request)
    generic = {"detail": "Falls ein Konto existiert, wurde eine E-Mail versendet"}
    if not _flows_enabled():
        return generic
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return generic
    token = secrets.token_urlsafe(32)
    user.reset_token_hash = _hash_token(token)
    user.reset_token_expires = utc_now() + timedelta(hours=2)
    db.commit()
    link = f"{settings.public_base_url.rstrip('/')}/passwort-reset?token={token}"
    background.add_task(
        _send_flow_mail,
        user.email,
        "Passwort zurücksetzen — PDF-Editor",
        "Guten Tag,\n\n"
        "über diesen Link können Sie ein neues Passwort für Ihr "
        f"PDF-Editor-Konto setzen:\n\n{link}\n\n"
        "Der Link ist 2 Stunden gültig. Falls Sie das nicht angefordert haben, "
        "ignorieren Sie diese Nachricht.\n",
    )
    return generic


@router.post("/reset-password")
def reset_password(
    request: Request,
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    _require_db(request)
    token_hash = _hash_token(payload.token)
    user = db.query(User).filter(User.reset_token_hash == token_hash).first()
    if not user or not user.reset_token_expires or user.reset_token_expires < utc_now():
        raise HTTPException(status_code=400, detail="Link ist ungültig oder abgelaufen")
    user.hashed_password = get_password_hash(payload.password)
    user.reset_token_hash = None
    user.reset_token_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return {"detail": "Passwort wurde geändert"}


# ── Cloudflare Turnstile (optional) ───────────────────────────


def verify_turnstile_or_403(token: str | None, remote_ip: str | None) -> None:
    """Nur aktiv, wenn PDFAPP_TURNSTILE_SECRET gesetzt ist."""
    if not settings.turnstile_secret:
        return
    if not token:
        raise HTTPException(status_code=403, detail="Sicherheitsprüfung erforderlich")
    try:
        resp = httpx.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": settings.turnstile_secret,
                "response": token,
                **({"remoteip": remote_ip} if remote_ip else {}),
            },
            timeout=10,
        )
        ok = resp.status_code == 200 and resp.json().get("success") is True
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(status_code=403, detail="Sicherheitsprüfung fehlgeschlagen")
