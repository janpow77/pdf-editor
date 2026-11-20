# Test- und Prüfplan: Automatische Schwärzung

Stand: 19.11.2026 · Prüfgegenstand: Werkzeug „Schwärzen“ (Einzelbegriff, Muster und Namensliste, KI-Namenserkennung), Batch-Operation `redact`, manuelle Bereichsschwärzung im Werkzeug „Kommentieren“.

## 1. Ziel und Leitfragen

Der Plan prüft die Schwärzung aus sechs Blickwinkeln und beantwortet am Ende vier Fragen:

1. **Funktioniert sie?** Findet sie, was sie finden soll (Trefferquote), und schwärzt sie nichts, was sie nicht soll (Genauigkeit)?
2. **Ist sie sicher?** Ist der geschwärzte Inhalt nach dem Export wirklich aus der Datei verschwunden, auch aus Metadaten, Kommentaren, Formularfeldern, Lesezeichen, Bildern und Rohbytes?
3. **Trägt sie große Dokumente?** Laufzeit, Speicher, Zeitlimits und Bedienbarkeit bei hunderten Seiten und zehntausenden Fundstellen.
4. **Wie steht sie im Vergleich?** Funktionsumfang und Verfahren gegenüber kommerziellen Programmen, daraus eine priorisierte Verbesserungsliste.

Bewertungsmaßstab ist der Einsatz in der Verwaltung: Herausgabe von Unterlagen nach Akteneinsicht oder Informationsfreiheit, Weitergabe von Prüfakten mit personenbezogenen Daten. Ein übersehener Treffer wiegt dort schwerer als ein Treffer zu viel; eine Schwärzung, die nur optisch wirkt, ist ein Datenschutzvorfall.

## 2. Prüfgegenstand

| Baustein | Fundstelle | Verfahren |
|---|---|---|
| Einzelbegriff | `backend/app/services/pdf_extras_service.py` `redact_search` (ab Z. 1010), API `POST /api/pdf-extras/redact` | `page.search_for()` von PyMuPDF, ohne Vorschau |
| Muster und Namensliste | `find_pattern_matches` / `redact_patterns` (Z. 532–648), API `POST /api/pdf-extras/redact-patterns` (mit `preview=true`) | Wörter je Zeile zusammensetzen, Regex auf Zeilentext, Treffer auf Wort-Rechtecke zurückführen |
| Musterkatalog | `REDACTION_PATTERNS` (Z. 184–237), API `GET /api/pdf-extras/redact/patterns` | 9 Regex-Muster plus `ki_namen` |
| KI-Namenserkennung | `load_de_ner_model` in `backend/app/pdf_backend.py` (Z. 132), spaCy `de_core_news_sm` 3.7 | NER zeilenweise, nur Label `PER` |
| Batch | `batch_apply` Zweig `redact` (Z. 1405 ff.), API `POST /api/pdf-extras/batch` | wie Muster, je Datei, ZIP mit `schwaerzungen.txt` und `fehler.txt` |
| GUI | `frontend/src/components/tools/PdfRedact.vue`, `PdfBatch.vue`, Bereichsschwärzung in `PdfAnnotate.vue` | Vue 3 |
| Bestehende Tests | `backend/tests/test_redact_fonts.py`, `test_pdf_extras.py` Z. 51, `test_pdf_extras2.py` Z. 207–265 | pytest; Frontend ohne Testwerkzeug |

Grenzen aus der Konfiguration: 50 MB je Datei (angemeldet 100 MB), 200 MB gesamt im Batch, höchstens 50 Dateien je Batch, höchstens 5 000 Seiten, 200 Begriffe, Vorschauliste auf 500 Einträge gekürzt, Zeitlimit 300 s in nginx und im Frontend.

## 3. Vorbefunde aus Codelesung und Stichproben

Vor dem eigentlichen Testlauf habe ich den Code gelesen und ein kurzes Erkundungsskript gegen den Dienst laufen lassen (PyMuPDF 2.1 in einer Testumgebung, ohne spaCy; der Container kann wegen `PyMuPDF>=1.23.8` eine andere Version haben, das prüft der Testlauf mit). Die Befunde sind **vorläufig**; jeder wird im Testlauf mit einem eigenen Testfall bestätigt oder verworfen.

| Nr. | Befund | Beleg | Gewicht |
|---|---|---|---|
| V1 | **Formularfeldwerte bleiben nach der Schwärzung erhalten**, obwohl der Zähler sie als geschwärzt meldet. | Probe: Textfeld mit E-Mail-Adresse, Ergebnis `redactions: 2`, Feldwert und Seitentext nach dem Export unverändert vorhanden. | kritisch |
| V2 | **Metadaten, Lesezeichen und Kommentare werden nicht bereinigt.** Eine E-Mail-Adresse in Autor, Titel, Inhaltsverzeichnis oder Notiz-Kommentar steht nach dem Export weiter in der Datei. | Probe: `author`, `title`, TOC, Kommentarinhalt unverändert; Rohbytes enthalten die Adresse. | kritisch |
| V3 | **„Groß- und Kleinschreibung beachten“ wirkt beim Einzelbegriff nicht.** `search_for` sucht immer ohne Beachtung der Schreibweise; der Schalter vertauscht nur das Flag `TEXT_DEHYPHENATE`. | Probe: Begriff „Meier“ mit `match_case=True` schwärzt „MEIER“ und „Meier“. Code Z. 1020. | hoch |
| V4 | **Namen über einen Zeilenumbruch oder mit Silbentrennung werden nicht gefunden.** Die Suche arbeitet zeilenweise. | Probe: „Erika / Musterfrau“ auf zwei Zeilen nicht als „Erika Musterfrau“ erkannt; „Muster-/frau“ gar nicht. | hoch |
| V5 | **Muster überschneiden sich und treffen Fachtext.** „Telefonnummer“ trifft Teile einer IBAN und „021/1060“ in „VO 2021/1060“; „Aktenzeichen“ trifft „VO 2021/1060“; „Kreditkarte“ trifft Teile einer IBAN und Kundennummern; „IP-Adresse“ trifft Versionsnummern wie „1.2.3.4“. Keine Prüfsummen (IBAN-Modulo 97, Luhn, Steuer-ID-Prüfziffer). | Probe Nr. 4 | hoch für Fachakten mit Rechtsgrundlagen |
| V6 | **Vorschau zeigt anderen Text als geschwärzt wird.** Bei „Nur ganze Wörter“ aus wird das ganze Wort geschwärzt („Meierhof“), die Vorschau zeigt aber „Meier“. Das Gleiche gilt für Satzzeichen am Wort („(erika@example.org),“). | Probe Nr. 5, Rechteckbreiten | mittel |
| V7 | **Gescannte PDFs ohne Textebene liefern „Nichts gefunden“** ohne Hinweis, dass gar kein Text vorhanden ist. | Code: keine Prüfung auf Bildseiten | hoch (falsche Sicherheit) |
| V8 | **Einzelbegriff ohne Vorschau**, Fundstellen nur als Liste, keine Markierung auf der Seite, keine Möglichkeit, einzelne Fundstellen abzuwählen. | `PdfRedact.vue` | mittel |
| V9 | **Große Dokumente laufen synchron.** 500 Seiten mit 112 500 Fundstellen: Vorschau 4 s, Schwärzen 57 s. Das Zeitlimit von 300 s wird bei etwa 2 500 Seiten in dieser Dichte erreicht; Fortschrittsanzeige fehlt. Schwärzen sucht alle Fundstellen ein zweites Mal. | Probe Nr. 6 | mittel |
| V10 | KI-Namenserkennung bekommt nur einzelne Zeilen als Kontext; das verschlechtert die Erkennung bei Fließtext. | Code Z. 589–593 | mittel, im Test zu messen |
| V11 | **Frische Installation von `requirements.txt` bricht den spaCy-Import.** pandas 3.1 verlangt numpy ≥ 2, `thinc` 8.2.4 (spaCy 3.7) ist gegen numpy 1 gebaut → `ValueError: numpy.dtype size changed`. `pdf_backend.py` fängt nur `ImportError` ab, das Backend käme beim Import nicht hoch. Das Docker-Image baut mit denselben ungebundenen Versionen. | Testumgebung 19.11.2026, Python 3.12 | kritisch für den nächsten Image-Bau |
| V12 | Begriffe ab Nr. 201 werden ohne Hinweis verworfen. | `pdf_extras.py`, Test F10 | mittel |
| V13 | IBAN-Muster schwärzt ein folgendes kurzes Wort mit („AT61 1904 3002 3457 3201 in“). | Test F01 | niedrig (Übermaskierung) |
| V14 | Verschlüsselte Datei führt zu HTTP 500 statt verständlicher Meldung. | Test R01 | mittel |
| V15 | Datei ohne PDF-Inhalt führt zu HTTP 500 statt HTTP 400. | Test R03 | mittel |

