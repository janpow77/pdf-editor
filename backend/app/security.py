"""JWT- und Passwort-Helfer (Port aus audit_designer core/security.py)."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import bcrypt as _bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

ALGORITHM = "HS256"

# passlib 1.7.4 liest bcrypt.__about__.__version__; in bcrypt>=4.1 existiert
# __about__ nicht mehr — Kompat-Shim gegen die laute Warnung.
if not hasattr(_bcrypt, "__about__"):
    _bcrypt.__about__ = SimpleNamespace(
        __version__=getattr(_bcrypt, "__version__", "unknown")
    )

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# auto_error=False: dasselbe Schema dient Pflicht- UND Optional-Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
