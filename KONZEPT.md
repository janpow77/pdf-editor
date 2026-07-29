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

### Phase 1 — umgesetzt

| Bereich | Werkzeuge |
|---|---|
| PDF | Zusammenführen, Teilen, Rotieren, PDF→Bilder, Komprimieren, Wasserzeichen, Bilder→PDF, Seiten ordnen, Vergleich, OCR, Metadaten, **Schützen/Entsperren (AES-256, pikepdf)**, **PDF→Word**, **PDF→Excel (tabula, Java im Image)** |
| Word | Word→PDF, Word verbinden, Word-Vergleich, Word-Metadaten |
| Excel | Excel-Metadaten |
| Auslieferung | Direkt-Download je Werkzeug, **ZIP-Download** aller Sitzungs-Ergebnisse (client-seitig via JSZip), **Mailversand** der Ergebnisse |
| Konten | **Optionale Anmeldung** (offene Registrierung, erster Admin per Env-Seed), höhere Limits für Angemeldete (100/400 MB, 60/min), gespeicherte Werkzeug-Einstellungen, Konto-Selbstlöschung (Art. 17 DSGVO), Admin-Bereich (Nutzer verwalten, Konfiguration einsehen) |

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

### Optionale Konten — vorgezogen und umgesetzt

Ursprünglich Phase 3, auf Nutzerwunsch vorgezogen. Grundsätze (alle eingehalten):

- Anonyme Nutzung bleibt vollwertig — kein Feature-Gating hinter Login; ohne
  erreichbare Datenbank läuft die App automatisch rein anonym weiter
  (`/api/health` → `accounts: false`).
- Ausdrückliche Einwilligung per Pflicht-Checkbox bei der Registrierung; die
  Datenschutzerklärung ist differenziert (ohne Konto wird nichts gespeichert; mit
  Konto nur E-Mail, bcrypt-Hash, Einstellungen, Zeitstempel).
- Datensparsames Modell: keine IP-Speicherung, kein Klarnamen-Zwang.
- Anonyme Tool-Requests öffnen keine DB-Session (tokenloser Pfad DB-frei).
- Sicherheit: Passwort-Policy (12+ Zeichen, gemischt), Lockout nach 10
  Fehlversuchen (30 min), identische Login-Fehlermeldung gegen User-Enumeration,
  Selbstschutz im Admin-Bereich (letzter aktiver Admin nicht entfernbar).

### Hardening-Backlog (offen)

- Alembic-Migrationen statt `create_all` (nötig ab der ersten Schema-Änderung).
- E-Mail-Verifikation bei Registrierung, Passwort-Reset per Mail.
- Refresh-Tokens / kürzere Access-Token-Laufzeit.
- Turnstile/Captcha für Registrierung und Mailversand, falls Missbrauch auftritt.

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

## 9. Soll-/Zielkriterien & Prüfverfahren

Abnahme = alle P0-Kriterien erfüllt. Automatisierte Kriterien sind in
`backend/tests/` abgedeckt (`pytest tests/ -q`), Rest per manueller Prüfung.