## 4. Testumgebung und Testkorpus

### 4.1 Umgebung

- Backend lokal mit `backend/requirements*.txt` inklusive spaCy-Modell; zusätzlich ein Lauf **ohne** spaCy-Modell (Rückfallverhalten).
- Docker-Compose-Stand wie im Betrieb (nginx-Zeitlimit 300 s, Größenlimits aus `config.py`).
- Prüfwerkzeuge für die Forensik: `pdftotext` (Poppler), `qpdf --qdf --object-streams=disable` zum Entpacken, `strings`/`grep` auf Rohbytes, `pdfimages`, `exiftool`, `mutool show`, PyMuPDF als Zweitleser, optional pdf.js und Adobe Reader als Fremdleser.
- GUI: Playwright (Chromium und Firefox), Breite 1440 px und 390 px, Hell- und Dunkelmodus, axe-core für Barrierefreiheit.

### 4.2 Testkorpus

Alle Dateien synthetisch; keine echten personenbezogenen Daten. Zu jeder Datei gehört eine **Soll-Liste** mit jedem zu schwärzenden Vorkommen (Muster, Text) und jedem Text, der **nicht** geschwärzt werden darf (Negativliste). Umgesetzt in `backend/tests/redaction_corpus.py`: Die Dateien werden im Speicher erzeugt, es liegen keine Binärdateien im Repository. Die Testfälle stehen in `backend/tests/test_redaction_audit.py`; bekannte Mängel sind dort als `xfail(strict=True)` mit ihrer V-Nummer markiert. Wird ein Mangel behoben, schlägt der Test an und die Markierung muss entfernt werden.

Auch Telefon- und Aktenzeichenmuster treffen Rechnungs-, Beleg- und Förderkennzeichen (z. B. „2024-0815“, „0701 686 11“, „EFRE-2021-0042“); das ist unter V5 erfasst.

| Kennung | Inhalt | Zweck |
|---|---|---|
| K01 | Einfacher Brief, eine Seite, je Muster zwei Treffer | Grundfunktion |
| K02 | Varianten je Muster: IBAN mit und ohne Leerzeichen, ausländische IBAN, E-Mail mit Umlaut-Domain und Plus-Adresse, Telefon in `+49 (0) 69 …`, `069/123 45-67`, `0171-…`; Datum `1.2.2024`, `01.02.24`, `1. Februar 2024`; IPv6 | Trefferquote je Muster |
| K03 | Negativtext: Rechtsgrundlagen (`VO (EU) 2021/1060`, `Art. 74 Abs. 1`), Rechnungs- und Belegnummern, Beträge, Versionsnummern, Haushaltsstellen, Förderkennzeichen | Fehlalarme |
| K04 | Layout-Fälle: zwei Spalten, Tabellen, Kopf- und Fußzeilen, gedrehter Text, Text über Zeilenumbruch, Silbentrennung, Blocksatz mit großen Abständen, Hoch- und Tiefstellung | Zeilenbildung, Rechtecke |
| K05 | Zeichensatz: Umlaute, ß, Ligaturen (fi, fl), kombinierende Diakritika, geschützte Leerzeichen, weiche Trennstriche, Type-3-Schriften, Schriften ohne ToUnicode-Tabelle | Textextraktion |
| K06 | Versteckte Inhalte: Metadaten (Info und XMP), Lesezeichen, Notizen, Freitext-Kommentare, Formularfelder (Text, Kombinationsfeld), Dateianhänge, optionale Inhalte (Ebenen), weißer Text auf weißem Grund, Text unter einem Bild, Text außerhalb der Seite (CropBox), JavaScript, Links mit `mailto:` | Sicherheit (V1, V2) |
| K07 | Bilder: Scan ohne Textebene, Scan mit OCR-Textebene, Bild mit eingebettetem Namen, Vektorgrafik unter Fundstelle | Bild- und Scanbehandlung (V7) |
| K08 | Fließtext mit 200 Personennamen in verschiedenen Formen (Vorname Nachname, Titel, Doppelnamen, Adelsprädikate, ausländische Namen, Namen am Satzanfang, Namen, die auch Wörter sind: „Klaus Koch“, „Herr Wagner“) | KI-Namenserkennung |
| K09 | Große Dateien: 50, 500, 2 000, 5 000 Seiten; dünn (1 Treffer je Seite) und dicht (> 200 Treffer je Seite); 45 MB mit Bildern | Leistung, Grenzen |
| K10 | Fehlerhafte Dateien: verschlüsselt mit Passwort, nur Rechteschutz, beschädigte Xref, inkrementell gespeichert mit älterer Fassung, PDF/A, signiertes PDF, Portfolio | Robustheit |
| K11 | Batch: 50 Dateien gemischt aus K01–K10, eine davon ohne Treffer, eine fehlerhaft | Batch |

