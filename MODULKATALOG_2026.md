# Modulkatalog 2026 — Abdeckungsanalyse

Abgleich des 18-Modul-Zielbilds („moderne PDF-Plattform 2026") mit dem
Ist-Stand der App. Legende: ✅ vorhanden · 🟡 teilweise · ❌ fehlt ·
⛔ Konflikt mit dem Kernversprechen „keine Datenspeicherung" (nur mit
Opt-in-Konto-Speicherung möglich, Architekturentscheidung nötig).

## 1. Grundlagen — ✅ weitgehend vollständig

| Funktion | Status |
|---|---|
| PDF erstellen aus Word/Excel/Bildern | ✅ (Word→PDF, Bilder→PDF) / 🟡 Excel→PDF fehlt (LibreOffice-Muster vorhanden, ~1 h) |
| PDF erstellen aus HTML/Webseiten | ❌ (bräuchte Headless-Browser im Backend) |
| Text ändern | ✅ WYSIWYG-Blockeditor (Grenze: kein Acrobat-Reflow) |
| Bilder austauschen | ❌ (Bild einfügen ✅ via Signatur/Wasserzeichen; gezielter Austausch fehlt) |
| Seiten verschieben/löschen/drehen/extrahieren/kopieren | ✅ (Seiten ordnen, Rotieren, Teilen) / 🟡 leere Seiten einfügen fehlt (trivial) |
| Merge / Split / Komprimieren | ✅ |

## 2. Konvertierung — 🟡 Kern vorhanden

✅ PDF→Word, PDF→Excel, PDF→Text, Word→PDF, Bilder→PDF, Scans→PDF (Scan-Optimierung mit OCR)
❌ PDF→PowerPoint/Markdown/HTML/EPUB/CSV/JSON, Excel→PDF, Webseiten→PDF
→ PDF→Markdown/HTML/CSV/JSON sind mit PyMuPDF gut machbar (mittlerer Aufwand); EPUB/PowerPoint Nische.

## 3. OCR — 🟡 solide Basis

✅ OCR mit unsichtbarer Textebene (deu/eng), automatische Drehung, Schräglagen-Korrektur (OCRmyPDF), mehrseitig, Tabellenerkennung (tabula bei PDF→Excel)
❌ 100+ Sprachen (nur weitere tesseract-Sprachpakete ins Image — geringer Aufwand pro Sprache), Handschrift (braucht andere Modelle), Formular-Struktur-Erkennung, Hintergrund entfernen/Bildverbesserung (unpaper installiert, `--clean` noch nicht exponiert).

## 4. KI-Funktionen — ❌ bewusst noch nicht

