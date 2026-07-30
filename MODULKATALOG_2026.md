# Modulkatalog 2026 — Abdeckungsanalyse

Abgleich des 18-Modul-Zielbilds („moderne PDF-Plattform 2026") mit dem
Ist-Stand der App. Legende: ✅ vorhanden · 🟡 teilweise · ❌ fehlt ·
⛔ Konflikt mit dem Kernversprechen „keine Datenspeicherung" (nur mit
Opt-in-Konto-Speicherung möglich, Architekturentscheidung nötig).

Stand nach dem Endausbau: alle Katalogpunkte, die ohne Datenspeicherung und
ohne Cloud umsetzbar sind, sind umgesetzt (Office→PDF, Text-Exporte,
Bereinigen, Rechteverwaltung, Signaturprüfung mit Vertrauensankern,
Stapelsignatur, Prüfakte, Qualitätsprüfung, Formular-Designer mit
Berechnungen und CSV-Serienbefüllung, Bild ersetzen, lokale KI mit fünf
Modi, Rolodex-Dashboard). Was offen bleibt, bleibt aus einem Grund — siehe
Tabelle am Ende.

## 1. Grundlagen — ✅ vollständig

| Funktion | Status |
|---|---|
| PDF erstellen aus Word/Excel/PowerPoint/ODF/RTF/Text/Bildern | ✅ (Word→PDF, Office→PDF via LibreOffice, Bilder→PDF) |
| PDF erstellen aus HTML | ✅ (HTML-Dateien via Office→PDF) / ❌ Live-Webseiten (bräuchte Headless-Browser **und** würde serverseitige URL-Abrufe erlauben → SSRF-Risiko, bewusst nicht umgesetzt) |
| Text ändern | ✅ WYSIWYG-Blockeditor (Grenze: kein Acrobat-Reflow) |
| Bilder austauschen | ✅ Bilder auflisten (mit Vorschau) und gezielt ersetzen; Einfügen via Signatur/Wasserzeichen |
| Seiten verschieben/löschen/drehen/extrahieren/kopieren/leere einfügen | ✅ (Seiten ordnen, Rotieren, Teilen, Leere Seiten) |
| Merge / Split / Komprimieren | ✅ |

## 2. Konvertierung — ✅ Kern + Entwickler-Formate

✅ PDF→Word, PDF→Excel, PDF→Text, PDF→Markdown, PDF→HTML, PDF→JSON (Textblöcke + Positionen), PDF→CSV (Tabellen), Word→PDF, Excel/PowerPoint/ODF/RTF/HTML→PDF, Bilder→PDF, Scans→PDF (Scan-Optimierung mit OCR)
❌ PDF→PowerPoint/EPUB (Nische), Live-Webseiten→PDF.

## 3. OCR — ✅ solide

✅ OCR mit unsichtbarer Textebene in 7 Sprachen (deu/eng/fra/ita/spa/nld/pol, kombinierbar), automatische Drehung, Schräglagen-Korrektur, Entrauschen (`--clean`/unpaper), mehrseitig, Tabellenerkennung (tabula bei PDF→Excel)
❌ 100+ Sprachen (weitere tesseract-Pakete ins Image — geringer Aufwand pro Sprache), Handschrift (braucht andere Modelle), Formular-Struktur-Erkennung.

## 4. KI-Funktionen — ✅ lokal, ohne Cloud

✅ Zusammenfassen, „Frage zum Dokument", **Übersetzung** (freie Zielsprache), **Schlagwörter** und **Gliederungsvorschlag** über einen OpenAI-kompatiblen Endpoint auf **eigener Infrastruktur** (`PDFAPP_LLM_URL`, z.B. ai-router des FlowAudit-Ökosystems). Kachel erscheint nur, wenn konfiguriert; Datenschutzerklärung weist die transiente Übertragung an das lokale LLM aus. Antworten sind als KI-generiert gekennzeichnet.
❌ Automatische Klassifizierung/Extraktion → gehört zu Modul 16 (Audit Designer).

## 5. Vergleich — 🟡

✅ Dokumentenvergleich Text + visuell (async), Word-Vergleich
❌ Tabellen-/Layout-spezifischer Vergleich, Versionsverwaltung mit Änderungsprotokoll (⛔ bräuchte Dokumentspeicherung).

## 6. Formulare — ✅ vollständig (außer XFA, bewusst)

