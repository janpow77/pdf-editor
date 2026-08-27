"""JWT- und Passwort-Helfer (Port aus audit_designer core/security.py)."""

from datetime import timedelta

import bcrypt as _bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.clock import utc_now
from app.config import settings

ALGORITHM = "HS256"

# auto_error=False: dasselbe Schema dient Pflicht- UND Optional-Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return _bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("ascii")
        )
    except (ValueError, UnicodeEncodeError):
        return False


def get_password_hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("ascii")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = utc_now() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