| Nr. | Kriterium (Sollwert) | Prüfverfahren | Status |
|---|---|---|---|
| F1 | Registrieren → sofort nutzbar; Login liefert JWT; `/api/auth/me` gibt Profil | `test_auth.py` + Browser | ✅ automatisiert |
| F2 | Passwort-Policy: <12 Zeichen o. fehlende Zeichenklassen → 422 | `test_auth.py` | ✅ automatisiert |
| F3 | Lockout: 10 Fehlversuche → 30 min Sperre (423), Erfolg resettet | `test_auth.py` | ✅ automatisiert |
| F4 | Admin-Seed idempotent (kein Duplikat bei Neustart) | `test_auth.py` + `compose restart` | ✅ automatisiert |
| F5 | Admin: listen/deaktivieren/entsperren/löschen; letzter Admin geschützt (400) | `test_auth.py` + `/admin` | ✅ automatisiert |
| F6 | Rollentrennung: `/api/admin/*` ohne Login 401, als USER 403 | `test_auth.py` | ✅ automatisiert |
| F7 | Gestufte Limits: anonym 50/200 MB + 30/min, angemeldet 100/400 MB + 60/min | `test_auth.py` (Größe) + manuell 31 Requests → 429 | ✅ Größe automatisiert |
| F8 | Preferences je Konto, Tools übernehmen Defaults, >16 KB → 413 | `test_auth.py` + manuell OCR-Default | ✅ automatisiert |
| F9 | `DELETE /me` mit Passwort → 204, Login danach 401 | `test_auth.py` | ✅ automatisiert |
| F10 | Schützen: fitz `needs_pass=True`; Entsperren korrekt; falsches Passwort 400 | `test_pdf_protect.py` | ✅ automatisiert |
| F11 | PDF→Word valides DOCX; `/api/pdf-convert/status` im Container `tabula: true` | `test_pdf_converter.py` + Container-curl | ✅ automatisiert |
| D1 | Keine Datei-Persistenz nach Verarbeitung | Dateisystem-Diff vor/nach Upload-Serie | manuell |
| D2 | users-Tabelle nur E-Mail/Hash/Rolle/Flags/Prefs/Zeitstempel — keine IP | `\d users` + Code-Review models.py | ✅ per Modell |
| D3 | Mail-Adresse nie in Logs (Erfolg + Fehlerpfade) | `docker compose logs \| grep "@"` nach Testversand | manuell |
| D4 | Anonym ohne DB-Zugriff; App läuft bei gestopptem Postgres weiter | `compose stop db` → Tools ok, health `accounts: false` | ✅ per Lifespan-Fallback |
| D5 | Registrierung nur mit Pflicht-Checkbox + Datenschutz-Link | Browser-Prüfung RegisterView | ✅ umgesetzt |
| D6 | Hinweis konsistent (Banner/Badge/Footer + Konto-Absatz) | Review der vier Hinweis-Stellen | ✅ umgesetzt |
| S1 | Anonyme Regression: Tools ohne Login byte-identisch | Smoke-Tests unverändert grün | ✅ automatisiert |
| S2 | Alle neuen Endpoints mit mindestens einem Test, Suite grün | `pytest tests/ -q` → 0 failed | ✅ (20 Tests) |
| S3 | `npm run type-check` + `build` fehlerfrei | CI-Befehle | ✅ |
| S4 | Compose healthy; Konten überleben Neustart (pgdata) | `compose ps` + Konto → restart → Login | manuell |
| SEC1 | SECRET_KEY + DB-Passwort Pflicht (`:?`), keine Secrets im Repo | `docker compose config` ohne .env → Fehler | ✅ umgesetzt |
| SEC2 | Ungültiger Token → 401, kein stilles Anonym-Downgrade | `test_auth.py` | ✅ automatisiert |
| SEC3 | Identische Login-Fehlertexte (keine User-Enumeration) | `test_auth.py` | ✅ automatisiert |

## 10. Roadmap

| Phase | Inhalt | Status |
|---|---|---|
| 1 | Scaffold: 16 Werkzeuge, Landing + Hinweis, ZIP-Download, Mailversand, Rate-Limiting, Docker, Impressum/Datenschutz-Gerüst | ✅ |
| 1.5 | Schützen/Entsperren, PDF→Word/Excel, optionale Konten (Nutzer + Admin), gestufte Limits, Postgres | ✅ |
| 1.6 | Anbieterdaten eintragen, SMTP-Zugang konfigurieren, Tunnel anlegen, Erst-Deploy | offen |
| 1.7 | Repo-Extraktion + CI (ghcr-Images, Smoke-Test-Gate) | offen |
| 2 | Visueller PDF-Editor (nach Defekt-Behebung, siehe Abschnitt 7), asynchrones OCR/Compare | offen |
| 3 | Hardening-Backlog (Alembic, E-Mail-Verifikation, Passwort-Reset, Turnstile) | offen |
