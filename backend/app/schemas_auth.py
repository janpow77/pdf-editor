"""Pydantic-Schemas für Registrierung, Login, Konto und Admin."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


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

    _pw = field_validator("password")(_validate_password)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    is_active: bool
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
