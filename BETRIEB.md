# Betrieb der PDF-Editor-App

Handbuch für den Weg von der Entwicklung bis zum laufenden Dienst: erst auf der
NUC, dann als eigenes Repository, dann auf dem Hetzner-Server. Danach die
Pflichten, die ein Dauerbetrieb mit sich bringt.

**Stand: 2026-08-01** · Branch `claude/pdf-editor-app-planning-fvkauh`, noch
nicht nach `main` gemergt.

> **Was hier nicht steht, ist genauso wichtig:** Die Befehle in diesem Dokument
> sind aus `docker-compose.yaml`, `.env.example` und dem vorhandenen
> Hetzner-Runbook abgeleitet und teilweise in einer Linux-Umgebung erprobt. Auf
> Ihrer NUC und dem Hetzner-Host sind sie **nicht** gelaufen. Rechnen Sie beim
> ersten Durchgang mit Abweichungen; die wahrscheinlichsten stehen jeweils
> unter „Wenn es klemmt".

---

## Teil A — Auf der NUC zum Laufen bringen

### A1. Verzeichnis und Quellcode

```bash
sudo mkdir -p /opt/pdf-editor && sudo chown $USER:$USER /opt/pdf-editor
cd /opt/pdf-editor

git clone -b claude/pdf-editor-app-planning-fvkauh \
  https://github.com/janpow77/audit_designer.git .

cd pdf-editor-app
```

Wer das Repo auf der NUC schon hat, spart sich den zweiten Klon:

```bash
cd ~/audit_designer
git fetch origin claude/pdf-editor-app-planning-fvkauh
git worktree add /opt/pdf-editor claude/pdf-editor-app-planning-fvkauh
cd /opt/pdf-editor/pdf-editor-app
```

### A2. Konfiguration

Zwei Werte sind Pflicht — ohne sie bricht Compose ab. Das ist Absicht: Ein
Dienst mit vorhersagbarem Signaturschlüssel wäre schlimmer als einer, der gar
nicht startet.

```bash
cp .env.example .env
{
  echo "COMPOSE_PROJECT_NAME=pdfapp"
  echo "PDFAPP_SECRET_KEY=$(openssl rand -hex 32)"
  echo "PDFAPP_DB_PASSWORD=$(openssl rand -hex 24)"
  echo "PDFAPP_ADMIN_EMAIL=<ihre-adresse>"
  echo "PDFAPP_ADMIN_PASSWORD=$(openssl rand -base64 18)"
  echo "PDFAPP_SOURCE_URL=https://github.com/janpow77/audit_designer"
} >> .env
chmod 600 .env
grep PDFAPP_ADMIN_PASSWORD .env      # einmalig notieren
```

`COMPOSE_PROJECT_NAME=pdfapp` trennt den Stack vom laufenden audit_designer.
Ohne die Angabe leitet Compose den Namen aus dem Verzeichnis ab — und
gleichnamige Volumes zweier Projekte sind eine unangenehme Fehlerquelle.

Die `.env` ist per `.gitignore` ausgeschlossen und darf nie in einen Commit
geraten.

### A3. Starten

```bash
ss -ltn | grep -w 8080 || echo "Port 8080 frei"
docker compose up -d --build
```

Der erste Build dauert 10–20 Minuten: LibreOffice, Ghostscript und Tesseract
wandern ins Backend-Image. Die Ports des audit_designer-Stacks (8003, 3002,
5433, 6381, 5555, 8889, 8010) werden nicht berührt; die App lauscht auf
`127.0.0.1:8080`.

### A4. Nachsehen, ob es wirklich läuft

```bash
docker compose ps                                    # alle healthy?
curl -s localhost:8080/api/health | jq '{status, accounts}'
curl -s localhost:8080/api/licenses | jq '.source_disclosure_required'
```

`accounts: true` heißt: Datenbank steht, Admin-Konto angelegt.

Danach ein Handgriff, den keine Automatik ersetzt — im Browser über
`http://localhost:8080` (bzw. per SSH-Weiterleitung):

1. Eine PDF hochladen, **Text bearbeiten** öffnen.
2. Bleibt die Seitenvorschau leer, fehlt die `.mjs`-Regel in der
   nginx-Konfiguration — dann läuft ein Stand vor dem 2026-08-01.
3. Eine Zeile ändern, anwenden, herunterladen, im Ergebnis nachsehen.

### A5. Wenn es klemmt

