"""Rate-Limiting pro Client — gestuft nach anonym/angemeldet.

Anonyme Requests werden pro IP limitiert (hinter Cloudflare aus
CF-Connecting-IP, lokal request.client.host), angemeldete pro Nutzer-ID mit
höherem Limit.

Die Default-Limits werden in ``RateTierMiddleware`` selbst geprüft (mit der
``limits``-Bibliothek), NICHT über ``SlowAPIMiddleware``: slowapi findet in
aktuellen FastAPI-Versionen die Handler von per ``include_router``
eingebundenen Routen nicht (``_IncludedRouter``-Wrapper in ``app.routes``)
und würde alle Tool-Endpoints stillschweigend vom Limit ausnehmen. Der
slowapi-``limiter`` bleibt für die strengeren per-Route-Limits
(Login/Registrierung/Mailversand) im Einsatz — dessen Dekorator wertet
unabhängig von der Middleware aus.

Bewusster Trade-off: Die Tier-Entscheidung liest nur das signierte JWT
(kein DB-Roundtrip pro Request). Ein deaktivierter Nutzer behält damit bis
zum Token-Ablauf das höhere Rate-Tier — Größen-Limits und Konto-Endpoints
prüfen dagegen immer gegen die Datenbank.
"""

import json

from limits import parse_many
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter
from slowapi import Limiter
from starlette.requests import Request

from app.config import settings
from app.security import decode_token

# Pfade ohne Default-Limit (Monitoring)
EXEMPT_PATHS = {"/api/health"}


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


# slowapi-Limiter NUR für die strengeren per-Route-Dekoratoren
# (auth.login/register, mail.send) — keine default_limits, siehe Modul-Doku.
limiter = Limiter(key_func=tier_key)

_storage = MemoryStorage()
_checker = MovingWindowRateLimiter(_storage)


def _limit_items(tier: str):
    raw = (
        settings.rate_limit_authed if tier == "authed" else settings.rate_limit_default
    )
    return parse_many(raw)


class RateTierMiddleware:
    """Pure-ASGI-Middleware: entscheidet das Tier aus dem signierten JWT
    (kein DB-Zugriff) und erzwingt die gestuften Default-Limits."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return
        if not limiter.enabled:  # gemeinsamer Kill-Switch (Tests)
            await self.app(scope, receive, send)
            return

        auth = ""
        client_host = scope.get("client")
        cf_ip = None
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                auth = value.decode("latin-1")
            elif name == b"cf-connecting-ip":
                cf_ip = value.decode("latin-1")

        sub = _sub_from_auth_header(auth)
        if sub:
            tier, key = "authed", f"user:{sub}"
        else:
            tier = "anon"
            key = cf_ip or (client_host[0] if client_host else "unknown")

        blocked = None
        for item in _limit_items(tier):
            if not _checker.hit(item, key):
                blocked = item
                break

        if blocked is not None:
            body = json.dumps(
                {
                    "detail": (
                        "Zu viele Anfragen — bitte kurz warten und erneut versuchen. "
                        f"(Limit: {blocked})"
                    )
                }
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
