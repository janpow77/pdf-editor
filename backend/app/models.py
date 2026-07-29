"""Datenmodell der optionalen Benutzerkonten — bewusst datensparsam.

Gespeichert werden nur: E-Mail, bcrypt-Hash, Rolle, Aktiv-Flag,
Werkzeug-Einstellungen (JSON), Zeitstempel und Lockout-Felder.
Keine IP-Adressen, keine Klarnamen, keine Nutzungshistorie.
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.USER
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # E-Mail-Verifikation + Passwort-Reset: nur Token-HASHES werden gespeichert
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verify_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verify_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reset_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > datetime.utcnow())