✅ Erkennen + Ausfüllen + Einbrennen (AcroForm: Text, Checkbox, Auswahl)
✅ **Formular-Designer**: Felder per Maus auf der Seitenvorschau aufziehen
(Textfeld, mehrzeilig, Kontrollkästchen, Dropdown, Liste, Signaturfeld) mit
Eigenschaften (Name, Hilfetext, Vorbelegung, Auswahlwerte, Schriftgröße,
Pflichtfeld, Nur-lesbar), Prüflauf vor dem Erzeugen, Layout lokal speichern
(localStorage-Autosave + JSON-Datei) und importieren — inkl. Übernahme
vorhandener Formularfelder aus einem PDF zur Weiterbearbeitung.
✅ **Berechnungen, Formatierung, Wertebereichsprüfung**: Summe/Produkt/
Mittelwert/Minimum/Maximum über gewählte Felder oder eine Formel über
Feldnamen; Zahl-, Währungs- und Prozentformat (deutsches Trennzeichen);
Min/Max-Prüfung. Umgesetzt als PDF-Aktionen (`AFSimple_Calc`,
`AFNumber_Format`, `AFRange_Validate`) inklusive Berechnungsreihenfolge
(/CO) und `NeedAppearances`. **Kein freies JavaScript**: der Dienst baut die
Skripte selbst aus einer geprüften Formel — sonst wäre die App ein bequemer
Weg, beliebiges JS in fremde PDFs zu schreiben.
✅ **CSV**: Feldwerte exportieren, leere Vorlage erzeugen und Serienbefüllung
(eine CSV-Zeile = ein PDF, Spalte `dateiname` steuert den Namen, mehrere
Zeilen ergeben ein ZIP).
🟡 Optionsfelder (Radio-Gruppen): nicht unterstützt — PyMuPDF 1.28 kann
mehrere Radio-Widgets einer Gruppe nicht anlegen; UI verweist auf Dropdown
bzw. Kontrollkästchen.
❌ XFA (bewusst nie — auch Adobe deprecates XFA); Ausführung der Rechen-
aktionen obliegt dem Viewer (Acrobat & Co.), einfache Browser-Vorschauen
zeigen sie nicht.

## 7. Digitale Signaturen — ✅ bis auf QES

✅ PAdES-Signatur mit eigenem PKCS#12, qualifizierte Zeitstempel (RFC-3161-TSA-URL optional pro Signatur), **Stapelsignatur** über die Batch-Verarbeitung, Bild-Signatur, **Signaturprüfung mit Bericht** (Integrität, CMS-Gültigkeit, Unterzeichner, Signierzeitpunkt, Abdeckung)
✅ **Vertrauenskette**: eigene Wurzelzertifikate (PEM/DER) hochladbar — damit wird zusätzlich geprüft, ob die Signatur auf einen vertrauenswürdigen Anker zurückführt; ohne Anker bleibt es ehrlich bei „nicht bewertet"
❌ QES/eIDAS-Vertrauensdienste und automatischer Bezug der EU-Trusted-Lists (regulatorisch bzw. Cloud-Abruf — bewusst offen).

## 8. Sicherheit — ✅

✅ Passwortschutz AES-256, Entsperren, Schwärzen (echte Redaction), Wasserzeichen, Metadaten bearbeiten, **Bereinigen** (Metadaten, XMP, JavaScript, eingebettete Dateien, versteckte Inhalte), **Rechteverwaltung** (Drucken/Kopieren/Ändern/Kommentieren via pikepdf)
✅ „Sichere Löschung" ist konzeptbedingt erfüllt: es wird nie gespeichert.

## 9. Annotation — ✅ bis auf Nischen

✅ Kommentare, Markierungen, Stempel, Zeichnen/Freihand, Textfelder, Einbrennen
❌ Audio-Kommentare, Aufgaben (⛔ Aufgaben brauchen Speicherung/Accounts).

## 10. Zusammenarbeit — ⛔ Architektur-Entscheidung

Mehrbenutzer, Freigaben, Versionierung, Cloud-Sync widersprechen dem
No-Storage-Kern. Realistischer Weg: Opt-in-Dokumentablage für Kontoinhaber
als eigenes Modul mit eigener Datenschutz-Basis — großer Schritt Richtung
„Dokumentenplattform", siehe Empfehlung unten.

## 11. Stapelverarbeitung — ✅ vollständig

✅ Batch (bis 50 Dateien → ZIP): Komprimieren, Rotieren, Passwortschutz, Bates fortlaufend, PDF/A, Wasserzeichen, Bereinigen, **Stapelsignatur** (ein Zertifikat für alle Dateien) und **Umbenennen** (Muster mit `{name}`/`{n}`); Batch-OCR läuft über die Job-Queue (einzeln)
✅ Serienbefüllung von Formularen aus CSV (Modul 6).

## 12. Automatisierung — 🟡 API ja, Orchestrierung nein

✅ Vollständige REST-API (alle 80+ Endpoints, OpenAPI unter /docs) — CLI/PowerShell/Python-Anbindung damit trivial
❌ Workflow-Designer, Webhooks, Zeitpläne, Makros (⛔ Zeitpläne/Webhooks brauchen Persistenz; Workflow-Designer existiert im Ökosystem bereits: FlowStat-Pipeline-Builder — Integration statt Neubau).

