# Plan: Schwärzung verbessern, nach auditcore überführen, in KPAnG einsetzen

Stand: 19.11.2026. Ergänzt den [Test- und Prüfplan](pruefplan-schwaerzung.md).

## Reihenfolge (Entscheidung 19.11.2026)

1. **pdf-editor verbessern und optimieren.** Die Schwärzung wird hier fertig entwickelt und gegen den Prüfplan abgenommen.
2. **auditcore.** Der abgenommene Stand fließt in die vorhandene Bibliothek `auditcore_pdf` ein. Der pdf-editor wird danach selbst Nutzer der Bibliothek.
3. **KPAnG / Regulierung.** Danach wird geprüft, wie Regulierung von `auditcore_pdf` 0.1.0 auf den neuen Stand wechselt.

## Ausgangslage

Es gibt heute drei Schwärzungsstände, die sich gegenseitig nicht kennen:

| Stand | Ort | Eigenschaften |
|---|---|---|
| pdf-editor | `backend/app/services/pdf_extras_service.py` | Muster, Begriffslisten, KI-Namenserkennung (spaCy), Vorschau als Liste, Batch. Keine Bereinigung versteckter Inhalte, zeilenweise Suche (V1–V10 im Prüfplan). |
| `auditcore_pdf` 0.1.0 | `auditcore/packages/auditcore_pdf` (origin/main), MIT, PyMuPDF nur als Extra `[pymupdf]` | Aus pdf-editor `ce34413` und audit_designer abgeleitet, mit Korrekturen: zeilenübergreifende Begriffe, Groß-/Kleinschreibung, Bereinigung von Metadaten/XMP/Anhängen/Kommentaren, Erkennung gescannter Seiten, Nachprüfung `verify_redaction`. Keine KI-Namenserkennung, keine Vorschau-/Auswahl-Schnittstelle. |
| Regulierung | `regulierung/backend/app/services/pdf_werkzeuge.py` (425 Zeilen) über `auditcore_pdf[pymupdf]==0.1.0`, Release v0.6.0 | Eigene Absicherung um die Bibliothek: Vorprüfung (verschlüsselt, Scan, Bilder, Vektorgrafik → Ablehnung), Muster mit Wortgrenzen, Geburtsdatum nur nach „geb.“/„geboren“, Zusatzprüfung Lesezeichen/Formularfelder/Zeilenumbruch, Rasterung mit Stempel „ENTWURF“. Einsatz: `POST /akteneinsicht/{id}/geschwaerzte-kopie` (§ 49 OWiG); Oberfläche `AkteneinsichtTab.tsx` ohne Vorschau, immer alle Muster. |

Stichprobe gegen `auditcore_pdf` 0.1.0 (19.11.2026, synthetische Datei):

- behoben gegenüber pdf-editor: Metadaten, Kommentare, Groß-/Kleinschreibung, Name über Zeilenumbruch
- **offen:** Formularfeldwert, Lesezeichen und `mailto:`-Link bleiben stehen. Die Nachprüfung meldet den Rest (`verified: False`), der Bericht steht aber trotzdem auf `success: True`, die Datei wird ausgeliefert. Musterkollisionen (Telefon in IBAN, „VO 2021/1060“ als Aktenzeichen, „1.2.3.4“ als IP) unverändert, Silbentrennung nicht erkannt, bei Teilworttreffern wird das ganze Wort geschwärzt.

## Schritt 1: pdf-editor (jetzt)

Umsetzung nach dem Prüfplan, so geschnitten, dass sie später ohne Umbau in die Bibliothek passt:

