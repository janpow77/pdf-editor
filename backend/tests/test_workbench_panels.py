"""Vertragstest: Werkbank-Panels dürfen nur auf echte Backend-Routen zeigen.

Hintergrund: Die Panel-Spezifikationen in frontend/src/lib/workbenchPanels.ts
nennen ihre Endpunkte als Zeichenketten. Ein Tippfehler oder ein falscher
Router-Prefix fällt sonst erst in der Produktion als 404 auf — so geschehen
bei Seitenzahlen, Kopf-/Fußzeile und Bates (2026-08-05).
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_workbench_panel_endpoints_exist():
    spec = Path(__file__).resolve().parents[2] / "frontend/src/lib/workbenchPanels.ts"
    source = spec.read_text(encoding="utf-8")
    endpoints = set(re.findall(r"endpoint: '([^']+)'", source))
    assert len(endpoints) >= 10, "verdächtig wenige Panel-Endpunkte gefunden"

    # Über das OpenAPI-Schema statt app.routes: neuere FastAPI-Versionen hängen
    # Router verzögert ein (_IncludedRouter) — die Pfade existieren erst nach
    # dem App-Start, den der TestClient auslöst.
    with TestClient(app) as client:
        paths = set(client.get("/openapi.json").json()["paths"])
    missing = sorted(endpoint for endpoint in endpoints if endpoint not in paths)
    assert not missing, f"Panel-Endpunkte ohne Backend-Route: {missing}"