## 5. Prüfbereiche und Testfälle

Kennzeichnung: F = Funktion, S = Sicherheit, L = Leistung, G = GUI, K = KI, B = Batch, R = Robustheit. Jede Zeile wird ein automatisierter Test, soweit nicht mit „manuell“ markiert.

### 5.1 Funktion und Erkennungsgüte (F)

| Nr. | Testfall | Erwartung |
|---|---|---|
| F01 | Jedes Muster einzeln gegen K01 | alle Soll-Treffer, keine weiteren |
| F02 | Trefferquote und Genauigkeit je Muster gegen K02 und K03 | Kennzahlen je Muster in einer Tabelle (siehe Abschnitt 6) |
| F03 | Überschneidung: alle Standardmuster zugleich gegen K02 | jede Zeichenfolge höchstens einmal gezählt; Zählung je Muster nachvollziehbar (V5) |
| F04 | Begriffsliste: exakte Treffer, Groß-/Kleinschreibung an und aus, ganze Wörter an und aus | Verhalten entspricht dem Hilfetext |
| F05 | Einzelbegriff mit „Groß- und Kleinschreibung beachten“ | nur exakte Schreibweise geschwärzt (V3) |
| F06 | Begriff über Zeilenumbruch und mit Silbentrennung (K04) | wird gefunden oder die GUI weist auf die Grenze hin (V4) |
| F07 | Mehrspaltiger Text und Tabellen (K04) | keine Treffer über Spaltengrenzen hinweg zusammengesetzt; keine Spalte übersehen |
| F08 | Rechteckgenauigkeit: Schwarzbalken deckt den Treffer vollständig, angrenzende Wörter bleiben lesbar | Abgleich der Restwörter mit Soll (V6) |
| F09 | Vorschau und Ergebnis stimmen überein: Anzahl `total` = `X-Redactions`, Text in der Vorschau = tatsächlich entfernter Text | identisch (V6) |
| F10 | Leere Eingaben, nur Leerzeichen, 200 und 201 Begriffe, Begriff mit Regex-Sonderzeichen (`a.b`, `(x)`, `\d`) | Validierungsfehler bzw. wörtliche Suche |
| F11 | Ergebnisdatei öffnet in Fremdlesern (pdf.js, Poppler, Adobe Reader, qpdf `--check`) | keine Fehler, Seitenzahl unverändert |
| F12 | Nicht betroffene Inhalte bleiben erhalten: Text, Schriften, Bilder, Links, Formularfelder ohne Treffer, Seitenrotation, Seitengröße | Vergleich vor/nach |
| F13 | Manuelle Bereichsschwärzung in „Kommentieren“: Rechteck über Text, Bild und Vektorgrafik | Inhalt darunter entfernt, nicht nur überdeckt |

### 5.2 Sicherheit der Entfernung (S)

Kern der Prüfung. Jeder Testfall prüft das Ergebnis mit **mindestens zwei unabhängigen Lesern** und auf Rohbyte-Ebene nach dem Entpacken mit `qpdf --qdf --object-streams=disable`.

| Nr. | Testfall | Erwartung |
|---|---|---|
| S01 | Geschwärzter Text per Textextraktion (PyMuPDF, `pdftotext`, pdf.js), Kopieren aus dem Reader, Volltextsuche | nicht auffindbar |
| S02 | Rohbytes der entpackten Datei nach dem Klartext und nach Hex-/UTF-16-Kodierung durchsuchen | nicht auffindbar |
| S03 | Formularfeld mit Treffer (K06) | Feldwert entfernt oder Feld entfernt; Zähler stimmt (V1) |
| S04 | Metadaten Info-Wörterbuch und XMP mit Treffer | bereinigt oder deutlich gewarnt (V2) |
| S05 | Lesezeichen, Kommentare, Freitext, `mailto:`-Links, Dateianhänge mit Treffer | bereinigt oder deutlich gewarnt (V2) |
| S06 | Weißer Text, Text unter Bild, Text außerhalb der CropBox, ausgeblendete Ebenen | gefunden und entfernt oder gewarnt |
| S07 | Bild unter einer Fundstelle | Bildpixel im Bereich geschwärzt (`pdfimages` prüfen), Rest des Bildes erhalten |
| S08 | Vektorgrafik unter einer Fundstelle | verhalten dokumentieren (PyMuPDF-Option `graphics`) |
| S09 | Inkrementell gespeicherte Datei mit älterer Fassung (K10) | ältere Fassung nach Export nicht mehr enthalten (`garbage=3` reicht? prüfen, sonst `garbage=4, clean=True`) |
| S10 | Signiertes PDF | Signatur wird ungültig; GUI warnt vorher |
| S11 | Seitenvorschaubilder (Thumbnails) im PDF | entfernt oder neu erzeugt |
| S12 | Rekonstruktion über Glyphenbreiten: Länge des Balkens und Abstände verraten die Wortlänge | dokumentieren; optional Balken auf feste Mindestbreite oder Zeilenbreite |
| S13 | Datenhaltung auf dem Server: Upload und Ergebnis nach der Anfrage nicht im Dateisystem, nicht in Logs, nicht im Job-Speicher länger als nötig; Vorschau-JSON enthält Fundtexte, wird nicht protokolliert | Prüfung von `uploads/`, Container-Logs, `jobs.py` |
| S14 | Anfrage ohne Anmeldung, fremde Job-IDs, CSRF | Zugriffsregeln wie bei den übrigen Werkzeugen |

### 5.3 Umfang und Leistung (L)

| Nr. | Testfall | Messgröße / Erwartung |
|---|---|---|
| L01 | K09 dünn und dicht: 50, 500, 2 000, 5 000 Seiten, Vorschau und Schwärzen getrennt | Laufzeit, Spitzen-RAM (`/usr/bin/time -v`), Größe vorher/nachher |
| L02 | Wo reißt das Zeitlimit von 300 s? | Seitenzahl/Fundstellendichte, ab der der Abbruch kommt; Fehlermeldung verständlich (V9) |
| L03 | 200 Begriffe gleichzeitig gegen 500 Seiten | Laufzeit linear statt quadratisch |
| L04 | KI-Namenserkennung auf 500 Seiten Fließtext | Laufzeit, RAM des spaCy-Modells, erster Aufruf (Modellladen) gesondert |
| L05 | Zwei und fünf parallele Anfragen | kein Blockieren anderer Werkzeuge, keine Speicherüberschreitung im Container |
| L06 | Vorschau mit mehr als 500 Fundstellen | Hinweis „gekürzt“ sichtbar, Gesamtzahl korrekt, Liste bleibt bedienbar |
| L07 | ReDoS: Zeilen mit 10 000 Ziffern, langen Leerzeichenfolgen, `a@a.a.a.a…` | jede Regex unter 100 ms je Zeile |
| L08 | Batch mit 50 Dateien, 200 MB gesamt | Laufzeit, Speicher, ZIP vollständig |

