# PDF-Editor-App — Konzept

**Stand: 2026-07-29** · Eigenständige, öffentlich nutzbare Web-App · Scaffold in diesem Ordner

---

## 1. Ziel & Abgrenzung

Eine eigenständige Web-App, die den bewährten PDF-/Word-/Excel-Werkzeugkasten aus
audit_designer als **kostenloses, öffentliches Angebot** verfügbar macht — ohne Login,
ohne Registrierung, ohne Datenspeicherung. Die App ist ein separates Produkt mit eigenem
Deployment (Subdomain `pdf.flowaudit.de`) und wird nach der Scaffold-Phase in ein
eigenes Repository extrahiert. Sie hat **keine Laufzeit-Abhängigkeit** zu audit_designer:
aller Code ist kopiert und entkoppelt (kein Auth, keine Stores, keine Feature-Flags).

## 2. Zielgruppe & Nutzungsversprechen

Zielgruppe sind alle, die schnell und ohne Anmeldung PDF-/Office-Dateien bearbeiten
wollen. Das Nutzungsversprechen ist zentraler Produktkern und wird prominent
kommuniziert (Landing-Page-Hero, Header-Badge, Banner, Footer, Datenschutzseite):

> **Kostenlos & ohne Datenspeicherung** — Ihre Dateien werden ausschließlich für die
> Dauer der Verarbeitung im Arbeitsspeicher gehalten und danach sofort verworfen.
> Keine Registrierung erforderlich.

Das Versprechen ist technisch gedeckt: Alle Services öffnen Uploads als In-Memory-Stream
(`fitz.open(stream=...)`), Ergebnisse gehen als `StreamingResponse` direkt zurück.
Es gibt keine Datenbank, kein Upload-Verzeichnis, keine Ergebnis-Ablage. Einzige
Ausnahme ist ein automatisch gelöschtes `TemporaryDirectory` während der
LibreOffice-Konvertierung (Word→PDF).

## 3. Funktionsumfang

### Phase 1 — im Scaffold umgesetzt

| Bereich | Werkzeuge |
|---|---|
| PDF | Zusammenführen, Teilen, Rotieren, PDF→Bilder, Komprimieren, Wasserzeichen, Bilder→PDF, Seiten ordnen, Vergleich, OCR, Metadaten |
| Word | Word→PDF, Word verbinden, Word-Vergleich, Word-Metadaten |
| Excel | Excel-Metadaten |
| Auslieferung | Direkt-Download je Werkzeug, **ZIP-Download** aller Sitzungs-Ergebnisse (client-seitig via JSZip), **Mailversand** der Ergebnisse |