## 13. Dokumentenmanagement — ⛔

Tags, Volltextsuche, Versionierung, Archiv = Dokumentspeicherung. Gehört
nicht in die anonyme Public-App, sondern in FlowAudit/Audit Designer
(dort existiert Harvester/KB bereits) oder ein Opt-in-Modul.

## 14. Cloud-Anbindungen — ❌ (bewusst)

OneDrive/Drive/Dropbox/S3/WebDAV: Jede Anbindung erweitert die
Datenschutz-Erklärung erheblich. Wenn, dann zuerst Nextcloud/WebDAV
(EU-/Behörden-relevant), als reiner Durchlauf ohne Speicherung.

## 15. Entwicklerfunktionen — 🟡

✅ REST-API + OpenAPI-Schema; strukturierte Exporte (JSON mit Textblöcken + Positionen, Markdown, CSV); Code als extrahierbares, entkoppeltes Paket
❌ SDK-Pakete, JS-API, Plugin-System, Dokument-Events — für eine anonyme Public-App ohne Nutzen; die REST-API deckt Automatisierung bereits ab.

## 16. KI-Workflow (Klassifizierung, Extraktion, RAG) — ❌ hier / ✅ im Ökosystem

Rechnungs-/Bescheid-Erkennung, Metadaten-Extraktion, RAG-Index: Das ist
exakt der Funktionskern von Audit Designer (VP-AI, Harvester, KB/pgvector).
Empfehlung: NICHT in der Public-App duplizieren, sondern die PDF-App-API
aus Audit Designer heraus nutzen (Vorverarbeitung: OCR, PDF/A, Split).

## 17. Behörden/Prüfer-Spezifika — ✅ Kern abgedeckt

✅ DSGVO-Schwärzung, Bates/Aktenzeichen-Kennzeichnung, PDF/A, Tabellen-Extraktion aus Bescheiden (PDF→Excel/CSV), Formulare, Signaturprüfung mit Bericht, **Prüfakte** (Merge mit Lesezeichen pro Dokument + durchgehender Bates-Nummerierung), Metadaten-Bereinigung vor Weitergabe
❌ Revisionssichere Archivierung (⛔ Speicherung), Fördernummern-/SAP-Erkennung (gehört zu Modul 16 → Audit Designer).

## 18. Premium 2026 — 🟡 Fundament + erste Bausteine

✅ Lokale KI ohne Cloud (Modul 4), **Qualitätsprüfung von Scans** (leere Seiten, Scans ohne Textebene, doppelte Seiten), Rolodex-Dashboard
❌ Sprachsteuerung, Mindmaps, Wissensgraphen, KI-Agenten: Zukunftsmodule.

---

## Fazit & empfohlene Reihenfolge

**Abdeckung heute**: Module 1, 2, 3, 4, 6, 7 (bis QES), 8, 9, 11, 17, 18 (Kern) vollständig; 5, 12, 15 im Kern vorhanden; 16 bewusst im Ökosystem; 10, 13, 14 stehen bewusst im Konflikt mit „keine Datenspeicherung".

**Bewusst offen — mit Begründung (keine reine Aufwandsfrage):**

| Punkt | Warum offen |
|---|---|
| Zusammenarbeit, DMS, Cloud-Anbindungen (10, 13, 14) | Widersprechen dem Kernversprechen „keine Datenspeicherung, keine Cloud". Nur als getrenntes Opt-in-Modul mit eigener Datenschutz-Basis denkbar — oder im Ökosystem (Audit Designer/FlowAudit), das die PDF-App als Verarbeitungs-API nutzt (Empfehlung). |
| Live-Webseiten → PDF | Bräuchte einen Headless-Browser im Image und serverseitige URL-Abrufe — ein SSRF-Einfallstor in einer öffentlich erreichbaren App. HTML-Dateien werden bereits konvertiert. |
| QES/eIDAS, EU-Trusted-Lists | Setzt einen Vertrauensdiensteanbieter bzw. laufenden Listenabruf (Cloud) voraus. Eigene Vertrauensanker sind hochladbar. |
| XFA-Formulare | Von Adobe selbst abgekündigt; kein Ziel. |
| Handschrift-OCR | Braucht andere Modellklassen als Tesseract. |
| PDF → PowerPoint/EPUB, Tabellen-/Layout-Vergleich | Nischenformate bzw. hoher Aufwand bei geringem Prüfnutzen; Text- und Visuellvergleich decken die Praxis ab. |
| SDK/JS-API/Plugin-System | Für eine anonyme Public-App ohne Nutzen — die REST-API deckt Automatisierung ab. |
| Ausführung der Formular-Berechnungen in der App | Die Aktionen liegen normkonform im PDF; ausgeführt werden sie vom Viewer (Acrobat & Co.). Ein eigener JS-Interpreter wäre ein Sicherheitsrisiko ohne Mehrwert. |