### 5.4 GUI und Bedienung (G)

Automatisiert mit Playwright, ergänzt um eine moderierte Sichtprüfung (manuell) mit zwei Testpersonen aus der Fachpraxis.

| Nr. | Testfall | Erwartung |
|---|---|---|
| G01 | Ablauf Einzelbegriff: Datei ablegen, Begriff, Bestätigung, Schwärzen, Download | Ergebnis heruntergeladen, Erfolgsmeldung mit Anzahl |
| G02 | Ablauf Muster: Standardmuster, Vorschau, Bestätigung, Schwärzen | Bestätigung wird bei jeder Änderung zurückgesetzt |
| G03 | Schaltfläche „Unwiderruflich schwärzen“ ohne Vorschau, in jedem Modus | gesperrt, bis eine Vorschau vorliegt (Entscheidung 19.11.2026; heute im Mustermodus optional, beim Einzelbegriff gar keine) |
| G04 | Fundstellen auf der Seite markiert, einzeln ab- und wieder auswählbar, Bereich nachbearbeitbar, fehlende Stelle ergänzbar | geschwärzt wird genau die bestätigte Auswahl (heute nur Liste, V8) |
| G05 | Mehrere Dateien ablegen | Weiterleitung zur Batch-Verarbeitung mit übernommener Auswahl |
| G06 | SpaCy fehlt | KI-Muster ausgegraut mit Hinweis; Batch mit `ki_namen` liefert 503 mit verständlicher Meldung |
| G07 | Fehlermeldungen: keine Fundstellen (422), zu große Datei, verschlüsselte Datei, Zeitüberschreitung | deutsch, verständlich, mit nächstem Schritt |
| G08 | Erklärtext „Wie erkennt die Schwärzung …“ | fachlich richtig, nicht zu lang, standardmäßig eingeklappt? (heute `open`) |
| G09 | Barrierefreiheit: Tastaturbedienung aller Schritte, Fokusreihenfolge, `aria-pressed`, Live-Region für Ergebnis, Kontrast der KI-Plakette, axe-core ohne schwere Verstöße | WCAG 2.1 AA |
| G10 | Mobil 390 px, Dunkelmodus | kein horizontales Scrollen, Lesbarkeit der Liste |
| G11 | Werkbank-Einbettung (`PdfWorkbench.vue`): Schwärzung als Werkzeug im Arbeitsplatz, Ergebnis-Rückübernahme, Verlauf/Rückgängig | Rückgängig vor dem Speichern möglich; nach dem Speichern unumkehrbar |
| G12 | Texte nach Sprachregeln: Umlaute, einheitliche Begriffe („Fundstelle“, „Schwärzung“) | Abgleich mit Skill `deutsche-formulierung` |
| G13 | Dateiname des Ergebnisses | Namensschema der Werkbank (`JJJJMMTT_Name.pdf`) oder `_geschwaerzt`; einheitlich mit anderen Werkzeugen |

### 5.5 KI-Namenserkennung (K)

| Nr. | Testfall | Erwartung |
|---|---|---|
| K-01 | K08 mit 200 Namen | Trefferquote, Genauigkeit, F1; Fehlerklassen (übersehen, Teilname, Fehlalarm) |
| K-02 | Gleicher Text zeilenweise vs. absatzweise an das Modell gegeben | Messung des Kontexteffekts (V10) |
| K-03 | `de_core_news_sm` gegen `de_core_news_lg` bzw. ein transformerbasiertes Modell | Güte gegen Laufzeit und RAM |
| K-04 | Namen in Tabellen, Unterschriftenzeilen, Verteilern | getrennt auswerten |
| K-05 | Kombination KI + Begriffsliste | doppelte Treffer werden nicht doppelt gezählt |
| K-06 | Rechtliche Einordnung: lokale Verarbeitung, keine Übermittlung, Transparenzhinweis in GUI und Datenschutzerklärung, Einstufung nach KI-Verordnung | Abgleich mit `DatenschutzView.vue` |

### 5.6 Batch (B)

| Nr. | Testfall | Erwartung |
|---|---|---|
| B01 | K11 mit Standardmustern | ZIP mit allen Dateien, `schwaerzungen.txt` je Datei mit Fundstellen, `fehler.txt` für die fehlerhafte |
| B02 | Datei ohne Treffer | wird unverändert übernommen oder klar ausgewiesen; Sollverhalten festlegen |
| B03 | Vorschau im Batch | Pflicht wie im Einzelmodus: Fundstellen je Datei anzeigen und abwählbar, erst dann schwärzen (heute keine Vorschau) |
| B04 | 51 Dateien, 201 MB | Ablehnung mit Meldung |
| B05 | Nachvollziehbarkeit: Protokoll enthält Datei, Seite, Muster, Fundtext | Protokoll selbst enthält die geschwärzten Daten → Hinweis zur getrennten Aufbewahrung |

### 5.7 Robustheit (R)

| Nr. | Testfall | Erwartung |
|---|---|---|
| R01 | Verschlüsseltes PDF mit Öffnungspasswort | verständliche Ablehnung |
| R02 | Nur Rechteschutz (Bearbeiten verboten) | Verhalten dokumentieren |
| R03 | Beschädigte Datei, Nicht-PDF mit `.pdf`-Endung | 400 mit Meldung, kein 500 |
| R04 | PDF/A-Datei | Ergebnis bleibt PDF/A-konform oder Hinweis (veraPDF) |
| R05 | Portfolio, XFA-Formular | Ablehnung oder Warnung |
| R06 | Fehler mitten im Schwärzen | keine halbe Datei ausgeliefert |

## 6. Kennzahlen und Abnahmekriterien

Für jedes Muster und die KI-Namenserkennung werden aus Soll- und Ist-Liste berechnet:

- **Trefferquote** (Recall) = gefundene Soll-Treffer / alle Soll-Treffer
- **Genauigkeit** (Precision) = richtige Treffer / alle Treffer
- **Restdatenfunde** = Vorkommen des geschwärzten Texts in der Ergebnisdatei, gleich an welcher Stelle

