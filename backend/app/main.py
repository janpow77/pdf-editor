"""PDF-Editor-App — öffentliches, zustandsloses Backend.

Alle Verarbeitungen laufen vollständig im Arbeitsspeicher; es gibt keine
Datenbank und keine persistente Ablage von Nutzerdateien. Schutz vor
Missbrauch über Rate-Limiting pro IP und Dateigrößen-Limits (app/config.py).
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api import mail, pdf_editor, pdf_tools
from app.config import settings
from app.ratelimit import limiter

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="PDF-Editor",
    description="Kostenlose PDF-, Word- und Excel-Werkzeuge — ohne Datenspeicherung.",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "detail": (
                "Zu viele Anfragen — bitte kurz warten und erneut versuchen. "
                f"(Limit: {exc.detail})"
            )
        },
    )


@app.get("/api/health")
async def health():
    from app.services.pdf_tools_service import get_pdf_tools

    return {"status": "ok", "features": get_pdf_tools().check_features()}


app.include_router(pdf_tools.router, prefix="/api")
app.include_router(pdf_editor.router, prefix="/api")
app.include_router(mail.router, prefix="/api")
