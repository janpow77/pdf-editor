# PDF-Editor-App

Eigenständige, öffentlich nutzbare Web-App mit PDF-, Word- und Excel-Werkzeugen —
**kostenlos, ohne Registrierungszwang, ohne Datenspeicherung**. Alle Datei-Verarbeitungen
laufen vollständig im Arbeitsspeicher des Servers; Nutzerdateien werden nie persistiert.

Optional gibt es **Benutzerkonten** (offene Registrierung): angemeldete Nutzer bekommen
höhere Limits (100 MB/Datei statt 50) und gespeicherte Werkzeug-Einstellungen. Der erste
Admin wird per Env-Variablen (`PDFAPP_ADMIN_EMAIL`/`PDFAPP_ADMIN_PASSWORD`) beim Start
angelegt; Admin-Bereich unter `/admin`. Konten liegen in PostgreSQL — ohne erreichbare
Datenbank läuft die App automatisch im rein anonymen Modus weiter.

Im Admin-Bereich lässt sich außerdem pro Werkzeug festlegen, ob es **nur angemeldeten
Nutzern** offensteht (Auslieferungszustand: nichts beschränkt). Beschränkte Werkzeuge
erscheinen für anonyme Besucher ausgegraut mit Hinweis auf die Anmeldung und werden
serverseitig mit HTTP 403 abgewiesen — nicht nur in der Oberfläche versteckt.

Konzept, Phasenplan, Soll-Kriterien und Datenschutz-Details: [KONZEPT.md](./KONZEPT.md)

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

Für OCR und Office→PDF müssen lokal `tesseract-ocr` (Sprachpakete `-deu`, `-eng`,
optional `-fra/-ita/-spa/-nld/-pol`) und `libreoffice-writer`/`-calc`/`-impress`
installiert sein — ohne sie degradieren die betroffenen Werkzeuge sichtbar
(Feature-Flags in `/api/health`).

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
| `PDFAPP_SECRET_KEY` | — | Pflicht (JWT-Signatur), `openssl rand -hex 32` |
| `PDFAPP_DB_PASSWORD` | — | Pflicht (Postgres-Passwort im Compose) |
| `PDFAPP_ADMIN_EMAIL` / `_PASSWORD` | *(leer)* | Admin-Seed beim ersten Start (idempotent) |
| `PDFAPP_MAX_FILE_SIZE_MB` | 50 | Limit pro Datei (anonym) |
| `PDFAPP_MAX_TOTAL_SIZE_MB` | 200 | Limit pro Multi-Datei-Operation (anonym) |
| `PDFAPP_MAX_FILE_SIZE_MB_AUTHED` | 100 | Limit pro Datei (angemeldet) |
| `PDFAPP_MAX_TOTAL_SIZE_MB_AUTHED` | 400 | Limit pro Operation (angemeldet) |
| `PDFAPP_RATE_LIMIT_DEFAULT` | `30/minute;500/day` | Rate-Limit pro IP (anonym) |
| `PDFAPP_RATE_LIMIT_AUTHED` | `60/minute;2000/day` | Rate-Limit pro Nutzer (angemeldet) |
| `PDFAPP_RATE_LIMIT_MAIL` | `5/hour` | Rate-Limit Mailversand |
| `PDFAPP_SMTP_HOST` | *(leer)* | leer = Mailversand deaktiviert (503) |
| `PDFAPP_LLM_URL` | *(leer)* | OpenAI-kompatibler Endpoint der EIGENEN Infrastruktur (z.B. ai-router) — leer = KI-Funktionen deaktiviert, keine Cloud |
| `PDFAPP_LLM_MODEL` | `qwen3.5:35b` | Modellname für die KI-Funktionen |

## Datenbank-Migrationen (Alembic)

Frische Datenbanken initialisiert der Backend-Start selbst (`create_all` +
Admin-Seed). Für Schema-Änderungen an bestehenden Datenbanken:

```bash
cd backend
alembic upgrade head        # nutzt PDFAPP_DATABASE_URL aus der Umgebung
alembic revision -m "..."   # neue Migration anlegen
```

Die Initial-Migration `0001` ist idempotent und läuft auch auf per
`create_all` erzeugten Beständen sauber durch (zieht fehlende Spalten nach).

## Betrieb

Vollständiges Handbuch für NUC-Inbetriebnahme, Extraktion in ein eigenes
Repository, Hetzner-Deployment und den laufenden Betrieb: **[BETRIEB.md](BETRIEB.md)**.

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