| Kriterium | Abnahmeschwelle |
|---|---|
| Restdatenfunde im Seiteninhalt | 0 |
| Restdatenfunde in Formularfeldern, Metadaten, Kommentaren, Lesezeichen | 0 oder ausdrückliche Warnung vor dem Schwärzen |
| Trefferquote Regex-Muster auf K02 (im unterstützten Format) | ≥ 99 % |
| Genauigkeit Regex-Muster auf K03 | ≥ 95 %, Fehlalarme in Rechtsgrundlagen = 0 |
| Trefferquote Begriffsliste | 100 % auf einer Zeile; Zeilenumbruch gefunden oder gewarnt |
| KI-Namenserkennung | Kennzahlen dokumentiert; GUI-Hinweis entspricht der gemessenen Güte |
| Vorschau = Ergebnis | 100 % übereinstimmend |
| Laufzeit 500 Seiten dicht | < 60 s, mit Fortschrittsanzeige ab 10 s |
| GUI | keine schweren axe-Verstöße; beide Testpersonen schaffen G01 und G02 ohne Hilfe |

## 7. Vergleich mit kommerziellen Programmen

Vergleichsgruppe: Adobe Acrobat Pro, Foxit PDF Editor, Nitro PDF Pro, PDF-XChange Editor sowie als Bibliothek iText pdfSweep; für den Behördeneinsatz zusätzlich eine Fachlösung für Informationsfreiheitsanfragen (z. B. Objective Redact). Die Angaben zu Fremdprodukten werden im Testlauf an aktuellen Herstellerunterlagen bzw. einer Testversion belegt; ohne Beleg bleibt eine Zelle offen.

**Vorgehen:** Testversionen stehen nicht zur Verfügung (Entscheidung 19.11.2026). Der Vergleich stützt sich deshalb auf Handbücher, Hilfeseiten und Funktionslisten der Hersteller. Jede Zelle bekommt eine Quelle mit Abrufdatum, Zellen ohne Quelle bleiben offen. Messwerte zu Fremdprodukten werden nicht behauptet.

| Merkmal | pdf-editor heute | Prüffrage für die Vergleichsprogramme |
|---|---|---|
| Echte Entfernung des Seiteninhalts | ja (PyMuPDF `apply_redactions`) | gleichwertig? |
| Zweistufiges Verfahren: erst markieren, prüfen, dann anwenden | nur Liste, Anwenden in einem Schritt | Markierungen auf der Seite sichtbar, einzeln annehmen/ablehnen? |
| Bereinigung versteckter Inhalte (Metadaten, Kommentare, Anhänge, Formularfelder, Ebenen, JavaScript) | nein (V1, V2) | eigene Funktion „Dokument bereinigen“? automatisch beim Schwärzen? |
| Vordefinierte Muster | 9 deutsche Muster | welche, mit Prüfsummen? |
| Eigene Muster (Regex) | nein, nur Begriffe | frei definierbar und speicherbar? |
| Namenserkennung | spaCy klein, lokal | KI-gestützt, lokal oder Cloud? |
| Schwärzungsgrund / Beschriftung des Balkens | nein | Rechtsgrundlage im Balken oder als Vermerk? |
| Ganze Seiten oder Seitenbereiche schwärzen | nein | ja? |
| Bilder und Scans (OCR vor dem Schwärzen) | nein, keine Warnung (V7) | OCR integriert? |
| Schwärzungsprotokoll | nur im Batch | Bericht mit Grund, Seite, Bearbeiter? |
| Batch | ja, bis 50 Dateien | ja? mit Vorschau? |
| Wiederverwendbare Profile („Akteneinsicht Standard“) | nein | ja? |
| Datenhaltung | eigener Server, keine Cloud | lokal oder Cloud-Verarbeitung? |
| Kosten / Lizenz | AGPL, frei | Lizenzkosten je Arbeitsplatz |

## 8. Vorläufige Verbesserungsliste

Die Liste wird nach dem Testlauf mit den Messwerten priorisiert. Vorläufige Reihenfolge nach Risiko:

1. **Restdaten beseitigen (V1, V2):** Beim Schwärzen Formularfelder mit Treffer entfernen bzw. leeren, Metadaten und XMP leeren, Kommentare, Lesezeichen und Anhänge nach den Mustern durchsuchen und bereinigen; zusätzlich ein Schalter „Dokument bereinigen“ (PyMuPDF `scrub()`), standardmäßig an. Ergebnis mit `garbage=4, clean=True` speichern.
2. **Einzelbegriff korrigieren (V3):** Groß-/Kleinschreibung über den Mustermodus umsetzen oder den Einzelbegriff ganz auf `redact_patterns` umstellen; damit erhält er auch die Vorschau.
3. **Muster schärfen (V5):** Prüfsummen für IBAN, Kreditkarte, Steuer-ID; Telefon mit Wortgrenzen und ohne Treffer innerhalb anderer Treffer; Aktenzeichen und IP-Adresse aus den Standardmustern nehmen oder mit Ausschlussliste für Rechtsgrundlagen versehen; überlappende Treffer zusammenführen.
4. **Scans erkennen (V7):** Seiten ohne Textebene zählen und vor dem Schwärzen warnen; OCR-Werkzeug als Vorstufe anbieten.
5. **Vorschau auf der Seite (V8, V6):** Fundstellen als Markierung im Seitenbild, einzeln abwählbar, Vorschautext = tatsächlich geschwärzter Bereich; manuelles Ergänzen per Rechteck im selben Ablauf.
6. **Zeilenübergreifende Suche (V4):** Zeilen eines Blocks zusammenhängend durchsuchen, Silbentrennung auflösen; KI-Namenserkennung absatzweise (V10).
7. **Große Dokumente (V9):** Schwärzung als Hintergrund-Job (`jobs.py`) mit Fortschritt; Fundstellen aus der Vorschau wiederverwenden statt neu suchen.
8. **Verwaltungsfunktionen:** Schwärzungsprotokoll auch im Einzelmodus, speicherbare Profile (Schwärzungsgründe nicht gewünscht, Entscheidung 19.11.2026).
9. **Testabdeckung:** Korpus und Soll-Listen als dauerhafte Regressionstests in `backend/tests/`; Playwright-Tests für die GUI (bisher kein Frontend-Testwerkzeug im Projekt).

## 9. Ablauf und Aufwand