| Beobachtung | Ursache | Abhilfe |
|---|---|---|
| `PDFAPP_SECRET_KEY muss gesetzt sein` | `.env` nicht gelesen | Aus dem Ordner mit der `docker-compose.yaml` starten, oder `--env-file` angeben |
| Backend `unhealthy`, Logs zeigen `OperationalError` | Datenbank noch nicht bereit | Normal beim ersten Start; `docker compose logs -f db` beobachten |
| Seitenvorschau bleibt leer | `.mjs` wird als `application/octet-stream` ausgeliefert | Stand aktualisieren (`git pull`), Frontend neu bauen |
| `accounts: false` | Kein `PDFAPP_SECRET_KEY` oder DB nicht erreichbar | Beides prüfen; die App läuft bewusst anonym weiter |
| Build bricht mit „no space left" ab | Image braucht ~3 GB | `docker system prune -a` |

---

## Teil B — In ein eigenes Repository überführen

Die App hat **keine** Laufzeitabhängigkeit zu audit_designer: kein Import, kein
gemeinsamer Pfad, kein geteiltes Compose. Geprüft durch eine Suche nach
Verweisen aus dem Ordner heraus — es gibt keine. Die Trennung ist damit ein
reiner Verwaltungsschritt.

### B1. Historie mitnehmen statt wegwerfen

`git subtree split` erzeugt einen Ast, der nur die Commits dieses
Unterverzeichnisses enthält — mit Datum, Autor und Begründung. Ein
Kopieren-und-neu-committen würde die gesamte Entwicklungsgeschichte
vernichten, und damit die Nachvollziehbarkeit, warum etwas so gebaut ist.

```bash
cd ~/audit_designer
git checkout claude/pdf-editor-app-planning-fvkauh
git pull

# Ast mit ausschließlich der Historie von pdf-editor-app/
git subtree split --prefix=pdf-editor-app -b pdf-editor-standalone

# Kontrolle: Liegt die Anwendung jetzt im Wurzelverzeichnis?
git ls-tree --name-only pdf-editor-standalone
# erwartet: .env.example  .gitignore  BETRIEB.md  KONZEPT.md
#           MODULKATALOG_2026.md  README.md  backend  docker-compose.yaml
#           frontend
```

Steht dort `pdf-editor-app`, hat der Split nicht gegriffen — dann stimmt der
`--prefix` nicht.

**Dieser Ablauf ist erprobt**, nicht nur beschrieben: Der Split wurde gegen den
Stand vom 2026-08-01 ausgeführt und ergab 154 Dateien in 22 Commits — Dateibestand
identisch zum Original, Historie bis zum ersten Commit erhalten. Im geklonten
Ergebnis liefen 160 pytest-Fälle grün, `npm ci`, `vue-tsc` und `vite build`
fehlerfrei.

### B2. Neues Repository befüllen

Auf GitHub ein leeres Repository anlegen (ohne README, ohne Lizenzdatei — sonst
gibt es beim ersten Push einen Konflikt), dann:

```bash
git push git@github.com:janpow77/pdf-editor.git pdf-editor-standalone:main
```

Danach frisch klonen und **prüfen, ob der Klon baubar ist** — das ist der
Schritt, der erfahrungsgemäß Überraschungen zutage fördert:

```bash
git clone git@github.com:janpow77/pdf-editor.git /tmp/pruefklon
cd /tmp/pruefklon
ls .gitignore docker-compose.yaml backend frontend    # alles da?
cd frontend && npm ci --no-audit && npm run type-check && npm run build
cd ../backend && python3 -m pytest tests/ -q
```

Genau hierfür trägt der Ordner eine **eigene `.gitignore`**: Die im
Wurzelverzeichnis von audit_designer wandert beim Split nicht mit. Ohne die
eigene Datei stünde das neue Repository ganz ohne Ignoriermuster da — beim
ersten `git add .` landeten `node_modules`, `dist` und im schlimmsten Fall die
`.env` in der Versionsverwaltung.

### B3. Was im alten Repository passiert

Erst wenn der Prüfklon baut und die Tests grün sind:

```bash
cd ~/audit_designer
git rm -r pdf-editor-app
git commit -m "chore: PDF-Editor-App in eigenes Repository ausgelagert"
```

Bis dahin bleibt der Ordner, wo er ist. Zwei Wochen Doppelablage sind billiger
als ein verlorener Stand.

Ebenfalls anzupassen, sonst laufen die Angaben ins Leere:

- `PDFAPP_SOURCE_URL` auf das neue Repository umstellen — sonst zeigt die
  Lizenzseite auf einen Quelltext, der die Anwendung nicht mehr enthält. Das
  ist keine Kosmetik: Die Angabe erfüllt eine Lizenzbedingung (siehe
  KONZEPT.md, Abschnitt Lizenzlage).