Die Ergebnisliste („Ergebnisse dieser Sitzung") existiert ausschließlich im Browser:
jede heruntergeladene Datei wird dort vorgemerkt und kann gebündelt als ZIP geladen
oder per Mail versendet werden. Ein Reload leert die Liste.

Das Backend stellt darüber hinaus bereits **alle** Editor-Endpoints bereit
(TOC, Annotationen, Schwärzung, Seitenzahlen, Kopf-/Fußzeile, Text-Suche/-Ersetzung,
Flatten) — nur die visuelle Oberfläche dafür fehlt noch (Phase 2).

### Phase 2 — visueller PDF-Editor

Portierung von `PdfEditor.vue` (+ Toolbar, AnnotationPanel, TocEditor) aus
audit_designer. Vorher sind die bekannten Defekte der Vorlage zu beheben (siehe
Abschnitt 7). Zusätzlich: pdf.js-Rendering (`pdfjs-dist` explizit als Dependency),
asynchrones OCR/Compare für große Dateien.

### Phase 3 — optionaler Account

Optionales Benutzerkonto ausschließlich für Komfortfunktionen (z. B. gespeicherte
Werkzeug-Voreinstellungen). Grundsätze:

- Anonyme Nutzung bleibt vollwertig — kein Feature-Gating hinter Login.
- Gesonderte, ausdrückliche Einwilligung; die Datenschutzerklärung wird differenziert
  („ohne Konto wird nichts gespeichert; mit Konto nur …").
- Erst ab dieser Phase wird ein Datenbank-Container Teil des Stacks.
- Ergänzend: Turnstile/Captcha für den Mailversand, falls Missbrauch auftritt.

## 4. Architektur

```
Browser (Vue 3 + Tailwind, deutsch)
  ├─ Tool-Komponenten (Kopien aus audit_designer, Import-Swap auf lib/api.ts)
  ├─ lib/results.ts   Sitzungs-Ergebnisse (nur RAM im Browser)
  ├─ lib/zip.ts       ZIP-Bündelung client-seitig (JSZip)
  └─ fetch /api/*  ──────────────┐
                                 ▼
nginx (static + Proxy /api, client_max_body_size 210m)
                                 ▼
FastAPI-Backend (zustandslos, keine DB)
  ├─ api/pdf_tools.py   Kopie + Auth-Strip (20 Endpoints)
  ├─ api/pdf_editor.py  Kopie + Auth-Strip (12 Endpoints)
  ├─ api/mail.py        Mailversand (aiosmtplib, transient)
  ├─ ratelimit.py       slowapi pro IP (CF-Connecting-IP)
  └─ services/          1:1-Kopien (PyMuPDF, Pillow, python-docx,
                        openpyxl, pytesseract, LibreOffice headless)
```

**Kopie-Strategie**: Code wird kopiert, nicht importiert. Die beiden Service-Dateien
sind unverändert übernommen (einzige interne Abhängigkeit: `PdfToolResult`), die
API-Router mechanisch von `get_current_user`/`User` befreit, die Vue-Komponenten per
Import-Swap von `useAuthFetch` (Bearer-Token) auf das tokenfreie `lib/api.ts` umgestellt.
Dadurch bleibt ein späterer Diff gegen die Vorlage trivial und die Extraktion in ein
eigenes Repo ist ein `git mv`.

## 5. Datenschutz & Nutzerhinweis

| Datum | Verarbeitung |
|---|---|
| Hochgeladene Dateien | Nur im RAM während des Requests; keine Ablage, kein Log der Inhalte |
| Ergebnis-Dateien | Streaming-Response an den Browser; Sitzungs-Liste nur client-seitig |
| E-Mail-Adresse (Mailversand) | Ausschließlich transient für den einen Versand; wird weder persistiert noch geloggt — auch Fehlerpfade geben bewusst keine SMTP-Details (können die Adresse enthalten) weiter |
| IP-Adresse | Kurzzeitig im RAM für Rate-Limiting; TLS-Terminierung und Auslieferung über Cloudflare |
| Cookies/Tracking | Keine Analyse-Cookies, kein Tracking |

Rechtliches: Impressum (§ 5 DDG) und Datenschutzerklärung sind als Seiten angelegt;
die Anbieterdaten sind vor Veröffentlichung einzutragen (TODO-Marker in
`ImpressumView.vue` / `DatenschutzView.vue`). Formulierungen für den optionalen
Account (Phase 3) sind bereits differenziert vorbereitet.

## 6. Missbrauchsschutz

| Maßnahme | Umsetzung |
|---|---|
| Rate-Limiting pro IP | slowapi global: `30/minute; 500/day` (env-konfigurierbar); Mail separat `5/hour`. IP aus `CF-Connecting-IP`, Fallback `request.client.host` |
| Dateigrößen | 50 MB/Datei, 200 MB/Operation (bewusst unter den internen 100/500 MB) |
| Mail-Anhänge | 20 MB gesamt, sonst Verweis auf ZIP-Download |
| Timeouts | 5-Minuten-Timeout client-seitig; nginx `proxy_read_timeout 300s` |
| Eskalation (bei Bedarf) | Cloudflare-WAF/Bot-Fight-Mode; Phase 3: Turnstile vor Mailversand |

## 7. Bekannte Defekte der Vorlage (vor Phase-2-Port zu beheben)

Aus `docs/reviews/funktions_prozessreview_2026-07-11.md` (Abschnitt 4.6) und eigener
Analyse — betreffen den **visuellen Editor**, nicht die in Phase 1 übernommenen Tools:

1. `PdfEditor.vue` umgeht an ~9 Stellen das Composable und ruft `fetch('/api/pdf-editor/…')` roh auf (Befund P1-10).
2. `usePdfEditor.ts` ruft `POST /api/pdf-editor/export` auf — der Endpoint existiert nicht (toter Pfad). Im Scaffold wurde das Composable deshalb gar nicht erst übernommen; OCR/Compare rufen `apiPost` direkt.
3. Text-Ersetzen-Bug (Replace), fehlende Tests für echte Schwärzung (Redaction), fehlende Passwort-/Signatur-/PDF-A-Erkennung.
4. OCR/Compare synchron — für große Dateien asynchron machen (SSE oder Polling).

## 8. Deployment

- **Stack**: `docker-compose.yaml` mit `backend` (python:3.12-slim + tesseract + LibreOffice, non-root, Healthcheck `/api/health`), `frontend` (Node-Build → nginx) und `cloudflared` (nur compose-Profil `prod`).
- **Hetzner**: Ablage nach dem Muster von `docs/HETZNER_DEPLOY.md` — `/opt/pdf-editor/compose.yaml`, Secrets in `/etc/pdf-editor/env` (0600). Eigener Cloudflare-Tunnel bzw. zusätzliches Hostname-Mapping `pdf.flowaudit.de → http://frontend:80`.
- **Später** (nach Repo-Extraktion): GitHub-Actions-Build nach ghcr (`…-pdf-backend`/`…-pdf-frontend`), Deploy per `docker compose pull && up -d`, Rollback über Image-Tag wie im Hauptprojekt.

## 9. Roadmap

| Phase | Inhalt | Status |
|---|---|---|
| 1 | Scaffold: 16 Werkzeuge, Landing + Hinweis, ZIP-Download, Mailversand, Rate-Limiting, Docker, Impressum/Datenschutz-Gerüst | ✅ in diesem Ordner |
| 1.1 | Anbieterdaten eintragen, SMTP-Zugang konfigurieren, Tunnel anlegen, Erst-Deploy | offen |
| 1.2 | Repo-Extraktion + CI (ghcr-Images, Smoke-Test-Gate) | offen |
| 2 | Visueller PDF-Editor (nach Defekt-Behebung, siehe Abschnitt 7), asynchrones OCR/Compare | offen |
| 3 | Optionaler Account (Komfort, gesonderte Einwilligung), ggf. Turnstile | offen |
