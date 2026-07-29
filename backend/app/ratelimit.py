"""Rate-Limiting pro Client-IP.

Hinter dem Cloudflare-Tunnel steht die echte Client-IP im Header
CF-Connecting-IP; lokal fällt der Key auf request.client.host zurück.
"""

from slowapi import Limiter
from starlette.requests import Request

from app.config import settings


def client_ip(request: Request) -> str:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=client_ip,
    default_limits=settings.rate_limit_default.split(";"),
)