- Den Verweis auf `pdf-editor-app/` in der `CLAUDE.md` von audit_designer.

### B4. Bilder bauen lassen (optional, aber empfohlen)

Solange auf dem Zielserver gebaut wird, dauert jedes Deployment 10–20 Minuten
und belegt Plattenplatz für Build-Zwischenstände. Im neuen Repository als
`.github/workflows/image.yaml`:

```yaml
name: Images bauen und nach GHCR schieben

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        component: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: ./${{ matrix.component }}
          push: true
          tags: |
            ghcr.io/janpow77/pdf-editor-${{ matrix.component }}:latest
            ghcr.io/janpow77/pdf-editor-${{ matrix.component }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Auf dem Server dann `image:` statt `build:` in der Compose-Datei und
`docker compose pull` statt `--build`.

---

## Teil B2 — Freigaben vor der öffentlichen Erreichbarkeit

Technisch kann der Dienst sofort öffentlich laufen. Diese Punkte sollten aber
vorher geklärt sein — sie kosten wenig Zeit und sind hinterher unangenehm.

| Punkt | Stand |
|---|---|
| Impressum nach § 5 DDG (Name, Anschrift, Kontakt, Verantwortlicher) | ✅ ausgefüllt: Jan Riener, privat betriebenes Angebot |
| Verantwortlicher nach Art. 13 DSGVO, Betroffenenrechte, Aufsichtsbehörde | ✅ in der Datenschutzerklärung benannt |
| Erklärung zur Barrierefreiheit | ✅ vorhanden — **freiwillig**, siehe unten |
| Quelltext öffentlich erreichbar (AGPL § 13) | ⚠️ offen — hängt daran, ob das neue Repository öffentlich ist |
| Eigener Cloudflare-Tunnel für die Domain | ⚠️ offen |

**Zur Barrierefreiheit:** Die Pflicht aus § 12b BGG und der BITV 2.0 trifft
öffentliche Stellen. Bei einem privat betriebenen Angebot gilt sie **nicht**.
Die Erklärung unter `/barrierefreiheit` wird deshalb freiwillig abgegeben und
ist als solche gekennzeichnet. Sollte das Angebot später von einer Behörde
übernommen werden, wird die Pflicht wirksam — dann ist zusätzlich ein Test mit
Screenreader nötig, und die Werkzeugoberflächen müssen in die Prüfung
einbezogen werden. Beides steht in der Erklärung als offen benannt.

**Zur AGPL:** `PDFAPP_SOURCE_URL` muss auf ein **öffentlich erreichbares**
Repository zeigen. Wird das neue Repository privat angelegt, ist die
Lizenzbedingung ab dem Moment verletzt, in dem der Dienst öffentlich läuft.
Das ist eine Entscheidung, keine Einstellung.

**Zwischenweg:** Der Betrieb auf dem Hetzner-Server **ohne** öffentlichen
Tunnel — nur über Tailscale erreichbar — macht die beiden offenen Punkte
gegenstandslos, weil der Dienst nicht öffentlich ist. Der Schritt zur
Öffentlichkeit ist danach nur noch der Tunnel.

---

## Teil C — Auf den Hetzner-Server bringen

Der Host betreibt bereits `checklist.flowaudit.de` aus `/opt/checklist`. Die
PDF-App kommt **daneben**, mit eigenem Verzeichnis, eigener Env-Datei und
eigenem Tunnel. Der vorhandene Stack wird dabei nicht angefasst.

### C1. Ablage

```bash
ssh hetzner
sudo mkdir -p /opt/pdf-editor /etc/pdf-editor
sudo chown deploy:deploy /opt/pdf-editor
git clone https://github.com/janpow77/pdf-editor.git /opt/pdf-editor
```

Env-Datei nach dem Muster des vorhandenen Stacks — `root:root`, `0600`, also
außerhalb des Repositorys:

```bash
sudo tee /etc/pdf-editor/env >/dev/null <<EOF
COMPOSE_PROJECT_NAME=pdfapp
PDFAPP_SECRET_KEY=$(openssl rand -hex 32)
PDFAPP_DB_PASSWORD=$(openssl rand -hex 24)
PDFAPP_ADMIN_EMAIL=<ihre-adresse>
PDFAPP_ADMIN_PASSWORD=<sicheres-passwort>
PDFAPP_PUBLIC_BASE_URL=https://pdf.flowaudit.de
PDFAPP_SOURCE_URL=https://github.com/janpow77/pdf-editor
PDFAPP_HSTS_SECONDS=15768000
PDFAPP_TRUST_CF_HEADER=true
TUNNEL_TOKEN=<token-des-neuen-tunnels>
EOF
sudo chmod 600 /etc/pdf-editor/env
```

Zwei Schalter, die man nur bewusst setzt:

- **`PDFAPP_TRUST_CF_HEADER=true`** lässt den Ratenbegrenzer `CF-Connecting-IP`
  glauben. Ist der Dienst *auch* direkt erreichbar, kann jemand diesen Kopf
  fälschen und das Limit umgehen. Nur setzen, wenn ausschließlich der Tunnel
  Zugang hat.
- **`PDFAPP_HSTS_SECONDS`** merkt sich der Browser für die angegebene Dauer.
  Ein späterer HTTP-Zugriff auf dieselbe Domain ist dann nicht mehr möglich.
  Erst einschalten, wenn TLS dauerhaft steht.

### C2. Cloudflare-Tunnel

**Den bestehenden Tunnel von audit_designer nicht verändern.** Im
Cloudflare-Dashboard einen eigenen Tunnel anlegen, Hostname
`pdf.flowaudit.de` → `http://frontend:80`, Token in die Env-Datei.