| Phase | Inhalt | Ergebnis | Aufwand (geschätzt) |
|---|---|---|---|
| 1 | Korpus-Generator und Soll-Listen (K01–K11) | Fixtures, `erwartet.json` | 1 Tag |
| 2 | Automatisierte Backend-Tests F, S, L, K, B, R | pytest-Suite, Kennzahlenbericht | 1,5 Tage |
| 3 | Forensik-Prüfung S01–S12 mit Fremdwerkzeugen | Restdatenbericht | 0,5 Tag |
| 4 | GUI-Tests G01–G13 mit Playwright, axe, Sichtprüfung | Screenshots, Befundliste (`@frontend-e2e`, `@ux-review`) | 1 Tag |
| 5 | Vergleich anhand von Herstellerunterlagen (keine Testversionen vorhanden) | Vergleichstabelle mit Quellen | 0,5 Tag |
| 6 | Auswertung, Priorisierung der Verbesserungen | Prüfbericht mit Maßnahmenliste | 0,5 Tag |

Phasen 1–3 laufen ohne Nutzerentscheidung. Für Phase 5 braucht es Testversionen der Vergleichsprogramme; für die Sichtprüfung in Phase 4 zwei Testpersonen.

## 10. Entscheidungen (19.11.2026)

- **Vorschau ist Pflicht.** Geschwärzt wird erst nach einer Vorschau, und zwar in allen Modi (Einzelbegriff, Muster, Batch). In der Vorschau lassen sich einzelne Fundstellen abwählen und wieder auswählen sowie nachbearbeiten (Bereich ändern, fehlende Stelle ergänzen). Geschwärzt wird genau die bestätigte Auswahl, nicht ein neuer Suchlauf. Daraus folgen die Testfälle G03, G04, F09 und die Verbesserungen 2 und 5 als Pflichtumfang.
- **Keine kommerziellen Vergleichsprogramme vorhanden.** Phase 5 wird zum Vergleich auf dem Papier: Herstellerunterlagen und öffentliche Dokumentation, jede Angabe mit Quelle. Messungen an Fremdprodukten entfallen; die Forensik S01–S12 läuft nur auf den eigenen Ergebnissen.
- **Keine Schwärzungsgründe.** Verbesserung 8 schrumpft auf Schwärzungsprotokoll und speicherbare Profile.
- **Keine vorhandene Vorlage und kein vorhandenes Korpus.** Das Korpus wird nach Abschnitt 4.2 neu erzeugt.
- **Rechenbedarf:** Die Schwärzung läuft vollständig auf der CPU, auch die KI-Namenserkennung (`de_core_news_sm`). Eine GPU wäre erst bei einem Transformer-Modell sinnvoll (K-03).

Offen ist nur noch, ob das Bereinigen versteckter Inhalte automatisch mitlaufen oder als eigener Schritt angeboten werden soll. Vorschlag: automatisch an, mit Liste der bereinigten Stellen in der Vorschau.

## 11. Umsetzungsstand (20.11.2026)

Schritt 1 aus dem [Plan für auditcore](plan-schwaerzung-auditcore.md) ist umgesetzt. Kern ist das neue Modul `backend/app/services/redaction.py`. Ablauf und Datenformat stehen in [schwaerzung-plan-format.md](schwaerzung-plan-format.md). Die Tests liegen in `backend/tests/test_redaction_audit.py` (Korpus `redaction_corpus.py`); die früheren `xfail`-Markierungen sind entfernt.

| Nr. | Stand | Umsetzung, Nachweis |
|---|---|---|
| V1 | behoben | Formularfelder mit Treffer werden entfernt (S05, G01, G09). |
| V2 | behoben | Treffer in Metadaten, XMP, Lesezeichen, Kommentaren, Links und Anhängen sind eigene Fundstellen in der Vorschau. Beim Schwärzen werden sie entfernt oder geleert, zusätzlich läuft die Bereinigung „Dokument bereinigen“ (`scrub`, standardmäßig an) (S03, S04, S06, G09). |
| V3 | behoben | Der Einzelbegriff läuft über dieselbe Suche, Groß-/Kleinschreibung wirkt (F05). |
| V4 | behoben | Treffer über Zeilenumbrüche hinweg, Silbentrennung wird aufgelöst, Spalten bleiben getrennt (F06, F07). |
| V5 | behoben | Prüfziffern für IBAN, Kreditkarte und Steuer-ID, echtes Kalenderdatum, Kontextregeln für Telefon, IP-Adresse und Aktenzeichen, Überlappungen aufgelöst (F01–F03). |
| V6 | behoben | Geschwärzt wird zeichengenau. Vorschautext und geschwärzte Fläche stimmen überein (F08). |
| V7 | behoben | `pages_without_text` im Plan, Warnung in der Oberfläche (G12). |
| V8 | behoben | Vorschau ist in allen Modi Pflicht: Seitenansicht mit markierten Fundstellen, einzeln oder gruppenweise abwählbar, eigene Bereiche, mehrere Dateien mit Status „geprüft“. Die Batch-Verarbeitung übergibt ans Schwärzen-Werkzeug (G02–G06, G10, Browsertest). |
| V9 | teilweise | Siehe Messung unten. Kein Hintergrund-Job; der Plan wird beim Anwenden zur Absicherung neu berechnet. |
| V10 | behoben | Die KI-Namenserkennung läuft je Seite auf dem ganzen Seitentext (K01, G14). |
| V11 | behoben | Der Importschutz fängt jede Ausnahme ab. `requirements.txt` ist auf spaCy 3.8 und das Modell 3.8.0 angehoben (siehe unten). |
| V12 | behoben | Mehr als 200 Begriffe ergeben HTTP 400 statt stiller Kürzung (F10, G11). |
| V13 | behoben | Das IBAN-Ende ergibt sich aus der Prüfziffer (F01). |
| V14 | behoben | Eine verschlüsselte Datei ergibt HTTP 400 mit Hinweis „passwortgeschützt“ (R01). |
| V15 | behoben | Eine Datei ohne PDF-Inhalt ergibt HTTP 400 (R03). |

**Fail-closed:** Nach dem Schwärzen wird die Ausgabe erneut durchsucht, und zwar im Seitentext, in den versteckten Ablagen und in den entpackten Rohdaten. Findet die Nachprüfung noch einen ausgewählten Text, wird keine Datei ausgeliefert (HTTP 422, Test G08). Gezählt wird lageunabhängig, weil MuPDF nach dem Entfernen von Glyphen den Rest einer Zeile teils um einige Punkt verschiebt. Ein Rechteckvergleich hätte deshalb Fehlalarme erzeugt.

