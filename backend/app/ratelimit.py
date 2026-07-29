"""Rate-Limiting pro Client — gestuft nach anonym/angemeldet.

Anonyme Requests werden pro IP limitiert (hinter Cloudflare aus
CF-Connecting-IP, lokal request.client.host). Angemeldete Requests werden
pro Nutzer-ID limitiert und bekommen das höhere Limit.

Bewusster Trade-off: Die Tier-Entscheidung liest nur das signierte JWT
(kein DB-Roundtrip pro Request). Ein deaktivierter Nutzer behält damit bis
zum Token-Ablauf das höhere Rate-Tier — die Größen-Limits und alle
Konto-Endpoints prüfen dagegen immer gegen die Datenbank.
"""

from contextvars import ContextVar

from slowapi import Limiter
from starlette.requests import Request

from app.config import settings
from app.security import decode_token

# Tier des laufenden Requests — von RateTierMiddleware VOR slowapi gesetzt,
# weil slowapi Callable-Limits mit key-Parameter im Middleware-Modus nicht
# unterstützt (LimitGroup.request bleibt None).
_tier: ContextVar[str] = ContextVar("rate_tier", default="anon")


def client_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    return request.client.host if request.client else "unknown"


def _sub_from_auth_header(auth: str) -> str | None:
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:])
        if payload and payload.get("sub"):
            return str(payload["sub"])
    return None


def tier_key(request: Request) -> str:
    sub = _sub_from_auth_header(request.headers.get("Authorization", ""))
    if sub:
        return f"user:{sub}"
    return client_ip(request)


def dynamic_limits() -> str:
    if _tier.get() == "authed":
        return settings.rate_limit_authed
    return settings.rate_limit_default


class RateTierMiddleware:
    """Pure-ASGI-Middleware: entscheidet das Rate-Tier aus dem signierten JWT
    (kein DB-Zugriff) und stellt es slowapi per ContextVar bereit."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        auth = ""
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth = value.decode("latin-1")
                break
        tier = "authed" if _sub_from_auth_header(auth) else "anon"
        token = _tier.set(tier)
        try:
            await self.app(scope, receive, send)
        finally:
            _tier.reset(token)


limiter = Limiter(key_func=tier_key, default_limits=[dynamic_limits])