- **Zweistufiger Ablauf als Schnittstelle:** `plan` liefert Fundstellen mit fester Kennung, Rechteck, Text, Quelle und Auswahlstatus sowie den SHA-256 der Datei. `apply` schwärzt genau die übergebene Auswahl und lehnt einen Plan zu einer anderen Datei ab. Damit ist die Pflicht zur Vorschau technisch abgesichert, nicht nur in der Oberfläche.
- **Fail-closed:** Bleibt nach dem Schwärzen eine ausgewählte Fundstelle irgendwo in der Datei lesbar (Seite, Formularfeld, Lesezeichen, Link, Metadaten, Rohbytes), wird nichts ausgeliefert.
- Bereinigung, zeilenübergreifende Suche und Scan-Erkennung nach dem Vorbild von `auditcore_pdf` 0.1.0, ergänzt um die dort noch offenen Punkte.
- Regeln aus Regulierung übernehmen, wo sie allgemein sind (Wortgrenzen, Geburtsdatum mit Kontext, Vorprüfung als Warnung statt Abbruch).
- Oberfläche: Seitenansicht mit markierten Fundstellen, einzeln und gruppenweise ab- und wieder auswählbar, Bereich ergänzen und anpassen; gleicher Ablauf im Batch.
- Ergebnis-Datenformat (Plan-JSON) dokumentieren. Es ist später der Vertrag für die auditcore-Oberflächenbausteine.

## Schritt 2: auditcore (danach)

- Ausbau von `auditcore_pdf` auf 0.2.0, kein neues Paket: Plan/Apply, fail-closed-Nachprüfung, erweiterte Bereinigung, Prüfziffern für IBAN/Kreditkarte/Steuer-ID, KI-Namenserkennung als Extra `[ner]` (spaCy ≥ 3.8 wegen numpy 2, siehe Prüfplan V11).
- Prüfkorpus und Kennzahlentests aus dem pdf-editor als Bibliothekstests übernehmen (synthetische Daten, ggf. `auditcore_dummygenerator` als Testabhängigkeit).
- Oberfläche nach dem vorhandenen Muster: Ansichtsmodell in `@auditcore/ui-core`, Komponente in `@auditcore/ui` (Vue, für pdf-editor) und `@auditcore/ui-react` (für Regulierung). Seitenbilder kommen aus `render_page`, kein pdf.js nötig.
- Herkunftsnachweis und Verhaltensänderungen nach den auditcore-Regeln (Characterization vor Extraktion, `provenance.json`, `docs/behavior-changes.md`), Lizenz MIT, PyMuPDF bleibt optionales Extra.
- pdf-editor wechselt auf die Bibliothek; seine bisherigen Tests laufen als Nutzertests weiter.
- Arbeit in einem eigenen auditcore-Worktree; der lokale Hauptcheckout steht auf `feat/regulierung-apt-deployment` und ist hinter `origin/main`.

## Schritt 3: KPAnG / Regulierung (zuletzt prüfen)

Zu prüfen, nicht vorab entschieden:

- Was aus `pdf_werkzeuge.py` in die Bibliothek gewandert ist und was KPAnG-eigen bleibt (Aktenzusammenführung, DOCX-Umwandlung, Stempel „ENTWURF“, Audit-Log).
- Akteneinsicht auf Plan/Apply umstellen; `AkteneinsichtTab.tsx` bekommt die React-Prüfansicht mit Pflicht-Vorschau.
- Anhebung aller auditcore-Pins auf ein gemeinsames Release (`test_auditcore_pins.py` verlangt das), APT-Lock über `deploy/apt/update_auditcore_lock.py`, beide Ziele Ubuntu 24.04 (py3.12) und 26.04 (py3.14).
- KI-Namenserkennung in Regulierung nur, wenn das spaCy-Modell als Wheel für beide Pythonversionen offline mitgeliefert werden kann; sonst zunächst ohne.
- AGPL-Freigabe für PyMuPDF liegt vor (IT/ISB, 08.10.2026, `requirements.txt` Z. 85–87); neue Abhängigkeiten brauchen ggf. eine eigene Freigabe.
- Plan-JSON enthält Klartext der Fundstellen: nur übertragen, nicht protokollieren oder dauerhaft speichern.