Zusammenfassen, Chat mit PDF, Übersetzung, Auto-Gliederung, Schlagwörter:
technisch über den vorhandenen ai-router des FlowAudit-Ökosystems gut
anbindbar (lokales LLM = „ohne Cloud" ✅). Voraussetzung: Erweiterung des
Datenschutz-Versprechens („Inhalte werden transient an das interne LLM
übergeben") — Produktentscheidung, dann 2–4 Tage für die ersten vier
Funktionen. Auto-Inhaltsverzeichnis existiert bereits regelbasiert (TOC-Auto-Detect).

## 5. Vergleich — 🟡

✅ Dokumentenvergleich Text + visuell (async), Word-Vergleich
❌ Tabellen-/Layout-spezifischer Vergleich, Versionsverwaltung mit Änderungsprotokoll (⛔ bräuchte Dokumentspeicherung).

## 6. Formulare — 🟡

✅ Erkennen + Ausfüllen + Einbrennen (AcroForm: Text, Checkbox, Auswahl)
❌ Felder erzeugen (Formular-Designer), Berechnungen/Validierung, CSV-Export der Felddaten (klein, lohnt), XFA (bewusst nie — auch Adobe deprecates XFA).

## 7. Digitale Signaturen — 🟡

✅ PAdES-Signatur mit eigenem PKCS#12, Stapelsignatur wäre über Batch ergänzbar, Bild-Signatur
❌ QES/eIDAS-Vertrauensdienste (regulatorisch, braucht Vertrauensdiensteanbieter), qualifizierte Zeitstempel (TSA-Anbindung — pyHanko kann das, braucht TSA-URL-Konfiguration: geringer Aufwand), Signatur-PRÜFUNG mit Bericht (pyHanko validation — mittlerer Aufwand, hoher Behörden-Mehrwert).

## 8. Sicherheit — ✅ weitgehend

✅ Passwortschutz AES-256, Entsperren, Schwärzen (echte Redaction), Wasserzeichen, Metadaten bearbeiten
🟡 Metadaten VOLLSTÄNDIG entfernen + versteckte Inhalte (ein „Bereinigen"-Werkzeug: geringer Aufwand) · Rechteverwaltung (Drucken/Kopieren-Flags via pikepdf: gering)
✅ „Sichere Löschung" ist konzeptbedingt erfüllt: es wird nie gespeichert.

## 9. Annotation — ✅ bis auf Nischen

✅ Kommentare, Markierungen, Stempel, Zeichnen/Freihand, Textfelder, Einbrennen
❌ Audio-Kommentare, Aufgaben (⛔ Aufgaben brauchen Speicherung/Accounts).

## 10. Zusammenarbeit — ⛔ Architektur-Entscheidung

Mehrbenutzer, Freigaben, Versionierung, Cloud-Sync widersprechen dem
No-Storage-Kern. Realistischer Weg: Opt-in-Dokumentablage für Kontoinhaber
als eigenes Modul mit eigener Datenschutz-Basis — großer Schritt Richtung
„Dokumentenplattform", siehe Empfehlung unten.

## 11. Stapelverarbeitung — 🟡

✅ Batch (bis 50 Dateien → ZIP): Komprimieren, Rotieren, Passwortschutz, Bates fortlaufend, PDF/A
❌ Batch-OCR/-Signierung/-Wasserzeichen/-Umbenennung (gleiche Mechanik, je ~1 h — OCR wegen Laufzeit über die Job-Queue).

## 12. Automatisierung — 🟡 API ja, Orchestrierung nein

✅ Vollständige REST-API (alle 70+ Endpoints, OpenAPI unter /docs) — CLI/PowerShell/Python-Anbindung damit trivial
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

✅ REST-API + OpenAPI-Schema; Code als extrahierbares, entkoppeltes Paket
❌ SDK-Pakete, JS-API, Plugin-System, Dokument-Events.

## 16. KI-Workflow (Klassifizierung, Extraktion, RAG) — ❌ hier / ✅ im Ökosystem

Rechnungs-/Bescheid-Erkennung, Metadaten-Extraktion, RAG-Index: Das ist
exakt der Funktionskern von Audit Designer (VP-AI, Harvester, KB/pgvector).
Empfehlung: NICHT in der Public-App duplizieren, sondern die PDF-App-API
aus Audit Designer heraus nutzen (Vorverarbeitung: OCR, PDF/A, Split).

## 17. Behörden/Prüfer-Spezifika — 🟡

✅ DSGVO-Schwärzung, Bates/Aktenzeichen-Kennzeichnung, PDF/A, Tabellen-Extraktion aus Bescheiden (PDF→Excel), Formulare
🟡 Signaturprüfung nach eIDAS (siehe Modul 7 — nächster sinnvoller Baustein), Prüfakte mit Inhaltsverzeichnis (Merge + TOC-Editor vorhanden, „Akte bauen"-Assistent fehlt)
❌ Revisionssichere Archivierung (⛔ Speicherung), Fördernummern-/SAP-Erkennung (gehört zu Modul 16 → Audit Designer).

## 18. Premium 2026 — ❌ (bis auf Fundament)

Lokale KI ohne Cloud: Fundament im Ökosystem vorhanden (ai-router).
Sprachsteuerung, Mindmaps, Wissensgraphen, Qualitätsprüfung von Scans,
KI-Agenten: Zukunftsmodule; Scan-Qualitätsprüfung (unscharfe/doppelte/
fehlende Seiten) wäre der greifbarste Kandidat (PyMuPDF + Heuristiken).

---

## Fazit & empfohlene Reihenfolge

**Abdeckung heute**: Module 1, 8, 9 praktisch vollständig; 2, 3, 5, 6, 7, 11, 12, 15, 17 im Kern vorhanden; 4, 16, 18 fehlen (KI); 10, 13, 14 stehen bewusst im Konflikt mit „keine Datenspeicherung".

**Nächste Ausbaustufen mit bestem Aufwand/Nutzen:**
1. **Signaturprüfung mit Bericht** (pyHanko-Validation) + TSA-Zeitstempel — Behörden-Mehrwert, kein Speicher-Konflikt.
2. **Kleinteilige Lücken schließen**: Excel→PDF, leere Seiten, Metadaten-Bereinigung, Rechteverwaltung, Formular-CSV-Export, weitere Batch-Operationen, mehr OCR-Sprachen.
3. **KI-Modul über den ai-router** (Zusammenfassen, Chat mit PDF, Übersetzung) — mit transparent erweitertem Datenschutzhinweis „lokales LLM, transient".
4. **PDF→Markdown/HTML/CSV/JSON** für den Entwickler-/Automatisierungs-Anwendungsfall.
5. **Plattform-Entscheidung**: Zusammenarbeit/DMS/Cloud nur als getrenntes Opt-in-Modul mit Dokumentablage — oder bewusst dem Ökosystem (Audit Designer/FlowAudit) überlassen und die PDF-App als dessen Verarbeitungs-API positionieren (Empfehlung).