### C3. Start

```bash
cd /opt/pdf-editor
docker compose --env-file /etc/pdf-editor/env --profile prod up -d --build
```

Im Produktivbetrieb erreicht der Tunnel den Frontend-Container über das
Compose-Netz. Die Portfreigabe `127.0.0.1:8080` wird dafür **nicht** gebraucht
— wer sie weglässt, verkleinert die Angriffsfläche um einen offenen Port und
umgeht zugleich eine mögliche Kollision mit dem vorhandenen Stack.

### C4. Abnahme

```bash
curl -s https://pdf.flowaudit.de/api/health | jq '{status, accounts}'
curl -sI https://pdf.flowaudit.de/ | grep -iE "content-security|strict-transport|x-frame"
docker compose --env-file /etc/pdf-editor/env ps
```

Die Kopfzeilen müssen erscheinen — sie sind der geprüfte Schutz gegen
Skripteinschleusung und Clickjacking. Fehlen sie, greift die Auslieferung nicht
auf die mitgelieferte nginx-Konfiguration zu.

---

## Teil D — Laufender Betrieb

### D1. Sicherung

Zu sichern ist **ausschließlich die Konten-Datenbank**. Nutzerdateien werden
nicht gespeichert — es gibt sie nach der Verarbeitung schlicht nicht mehr. Das
ist der Kern des Nutzungsversprechens und hier die angenehme Folge: Der
Sicherungsumfang ist winzig.

```bash
# In den Crontab von deploy, täglich
docker exec pdfapp-db-1 pg_dump -U pdfapp pdfapp \
  | gzip > /opt/pdf-editor/backups/pdfapp_$(date +%F).sql.gz
find /opt/pdf-editor/backups -name 'pdfapp_*.sql.gz' -mtime +14 -delete
```

Eine Sicherung, die nie zurückgespielt wurde, ist eine Vermutung. Einmal pro
Quartal auf einem Testsystem einspielen und anmelden.

### D2. Aktualisierung der Fremdbibliotheken

Der Grund für die Kapselung in `backend/app/pdf_backend.py`: Alle
Fremdbibliotheken laufen über einen Zugangspunkt, ein Wechsel trifft eine Datei
statt sieben. Die Komponenten und ihre Lizenzen stehen unter `/lizenzen` und
kommen aus demselben Register, über das sie geladen werden — die Liste kann
nicht veralten, ohne dass die Funktion mit veraltet.

| Anlass | Frist | Vorgehen |
|---|---|---|
| Sicherheitsmeldung zu PyMuPDF, pikepdf, Ghostscript, LibreOffice | 7 Tage | Version anheben, Tests, Deployment |
| Sonstige Aktualisierung | quartalsweise | Gesammelt, mit vollem Testlauf |
| Neue Hauptversion (z.B. PyMuPDF 2.x) | nach Bedarf | Auf Testsystem, `/lizenzen` gegenprüfen |

Vor jedem Deployment, ohne Ausnahme:

```bash
cd backend && python3 -m pytest tests/ -q     # 160 Fälle
cd ../frontend && npm run type-check && npm run build
```

