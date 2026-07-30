"""Pydantic-Schemas für Registrierung, Login, Konto und Admin."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password(v: str) -> str:
    """Passwort-Policy (identisch zur audit_designer-Vorlage)."""
    if len(v) < 12:
        raise ValueError("Passwort muss mindestens 12 Zeichen lang sein")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Passwort muss mindestens einen Großbuchstaben enthalten")
    if not re.search(r"[a-z]", v):
        raise ValueError("Passwort muss mindestens einen Kleinbuchstaben enthalten")
    if not re.search(r"\d", v):
        raise ValueError("Passwort muss mindestens eine Zahl enthalten")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
        raise ValueError("Passwort muss mindestens ein Sonderzeichen enthalten")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    turnstile_token: str | None = None

    _pw = field_validator("password")(_validate_password)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str

    _pw = field_validator("password")(_validate_password)


class VerifyEmailRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    is_active: bool
    is_verified: bool = False
    created_at: datetime
    last_login: datetime | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserResponse(UserResponse):
    locked: bool = False


class AdminUserUpdate(BaseModel):
    is_active: bool


class AccountDelete(BaseModel):
    password: str


class ToolAccessUpdate(BaseModel):
    """Werkzeuge, die nur angemeldeten Nutzern offenstehen (Werkzeug-IDs)."""

    login_required: list[str] = Field(default_factory=list, max_length=200)
