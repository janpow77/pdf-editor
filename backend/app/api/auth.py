"""Registrierung, Login und Profil.

Datenschutz: Fehlgeschlagene Logins werden NICHT mit E-Mail-Adresse geloggt.
Die Login-Fehlermeldung ist für „Konto existiert nicht" und „Passwort falsch"
identisch (kein User-Enumeration-Kanal).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import settings
from app.db import get_db
from app.models import User, UserRole
from app.ratelimit import limiter
from app.schemas_auth import RegisterRequest, Token, UserResponse
from app.security import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])

LOGIN_ERROR = "E-Mail-Adresse oder Passwort ist falsch"


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
    db: Session = Depends(get_db),
):
    """Offene Registrierung: E-Mail + Passwort, Konto sofort aktiv."""
    _require_db(request)
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409, detail="Für diese E-Mail-Adresse existiert bereits ein Konto"
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

    if user and user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Konto ist temporär gesperrt — bitte in 30 Minuten erneut versuchen",
        )

    if not user or not verify_password(form_data.password, user.hashed_password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 10:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
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
    user.last_login = datetime.utcnow()
    db.commit()

    return _token_for(user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse.model_validate(user)