**Messung V9 (19.11.2026, gleiche Maschine wie Probe Nr. 6):** Gemessen wurde mit 500 dichten Seiten. Das ergibt 45 000 Fundstellen; früher waren es 112 500, weil sich die Treffer überlappten. Der Plan dauert 5,2 s, das Anwenden einschließlich erneuter Suche und Nachprüfung 46 s. Nach den Nachbesserungen aus der Code-Prüfung (unten) sind es 5,3 s und 51 s; dazu kommen die erweiterte Rohdatenprüfung und das Freilegen der ganzen Seite. Die Plan-Antwort ist dabei 13 MB groß. Das Zeitlimit von 300 s würde bei dieser Dichte erst bei etwa 3 000 Seiten erreicht. Offen bleibt ein Hintergrund-Job mit Fortschrittsanzeige für noch größere Akten.

**Abhängigkeiten (V11):** Eine frische Umgebung mit spaCy 3.8.18, numpy 2.5, pandas 3.1 und `de_core_news_sm` 3.8.0 wurde aus `requirements.txt` aufgebaut. Darin laufen alle Schwärzungstests, auch die mit der KI-Namenserkennung.

### 11.1 Befunde der unabhängigen Code-Prüfung (19. und 20.11.2026)

Ein Agent (`@code-audit`) hat den Stand nach Schritt 1 geprüft, ein zweiter (`@frontend-e2e`) die Oberfläche im Browser. Eine zweite Code-Prüfung am 20.11.2026 hat die Korrekturen nachgeprüft. Sie bestätigte H2 bis H4 und M1 bis M7 als geschlossen, K1, H1 und M5 nur als teilweise geschlossen und fand die Lücken H-N1 und M-N1 bis M-N7. Diese sind unten nachgetragen. Eine dritte Prüfung derselben Art hat danach noch acht Punkte gefunden (N3-1 bis N3-8), ebenfalls nachgetragen. Lücken in der Nachprüfung wurden zusätzlich mit eigenen Prüfdateien nachgestellt (Kopie, Ebenen, Boxen, Formularfelder, Strukturbaum). Die Regressionstests stehen in `test_redaction_audit.py` unter `test_a_*`.

