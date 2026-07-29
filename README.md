# PDF-Editor-App

Eigenständige, öffentlich nutzbare Web-App mit PDF-, Word- und Excel-Werkzeugen —
**kostenlos, ohne Registrierung, ohne Datenspeicherung**. Alle Verarbeitungen laufen
vollständig im Arbeitsspeicher des Servers; es gibt keine Datenbank und keine
persistente Ablage von Nutzerdateien.

Konzept, Phasenplan und Datenschutz-Details: [KONZEPT.md](./KONZEPT.md)

## Quickstart (lokal)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/                       # Smoke-Tests
uvicorn app.main:app --port 8000    # API auf :8000, Docs unter /docs

# Frontend (zweites Terminal)
cd frontend
npm install
npm run dev                         # http://localhost:3010 (Proxy /api → :8000)
```

Für OCR und Word→PDF müssen lokal `tesseract-ocr` (mit `-deu`/`-eng`) und
`libreoffice-writer` installiert sein — ohne sie degradieren die betroffenen
Werkzeuge sichtbar (Feature-Flags in `/api/health`).

## Docker (Gesamtstack)

```bash
docker compose up --build
# → http://localhost:8080 (nginx: Frontend + Proxy /api → Backend)
```

## Konfiguration

Alle Einstellungen über Umgebungsvariablen mit Präfix `PDFAPP_` — siehe
[.env.example](./.env.example). Wichtig:

| Variable | Default | Zweck |
|---|---|---|
| `PDFAPP_MAX_FILE_SIZE_MB` | 50 | Limit pro Datei |
| `PDFAPP_MAX_TOTAL_SIZE_MB` | 200 | Limit pro Multi-Datei-Operation |
| `PDFAPP_RATE_LIMIT_DEFAULT` | `30/minute;500/day` | Rate-Limit pro IP (alle Endpoints) |
| `PDFAPP_RATE_LIMIT_MAIL` | `5/hour` | Rate-Limit Mailversand |
| `PDFAPP_SMTP_HOST` | *(leer)* | leer = Mailversand deaktiviert (503) |

## Deployment Hetzner + Cloudflare-Tunnel (`pdf.flowaudit.de`)

Analog zum Muster in `docs/HETZNER_DEPLOY.md` des audit_designer-Repos:

1. **Ablage auf dem Host**: `compose.yaml` nach `/opt/pdf-editor/`, Env-Datei nach
   `/etc/pdf-editor/env` (root:root, 0600).
2. **Cloudflare-Tunnel**: im Cloudflare-Dashboard einen (eigenen) Tunnel anlegen und
   das Hostname-Mapping `pdf.flowaudit.de → http://frontend:80` konfigurieren;
   `TUNNEL_TOKEN` in die Env-Datei.
3. **Start**: `cd /opt/pdf-editor && docker compose --env-file /etc/pdf-editor/env --profile prod up -d --build`
4. **Verifikation**: `curl -s https://pdf.flowaudit.de/api/health` → `"status": "ok"`.

Später (nach Extraktion in ein eigenes Repo): GitHub-Actions-Build nach ghcr
(`audit_designer-pdf-{backend,frontend}`) und `docker compose pull` statt `--build`.

## Herkunft des Codes

Backend-Services und Tool-Komponenten sind Kopien aus dem audit_designer-Repo
(`backend/app/services/pdf_{tools,editor}_service.py`,
`frontend/src/components/vpai/pdf-tools/`), entkoppelt von Auth, Stores und
Feature-Flags. Die App ist bewusst import-frei gegenüber audit_designer und kann
als Ganzes in ein eigenes Repository verschoben werden.