**Offen und ehrlich benannt:** Die Versionen in `requirements.txt` sind
überwiegend nach oben offen (`>=`). Ein Fremdrelease kann den Build damit
unbemerkt verändern. Vor dem Produktivbetrieb sollten die Versionen festgezogen
und ein Paketspiegel eingerichtet werden, damit ein Build nicht von der
Erreichbarkeit von PyPI und npm abhängt.

### D3. Verfügbarkeit

Es gibt **keine Hochverfügbarkeit** und das ist eine bewusste Entscheidung: ein
Host, ein Container je Dienst. Fällt der Server aus, ist die Anwendung weg, bis
er wieder da ist. Für ein kostenloses Hilfswerkzeug ist das vertretbar — für
einen Dienst, auf den sich ein Verfahren stützt, wäre es das nicht.

Wer eine Zusage braucht: Bearbeitungszeit an Werktagen, keine Zusicherung
außerhalb. Das gehört in die Dienstbeschreibung, bevor jemand anderes eine
Erwartung daraus ableitet.

Eine Grenze, die bei mehreren Instanzen zuschlägt: Die Auftragsverwaltung für
lange Läufe (OCR, Vergleich) hält Ergebnisse **prozesslokal** im Speicher. Mit
mehreren Backend-Instanzen fände die Abholung ihren Auftrag nicht mehr.
Skalierung erfordert vorher einen gemeinsamen Auftragsspeicher.

### D4. Rückfall

```bash
cd /opt/pdf-editor
git log --oneline -5
git checkout <letzter-guter-stand>
docker compose --env-file /etc/pdf-editor/env --profile prod up -d --build
curl -s https://pdf.flowaudit.de/api/health | jq .status
```

Mit GHCR-Bildern (Teil B4) geht es schneller und ohne Bauen: Bild-Tag in der
Compose-Datei zurücksetzen, `docker compose up -d --force-recreate`.

Bei Datenbankänderungen gilt die Reihenfolge aus dem vorhandenen
Hetzner-Runbook: erst sichern, dann die neue Anwendungsversion, danach die
Migration — und Migrationen rückwärtskompatibel schreiben.

### D5. Zuständigkeit

Ein Dienst ohne benannte Zuständigkeit ist ein Dienst, den im Zweifel niemand
repariert. Vor der Freigabe zu klären und hier einzutragen:

- Fachliche Zuständigkeit: _________
- Technische Zuständigkeit: _________
- Vertretung: _________
- Meldeweg bei Störung: _________

### D6. Restrisiken, die im Quelltext nicht zu schließen sind

Diese Punkte lassen sich nur durch die Betriebsumgebung abfangen. Sie sind
bekannt, gemindert, aber nicht beseitigt:

1. **Office-Konvertierung.** LibreOffice läuft mit eigenem Profil je Aufruf,
   ohne Makros und ohne Aktualisierung von Verknüpfungen. Der Import
   eingebetteter Bilder ist aber Teil des Formats — eine hochgeladene Datei
   könnte weiterhin auf lokale Pfade oder interne Adressen verweisen.
   Vollständig geschlossen ist das erst mit einem Konvertierungsprozess ohne
   Netzzugang und ohne Lesezugriff auf das übrige Dateisystem: eigener
   Container, kein Egress, Dateisystem nur lesbar.
2. **Ein Host.** Siehe D3.
3. **Offene Versionsangaben.** Siehe D2.
4. **AGPL.** PyMuPDF und Ghostscript verlangen, dass Nutzende des Dienstes den
   Quelltext erhalten. Nach der Extraktion muss `PDFAPP_SOURCE_URL` auf das
   neue Repository zeigen, und dieses muss öffentlich erreichbar sein. Ist es
   das nicht, ist die Lizenzbedingung verletzt — die Lizenzseite weist im
   Betrieb darauf hin, wenn die Adresse fehlt.

---

## Kurzreferenz

```bash
# NUC
cd /opt/pdf-editor/pdf-editor-app
docker compose up -d --build
docker compose logs -f backend
docker compose down                      # ohne -v, sonst sind die Konten weg

# Hetzner
ssh hetzner
cd /opt/pdf-editor
docker compose --env-file /etc/pdf-editor/env --profile prod up -d
docker compose --env-file /etc/pdf-editor/env logs -f backend
curl -s https://pdf.flowaudit.de/api/health | jq .

# Vor jedem Deployment
cd backend && python3 -m pytest tests/ -q
cd frontend && npm run type-check && npm run build
```

`docker compose down -v` löscht das Datenbank-Volume und damit alle Konten.
Ohne `-v` bleiben sie erhalten.