| Nr. | Befund | Stand | Umsetzung, Test |
|---|---|---|---|
| K1 | Nachprüfung übersah Schreibvarianten, gleiche Texte und verschachtelte Begriffe | behoben (Rest in M-N2) | Zählung je Seite und für versteckte Ablagen in flacher Form (NFKC, ohne Groß-/Kleinschreibung und Leerraum). Rohdatenprüfung in mehreren Kodierungen und Schreibweisen. Auswahlfelder und Kommentare, die eine Schwärzung berühren, werden entfernt (`test_a_k1_*`). |
| H1 | Text auf ausgeblendeten Ebenen, außerhalb der MediaBox, in `ActualText`/`Alt`, `PieceInfo`, XFA und eigenen Info-Schlüsseln blieb stehen | behoben (Reste in H-N1, M-N6) | Ebenen werden für Suche und Schwärzung eingeblendet und danach wieder ausgeblendet. Die Suche läuft ohne Beschnitt. Zeichenketten in Objekten und Inhaltsströmen werden ersetzt. XFA wird immer entfernt, ebenso XMP mit geschwärztem Text, auch auf Seitenebene (`test_a_h1_*`). |
| H2 | HTTP 500 und falsche Anzeigelage bei versetzter MediaBox | behoben | Ursprung der Anzeige aus CropBox minus MediaBox, ganze Seite als `Rect(x0, 0, x1, Höhe)` (`test_a_h2_offset_mediabox`). |
| H3 | Rechenlast über sehr viele eigene Bereiche | behoben | Höchstens 500 Bereiche, 100 je Seite. Die Oberfläche meldet die Grenze (`test_a_h3_area_limits`). |
| H4 | Begriffe nicht gefunden bei Ligatur, NFD, Nullbreite, ß/SS, Doppelnamen über Zeilenumbruch, geteilter Grundlinie | behoben | Normalisierung im Seitentext und im Suchmuster (`test_a_h4_*`). |
| M1 | Alte Endpunkte schwärzten ohne Vorschau | behoben | HTTP 410, außer bei `PDFAPP_REDACT_WITHOUT_PREVIEW=true` (`test_a_m1_*`). |
| M2 | Stapel übernahm Dateien ohne Auswahl unbereinigt | behoben | Mit `sanitize` wird bereinigt und nachgeprüft (`_bereinigt.pdf`, G10). |
| M3 | Nachprüfung eigener Bereiche lief auf beschnittenen Seiten ins Leere | behoben | Umrechnung vor dem Freilegen der Seite (`test_a_m3_*`). |
| M4 | 1-MB-Grenze für das Formularfeld `plan` | behoben | Datei-Teil `plan_file`/`plans_file` bis 8 MB, die Oberfläche nutzt ihn (`test_a_m4_*`). |
| M5 | Fehlerhafte Auswahl ergab HTTP 500 | behoben (Rest in M-N7) | Typprüfung, HTTP 400 (`test_a_m5_*`). |
| M6 | Verhalten hing von der PyMuPDF-Version ab | behoben | `PyMuPDF>=2.1,<3` in `requirements.txt`. |
| M7 | Begriff in abgewählter E-Mail-Adresse wurde verdeckt und blieb lesbar | behoben | Begriffe weichen nur Begriffen (`test_a_m7_*`). |
| B1 | Dateiauswahl nahm nur eine Datei | behoben | `FileDrop` mit `multiple`. |
| B2 | Fokusring auf Fundstellen unsichtbar | behoben | `focus-visible`-Umriss. |
| B3 | Fundstellen auf 390 px kaum antippbar | teilweise | Bedienelemente der eigenen Bereiche auf kleinen Bildschirmen vergrößert (siehe F2). Die Fundstellen selbst bleiben maßstabsgetreu; für Touch ist die Liste neben der Seite der Weg. |
| B4 | Ecke zum Vergrößern nicht per Tastatur erreichbar | behoben | Schaltfläche mit Pfeiltasten, Umschalt für größere Schritte. |
| F1 | Nachtest im Browser: HTTP 422, wenn ein Begriff in einer ausgewählten E-Mail-Adresse steckt und derselbe Name anderswo abgewählt ist | behoben | Die Nachprüfung zieht Vorkommen jetzt nach Lage ab: Überlappende ausgewählte Stellen zählen einmal. Die Tests `test_a_f1_*` waren vor der Korrektur rot. |
| F2 | Nachtest im Browser: × und Ecke auf 390 px nur 24 bzw. 20 px groß | behoben | Unsichtbare Trefferfläche von 44 px auf kleinen Bildschirmen. |
| H-N1 | Ausgewählter Name blieb im Alternativtext lesbar (HTTP 200), wenn ein längeres Wort wie „Krausestr.“ sichtbar blieb | behoben | Alternativ- und Ersatztexte (`Alt`, `ActualText`, `E`, `TU`) werden immer ersetzt, sobald sie einen geschwärzten Text enthalten. Ein Rohdatentreffer gilt nur noch als entschuldigt, wenn derselbe Text als ganzes Wort lesbar bleibt (`test_a_hn1_*`). |
| M-N1 | Abgewähltes Lesezeichen wurde überschrieben, wenn derselbe Begriff in einer ausgewählten E-Mail-Adresse stand | behoben | „Nur an ausgewählten Stellen“ richtet sich nach denselben lagebezogenen Grenzen wie die Nachprüfung (`test_a_mn1_*`). |
| M-N2 | Teilausfall einer Fundstelle über zwei Zeilen („Max / Mustermann“, IBAN) blieb unbemerkt | behoben | Jede Zeile einer mehrzeiligen Fundstelle wird einzeln nachgezählt (`test_a_mn2_*`). |
| M-N3 | Lesezeichen mit Nullbreitenzeichen oder weichem Trennzeichen blieb teilweise lesbar | behoben | Bereinigte Vergleichsform; bleibt ein Treffer übrig, wird der ganze Titel ersetzt. MuPDF liefert das weiche Trennzeichen als NUL-Zeichen, das jetzt ebenfalls entfällt (`test_a_mn3_*`). |
| M-N4 | Fehlalarm (HTTP 422) durch Namen in eingebetteten Schriften, etwa „Vera“ in „Bitstream Vera“ | behoben | Schriftdateien (`FontFile`, `FontFile2`, `FontFile3`) zählen nicht zur Rohdatenprüfung (`test_a_mn4_*`). |
| M-N5 | 160 s für 8 000 E-Mail-Adressen und 40 000 Zeichenketten | behoben | Vorauswahl über Präfixe statt langer Alternativen, Begriffsindex beim Ersetzen von Zeichenketten. Jetzt 13,5 s für denselben Fall, 4,5 s für 2 000 Adressen (`test_a_mn5_*`). |
| M-N6 | Ebene über eine Sichtbarkeitsregel (`/OCMD` mit `/P /AllOff` oder `/VE`) ausgeblendet: Text wurde nicht gefunden | behoben | Regeln werden für Suche und Schwärzung auf „sichtbar“ gestellt und danach wiederhergestellt. Scheitert das Einblenden mittendrin, wird das bereits Geänderte zurückgesetzt (`test_a_mn6_*`). |
| M-N7 | HTTP 500 bei `Infinity`, `1e400`, `NaN` oder tiefer Schachtelung im Plan; `NaN` hätte die ganze Seite geschwärzt | behoben | JSON ohne Sonderwerte, nur endliche Zahlen, Seitenzahl als ganze Zahl; Schachtelungsfehler ergeben HTTP 400 (`test_a_mn7_*`). |
| N3-1 | Ebene mit `/Usage/View/ViewState /OFF`: MuPDF blendet sie aus, Plan und Nachprüfung sahen den Text nicht (HTTP 200 mit Rest auf der Ebene) | behoben | `Usage` wird an allen Ebenen für Suche und Schwärzung entfernt und danach wiederhergestellt (`test_a_n3_1_*`). |
| N3-2 | Falscher 422, wenn ein Wort im Inhaltsstrom in Stücken steht („(Krause) Tj (straße) Tj“) | behoben | Treffer in Inhaltsströmen von Seiten und Form-XObjects gelten als entschuldigt, wenn der Text Teil des Sichtbaren ist; außerhalb bleibt der wortgenaue Vergleich (`test_a_n3_2_*`). |
| N3-3 | Alternativtext als eigenes Objekt (`/Alt 12 0 R`) blieb stehen, wenn derselbe Name anderswo abgewählt war | behoben | Objekte, auf die `Alt`, `ActualText`, `E` oder `TU` verweisen, werden wie Alternativtexte behandelt (`test_a_n3_3_*`). |
| N3-4 | Eine kurze Form („Anna“) bremste die Suche nach vielen langen Formen (9,7 s) | behoben | Formen werden nach Länge gruppiert, je Gruppe eigener Anfang. Derselbe Fall braucht jetzt 0,03 s (`test_a_n3_4_*`). |
| N3-5 | Kurze Begriffe (1–2 Zeichen) ersetzten fremde Alternativtexte („AB“ in „Abbildung“) | behoben | Kurze Begriffe zählen nur als ganzes Wort; Zeilenteile mehrzeiliger Fundstellen erst ab drei Zeichen (`test_a_n3_5_*`). |
| N3-6 | Sichtbarkeitsregeln direkt in den Ressourcen (`/Properties << /MD1 << /Type /OCMD … >> >>`) wurden nicht eingeblendet | behoben | Auch eingebettete Regeln werden eingeblendet und wiederhergestellt (`test_a_n3_6_*`). |
| N3-7 | Wiederherstellung schrieb `/P null` statt den Schlüssel zu entfernen und verlor Werte in Zeichenkettenform | behoben | Zeichenketten werden als solche zurückgeschrieben, ausdrückliche `null`-Schlüssel entfernt (`test_a_n3_7_*`). |
| N3-8 | Oberfläche: Zusatzdatei bei voller Liste verwarf alle Pläne; „Datei geladen“ vor der Ablehnung wegen Gesamtgröße | behoben | Pläne verfallen nur, wenn wirklich eine Datei dazukommt. Die Dateiauswahl kennt den verbleibenden Platz und lehnt vorher ab. |

Außerdem in der Oberfläche:

- Die Bestätigung wird zurückgesetzt, sobald sich Auswahl, Bereiche oder der Status „geprüft“ ändern.
- Wird eine Datei vor der angezeigten entfernt, bleibt die Ansicht auf derselben Datei.
- Die Gesamtgröße aller Dateien wird vor der Suche geprüft, auch für Dateien, die aus einem anderen Werkzeug übergeben werden.

Die zwölf neuen Tests zu H-N1 und M-N1 bis M-N6 (ohne M-N7, dessen Korrektur in der Schnittstelle liegt) schlagen auf dem Stand vor der zweiten Korrektur fehl, von den zehn Tests zu N3 sieben auf dem Stand davor; die übrigen drei sind Gegenproben.

**Testlauf 20.11.2026:** 343 Backend-Tests bestanden, alle Schwärzungstests eingeschlossen. Fünf Tests schlagen in dieser Umgebung fehl, keiner betrifft die Schwärzung:

- vier in `test_form_advanced` (Formularberechnung), schon vor diesen Änderungen rot;
- `test_to_excel_preview_zeigt_tabelleninhalt`, weil `tabula` Java braucht und Java hier fehlt.

`vue-tsc` und der Produktions-Build laufen ohne Fehler. Ein auditcore-runner-Prüfprofil hat das Repository nicht.

