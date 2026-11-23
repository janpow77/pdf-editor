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

### 11.2 Browserprüfung (20.11.2026)

`@frontend-e2e` hat den Stand im Browser geprüft, mit Produktions-Build und laufendem Backend. Geprüft wurden:

- der Einzelablauf mit Abwahl und eigenem Bereich;
- der Batch mit Vorschau je Datei;
- Ablehnungen wegen Dateityp, Dateigröße, Gesamtgröße und voller Liste;
- ein simulierter 422;
- die Konsole;
- die Smartphone-Breite (390 px).

Die Ergebnis-PDFs wurden mit PyMuPDF nachgeprüft: Ausgewählte Texte fehlen, abgewählte sind noch da. Es gab keine JS-Fehler. Gefunden wurden fünf Punkte, alle behoben und in einer zweiten Runde im Browser bestätigt:

| Nr. | Befund | Stand | Korrektur |
|---|---|---|---|
| E-1 | Ab etwa 30 Dateien liefen die Plan-Anfragen in das Rate-Limit (30 je Minute). Die Meldung riet zum Entfernen, und ein erneutes Suchen verwarf auch die fertigen Pläne. | behoben | Der Server nennt bei 429 die Wartezeit (`Retry-After`). Die Suche wartet bis 90 s und wiederholt bis zu fünfmal je Datei, die Restzeit steht auf der Schaltfläche. Ein erneutes Suchen holt nur die fehlenden Pläne (`test_rate_limit_sends_retry_after`). |
| E-2 | Bei voller Liste erschien zuerst „Datei geladen“, dann die Ablehnung. | behoben | Die Dateiauswahl lehnt bei voller Liste sofort ab. |
| E-3 | Bei überschrittenem Restplatz klang die Meldung wie ein Dateilimit. | behoben | Die Meldung nennt den Restplatz bis zur Gesamtgröße. |
| E-4 | Eine Mehrfachauswahl über der Gesamtgröße wurde ganz abgelehnt. | behoben | Passende Dateien werden übernommen, nur die übrigen werden mit Namen abgelehnt. |
| E-5 | Nach einem 422 blieben die alten Pläne stehen, die Meldung sprach aber von neuer Suche. | behoben | Pläne werden dann verworfen, die Ansicht springt zu den Suchkriterien. |

### 11.3 KI-Namenserkennung in Tabellen (20.11.2026)

An einer aus Excel erzeugten Anwesenheitsliste (erfundene Namen) fand die KI-Namenserkennung allein nur einen Teil der Namen.

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-1 | Im Seitentext zog spaCy Namen aus Nachbarzellen zu einem Treffer zusammen oder erkannte sie nicht. | behoben | Treffer werden an Zellgrenzen geteilt. Jeder kurze Zellinhalt (höchstens sechs Wörter) wird zusätzlich einzeln erkannt. |
| T-2 | „Nachname, Vorname“ wurde oft nicht oder als Ort erkannt. | behoben | Die Listenform zählt, wenn die KI die Umstellung „Vorname Nachname“ als Person erkennt. |
| T-3 | Allein stehende Nachnamen („Reiter“) wurden nie erkannt. | behoben | Die Bestandteile belegter Namen werden im ganzen Dokument wortgenau nachgesucht. Belegt ist ein Name, den die KI aus mindestens zwei Bestandteilen erkennt (Initialen zählen mit) oder den die Listenform bestätigt. Nicht nachgesucht wird nach einem Artikel („der Richter“, aber nicht „von der Heide“) und beim Monatskürzel im Datum („15. Jan.“). Die nachgesuchten Treffer bilden in der Vorschau eine eigene Gruppe „Namen (im Dokument nachgesucht)“. Ein Nachname, der nirgends belegt ist, bleibt unerkannt; für unbestätigte Zellbelege gilt die Grenze aus T-5. |
| T-4 | Mit „Prof. Dr.“ davor erkannte spaCy keinen Namen. | behoben | Führende Titel werden vor der Einzelerkennung abgeschnitten; der Titel bleibt lesbar. |

Zeilen eines Absatzes werden bewusst nicht einzeln erkannt: Ohne Satzzusammenhang meldete spaCy dort „Förderantrag“ als Namen. Die Anwesenheitsliste wird vollständig erkannt, im Fließtext-Korpus bleibt die Trefferquote gleich.

Die unabhängige Code-Prüfung desselben Tages ergab dazu:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-5 | Die Nachsuche vervielfachte Fehltreffer: Tabellenköpfe („Förderquote“, „Summe Netto“), Substantive („der Richter“), „Jan“ im Datum. | behoben, Rest offen | Nach Art des Belegs (siehe T-16, T-22): Ohne Grenze nachgesucht werden Namen aus einem Satz (ein kleingeschriebenes Wort in derselben Zelle, in der sichtbaren Zeile des Treffers oder direkt davor oder danach; Wörter wie „in“, „je“, „und“, „inkl“, „lt“ zählen nicht), aus der Listenform und aus einer Zelle, deren Namen die KI im Mustersatz „Gestern habe ich … getroffen.“ vollständig als Person bestätigt. Für unbestätigte Zellbelege gilt max(10, 4 × verschiedene direkte Fundstellentexte). Mindestens 50 gelten für Belege über Zellgrenzen mit Bestätigung und für Zellbelege, deren Namen der Mustersatz nur zum Teil bestätigt („Thomas Berger“ aus „Auftragnehmer Thomas Berger“). Darüber bleiben nur Stellen mit Anrede oder Titel davor („Herr“, „Frau“, „Hr.“, „Fr.“, „Dr.“, „Dr. med.“, „Dr.-Ing.“, „Dipl.-Ing.“, „Dipl.-Ing. (FH)“, „Dipl.-Ök.“, „Prof.“). Kontaktwörter („Telefon“, „Telefonnummer“, „Telefax“, „Fax“, „Tel“, „Mobil“, „Handy“, „Durchwahl“, auch in „Telefon-Nr“ oder „Telefon/Fax“) werden nie nachgesucht. Häufige Spaltenköpfe („Pos“, „Menge“, „Summe“, „Betrag“, „Netto“, „Brutto“ und weitere) werden aus Zellbelegen nur mit Anrede davor nachgesucht; aus einem Satz oder der Listenform neben einem anderen Wort, einer Anrede oder einem Titel belegt, gelten sie als Nachname („Petra Preis“, „Menge, Wolfgang“, „Dr. Menge“). Besteht ein solcher Beleg nur aus Spaltenköpfen („Summe Netto nach Skonto“, „Netto, Brutto“), gilt er als Zellbeleg. Ein Spaltenkopf als Etikett („Summe Thomas Berger“) macht den Beleg zur Teilbestätigung mit der Grenze 50. Dazu die Ausnahmen aus T-3. Offen: Was die KI direkt meldet, bleibt Fundstelle, auch ein Fehltreffer („Telefon“, „Netto“ im Fließtext); das war schon vor der Tabellenerkennung so. Der Mustersatz bestätigt auch manche Paare aus Spaltenköpfen („Netto Brutto“, „Pos Menge“); was nicht auf der Liste der Spaltenköpfe steht, kann so bis zur Grenze nachgesucht werden. In der Vorschau lässt sich die Gruppe gesammelt abwählen; ohne Vorschau (Batch) wird geschwärzt. |
| T-6 | Eine CropBox, die über die MediaBox hinausragt (zulässig), ließ die Vorschau mit KI und das Anwenden mit `ValueError` scheitern. | behoben | Der Seitentext wird für Suche und KI nur einmal ermittelt. Beim Anwenden wird der gespeicherte CropBox-Wert gesichert und unverändert zurückgeschrieben. |
| T-7 | Bei Tabellen verdreifachte sich die Laufzeit (50 Seiten: 8,3 s statt 2,7 s). | verbessert | Gleiche Zellinhalte prüft die KI nur einmal: 5,0 s statt 2,7 s. Fließtext: 80 Seiten 1,4 s statt 0,8 s. |
| T-8 | Spans der KI außerhalb des Textes ergaben `IndexError`. | behoben | Spans werden auf den Text begrenzt. |
| T-9 | Lücken der Nachsuche: Großschreibung („MÜLLER“), Binnenmajuskeln („McDonald“), Einzelteile von Doppelnamen (der ganze Doppelname wird nachgesucht), Namen unter drei Buchstaben, Silbentrennung. | offen | Bewusst nicht erweitert: Jede Lockerung erhöht die Fehltreffer aus T-5. |

Die Nachprüfung (fünfte Runde, 22.11.2026) ergab:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-10 | Rückschritt: Die Belegregel aus T-5 verwarf KI-Treffer mit Initiale oder fremden Buchstaben („A. Stahl“, „Ömer Çelik“) und einzelne Zellnamen („Atreides“), die vorher geschwärzt wurden. | behoben | Alles, was die KI meldet, wird wieder direkt übernommen; ein übersehener Name wiegt schwerer als ein abwählbarer Fehltreffer. Gegen die Vervielfachung wirkt die Obergrenze aus T-5. Initialen und Buchstaben außerhalb des deutschen Alphabets zählen als Bestandteile. |
| T-11 | Zwei Tabellenköpfe nebeneinander, eine Zweiwortzelle oder „Telefon, Telefax“ als Listenform belegten einen Fehltreffer und lösten massenhaft Nachsuche aus. | behoben | Grenze aus T-5. In den Belegen („Begünstigter“ 120×, „Summe“ 51× und 120× bei wiederkehrendem Spaltenkopf) entsteht mit echter KI kein Nachsuche-Treffer mehr. „Telefon, Telefax“ gilt seit T-23 nicht mehr als Listenform. |
| T-12 | „Jan.“ am Satzende und „von der Heide“ wurden nicht mehr nachgesucht. | behoben | Monatskürzel nur im Datum ausgenommen, Artikel nach „von“, „van“, „zu“, „ter“, „de“ nicht gewertet. |
| T-13 | Spans der KI wurden auf die Seite statt auf die Zelle begrenzt. | behoben | Begrenzung auf den Abschnitt. |
| T-14 | Die Vorschau hält alle Seitentexte zugleich (300 dichte Seiten: 185 MiB Python-Speicher statt 11 MiB). | teilweise | Ohne KI wird wieder seitenweise gesucht (2,5 MiB). Mit KI bleibt es dabei, weil die Nachsuche das ganze Dokument braucht; das Anwenden lag schon vorher in dieser Größenordnung. |
| T-15 | Ein Name kann in der Vorschau in zwei Gruppen stehen (direkt und nachgesucht); die neue Quelle steht nicht in `GET /redact/patterns`. | offen | Bewusst so: Abwählen einer Gruppe schwärzt über die andere weiter (sicher). Die Quelle ist im Planformat beschrieben. |

Die Nachprüfung (sechste Runde, 22.11.2026) ergab:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-16 | Die Obergrenze aus T-5 ließ häufige echte Namen ganz lesbar: spaCy erkennt „Thomas Berger“ einmal, „(Herr) Berger“ im Text nie; ab elf Nennungen wurde gar nicht mehr nachgesucht (60 von 61 lesbar). | behoben | Grenze nur noch für unbestätigte Zellbelege und Belege über Zellgrenzen hinweg (T-5), darüber Stellen mit Anrede oder Titel weiter geschwärzt. Belege: 60 von 60 „Berger“ aus dem Satz, 16 von 16 aus einer Tabellenzelle nachgesucht. |
| T-17 | Ein Spaltenkopf, der auf jeder Seite wiederkehrt, hob die Grenze mit jeder Seite an („Summe“ 40× nachgesucht). | behoben | Gezählt werden verschiedene direkte Fundstellentexte. |
| T-18 | Doppelnamen („Meyer-Lüdenscheidt“, „Hans-Peter“) wurden nicht mehr nachgesucht. | behoben | Jeder Teil wird für sich auf Großschreibung geprüft. |
| T-19 | Die Nachsuche wuchs mit Zahl der Namen × Textlänge (300 Seiten × 150 Namen: 33 s). | behoben | Wörter werden einmal erfasst und nachgeschlagen: 0,7 s. |
| T-20 | Eine fehlerhafte KI-Funktion konnte die ganze Seite belegen oder einen Absturz (HTTP 500) auslösen. | behoben | Spans werden geklemmt; ein Ergebnis in falscher Form ergibt eine klare Fehlermeldung. |
| T-21 | Die Grenze war nicht getestet. | behoben | Tests für Grenzwert 10/11, Anrede, häufige Namen, Mustersatz, Spaltenkopf über Zellgrenzen, Doppelnamen und fehlerhafte KI. Fünf Mutationsproben blieben dabei unbemerkt; die Lücken schließt T-26. |

Die Nachprüfung (siebte Runde, 22.11.2026) ergab:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-22 | Schwer: Eine Kopfzeile aus nahen Spalten („Ort Telefon Begünstigter Betrag“) liest MuPDF als eine Zeile. Die Nachbarwörter galten als Satzzusammenhang, ein Fehltreffer darin wurde ohne Grenze nachgesucht („Betrag“ und „Telefon“ je 120×, „Summe“ 121×). | behoben, siehe T-27 | Als Satz zählt nur ein kleingeschriebenes Wort in derselben Zelle oder Zeile; sonst entscheidet der Mustersatz. In denselben Belegen kein Nachsuche-Treffer mehr; „Berger“ aus einem Satz weiter 60 von 60. Kopfzeilen mit „inkl.“ oder „in EUR“ blieben offen (T-27). |
| T-23 | „Telefon“, „Telefax“ bestanden Mustersatz und Listenform. | behoben | Kontaktwörter gelten nie als Namensteil und werden vor dem Mustersatz entfernt. |
| T-24 | Ein Name aus getrennten Spalten (Vorname &#124; Nachname) blieb ab elf Nennungen ganz lesbar. | teilweise | Bestätigt der Mustersatz das Paar, gilt eine Grenze von mindestens 50. Eine Freigabe ohne Grenze lässt der Mustersatz nicht zu, er bestätigt auch Paare aus Spaltenköpfen („Pos Menge“). Ohne Grenze wäre in einer Belegliste mit 300 Seiten „Betrag“ 3.587× geschwärzt worden. Über 50 Nennungen bleibt ein solcher Name ohne Anrede lesbar; so am 23.11.2026 entschieden. |
| T-25 | Der Mustersatz lief auf jede Zelle (300 dichte Seiten: 34.728 zusätzliche KI-Texte, 16 s). | behoben | Er läuft nur noch für Wörter, die sonst an der Grenze scheitern: 51 Texte, Vorschau 44 s → 30 s. |
| T-26 | Testlücken: Satzregel, Teilbestätigung im Mustersatz, Zellgrenzen-Regel, Titel und Faktor 4 waren nicht abgesichert. Eine fehlerhafte KI ergab HTTP 400, eine abstürzende HTTP 500. | behoben, siehe T-30 | Neue Tests dazu; von 26 Mutationsproben schlagen 25 an. Unbemerkt bleibt nur das Weglassen der Prüfung, ob ein direkter Treffer innerhalb eines Worts beginnt; das wirkt sich nur bei Teiltreffern in Bindestrichwörtern aus, die Überlappungsauflösung fängt es ab. Fehler der KI-Funktion ergeben jetzt HTTP 502 mit Meldung. Die Anrede erkennt auch „Hr.“, „Fr.“, „Dr. med.“, „Dr.-Ing.“. |

Die Nachprüfung (achte Runde, 23.11.2026) ergab:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-27 | Schwer: Kleine Wörter in einer Kopfzeile („Kostenart Summe Netto inkl. USt“, „… in EUR“) galten als Satz; „Summe“ und „Menge“ wurden je 301× nachgesucht. | behoben, siehe T-34 | Wörter wie „in“, „je“, „pro“, „bis“, „und“, „inkl“, „zzgl“, „lt“ zählen nicht als Satz. In denselben Belegen kein Nachsuche-Treffer mehr. |
| T-28 | Schwer: Meldete die KI das Etikett mit („Auftragnehmer Thomas Berger“) und bestätigte der Mustersatz nur den Namen, blieb der Name im Text lesbar (0 von 60). | behoben, siehe T-33 | Ein bestätigter Teil mit mindestens zwei Bestandteilen zählt; nur seine Wörter werden nachgesucht. In acht Etikett-Belegen vorher 0 von 60. |
| T-29 | Ein im Mustersatz bestätigter Spaltenkopf („Pos Menge“, auch „Pos Menge Thomas Berger“) wurde ohne Grenze nachgesucht. | behoben, siehe T-32 | Häufige Spaltenköpfe werden nie nachgesucht, ebenso zusammengesetzte Kontaktwörter („Telefon-Nr“, „Telefon/Fax“) und „Handy“, „Durchwahl“. Offen: Spaltenköpfe außerhalb der Liste. |
| T-30 | Tests ließen stilles Scheitern der KI (leere Treffer statt Fehler), den 502 beim Anwenden, den Satz rechts vom Namen, die Grenze 50/51 und das Suchfenster der Anrede ungeprüft. | behoben | Tests mit festem Ausgang je Fall; ein Absturz der KI meldet „KI-Namenserkennung ist fehlgeschlagen“, ein falsches Ergebnis „lieferte ein ungültiges Ergebnis“, beides HTTP 502. „Dipl.-Ing.“ zählt als Titel. Der Mustersatz läuft über Zellgrenzen nur, wenn er die Grenze noch ändern kann. Von 29 Mutationsproben schlugen 28 an; die übrige war entgegen der ersten Annahme nicht wirkungsgleich (siehe T-35). |
| T-31 | HTTP 502 ist mehrdeutig, weil nginx ihn auch bei einem Ausfall des Backends erzeugt. | offen | Bewusst so: Die Meldung im Feld `detail` unterscheidet beide Fälle; die Oberfläche zeigt sie an. |

Die Nachprüfung von 578166b (neunte Runde, 23.11.2026) ergab:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-32 | Schwer: Die Liste der Spaltenköpfe sperrte auch Nachnamen aus einem Satz und der Listenform („Petra Preis“, „Wolfgang Menge“, „Preis, Petra“), selbst mit Anrede; die Prüfung der Bindestrich-Teile sperrte Doppelnamen wie „Schmidt-Mai“ (je 0 von 20). | behoben | Spaltenköpfe gelten nur bei Zellbelegen als gesperrt, dort mit Anrede weiter nachgesucht; Bindestrich-Teile werden nur auf Kontaktwörter geprüft. Jetzt 19 bis 20 von 20, die Listenform ist wieder ganz Fundstelle. |
| T-33 | Schwer: Die Teilbestätigung (T-28) gab Kopfzeilen außerhalb der Liste ohne Grenze frei („Lieferant“, „Begünstigter“, „Auftraggeber“ je rund 80×, in einer Belegliste 120 von 121). | behoben, Rest offen | Ein nur zum Teil bestätigter Name gilt bis mindestens 50 Nennungen, nur ein ganz bestätigter Zellbeleg ohne Grenze; so am 23.11.2026 entschieden. In den 45 Etikett-Belegen mit 50 Nennungen je 50 von 50; über 50 Nennungen ohne Anrede und ohne Satzbeleg bleibt ein solcher Name lesbar. |
| T-34 | Die Punktregel aus T-27 wertete jedes Verb am Satzende als Abkürzung, „von“, „an“, „mit“ machten keinen Satz („Lukas Fischer unterschreibt.“, „Antrag von Lukas Fischer“ je 0 von 30). Ein kleingeschriebenes Wort weit unten im selben Block machte ein Etikett oben zum Satz. | behoben | Feste Liste der Abkürzungen und Kopfzeilenwörter statt Punktregel; Satzwörter zählen nur in der Zeile des Treffers und direkt davor oder danach. Die genannten Zeilen jetzt 30 von 30. |
| T-35 | Testlücken: bestätigter Beleg über Zellgrenzen ohne Grenze, Klemmung im Mustersatz, mehrere bestätigte Teile, „Telefon:“ mit Doppelpunkt. Ein `ValueError` der KI selbst hieß „ungültiges Ergebnis“; „Dipl.-Ing. (FH)“ und „Dipl.-Ök.“ galten nicht als Titel. | behoben | Tests dazu; Absturz und falsches Ergebnis werden getrennt geprüft; Titel ergänzt. Alle 39 Mutationsproben schlagen an. |
| T-36 | „Thomas Berger-Fax“: „Berger“ wird nicht nachgesucht, weil der Doppelname ein Kontaktwort enthält. Fehlt der KI ein Name ganz („Zahlung an Lukas Fischer per Überweisung“), hilft auch die Nachsuche nicht. | offen | Selten; Grenze des Modells. |

Die Nachprüfung (zehnte Runde, 23.11.2026) ergab:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-37 | Schwer: Mit „nach“, „für“, „bei“ usw. als Satzwort galt eine Kopfzeile wie „Summe Netto nach Skonto“ oder „Rabatt Skonto bei Zahlung“ als Satz; „Summe“ und „Skonto“ wurden ohne Grenze nachgesucht (30 von 30). | behoben | Ein Satz- oder Listenbeleg, der nur aus Spaltenköpfen besteht, gilt als Zellbeleg. In denselben Belegen kein Nachsuche-Treffer mehr; „Petra Preis“ und „Menge, Wolfgang“ bleiben Nachnamen. |
| T-38 | Zerlegte MuPDF eine Zeile wegen großer Wortabstände (Blocksatz, Formulare), zählte jedes Stück als eigene Zeile; das Satzwort am Zeilenende lag dann außerhalb des Fensters. | behoben | Stücke derselben Grundlinie zählen als eine sichtbare Zeile. |
| T-39 | Testlücken: Satz in der Zeile nach dem Namen, Grenze bei zwei Zeilen Abstand, Spaltenkopf als Etikett („Summe Thomas Berger“). | behoben | Tests dazu; das Etikett aus einem Spaltenkopf gilt als Teilbestätigung (Grenze 50, 40 von 40, bei 60 Nennungen 0). Alle 48 Mutationsproben schlagen an. |
| T-40 | Lieferte die KI-Funktion einen Generator, liefen ihre Fehler erst bei der Umwandlung auf und konnten HTTP 500 statt 502 ergeben. | behoben, siehe T-41 | Fehler beim Abruf, auch aus inneren Generatoren, heißen „ist fehlgeschlagen“; ein Ergebnis, das keine Liste ist, heißt „lieferte ein ungültiges Ergebnis“. |

Die Nachprüfung von 023889e (elfte Runde, 23.11.2026) ergab keinen schweren Befund, aber:

| Nr. | Befund | Stand | Lösung |
|---|---|---|---|
| T-41 | Rückschritt aus T-37: Meldete die KI nur Titel und Nachnamen („Dr. Menge“ aus „Die Prüfung führte Frau Dr. Menge durch.“), galt der Beleg als reiner Spaltenkopf; „Menge“ wurde nicht mehr nachgesucht (30 → 0). Ein nicht iterierbares Ergebnis der KI hieß „fehlgeschlagen“, ein Fehler in einem inneren Generator ergab HTTP 500. | behoben | Anrede oder Titel im Beleg zählt als anderes Wort; „Dr. Menge“ wieder 30 von 30, „Summe Netto nach Skonto“ weiter ohne Nachsuche. Fehlermeldungen wie in T-40. Alle 51 Mutationsproben schlagen an. |
| T-42 | Kopfzeilen mit kaufmännischen Wörtern außerhalb der Liste der Spaltenköpfe („Gesamtsumme Netto nach Skonto“, „Kosten Netto nach Skonto“, „Endbetrag Netto bei Zahlung“) gelten weiter als Satz; das Wort außerhalb der Liste wird ohne Grenze nachgesucht (je 40 von 40, schon vor dieser Runde so). | offen | Die Liste kann nicht vollständig sein; die Gruppe „Namen (im Dokument nachgesucht)“ lässt sich in der Vorschau gesammelt abwählen. |

Neue Tests decken T-1 bis T-41 ab, darunter ein Lauf Vorschau → Anwenden mit echter KI auf einer Tabelle.

Nicht geprüft wurden der angemeldete Zustand mit höheren Grenzen, ein echter 422 des Servers (nur simuliert, die Fälle sind im Backend getestet), die Übergabe aus der Werkbank und das Zeichnen per Touch.

Die zwölf neuen Tests zu H-N1 und M-N1 bis M-N6 (ohne M-N7, dessen Korrektur in der Schnittstelle liegt) schlagen auf dem Stand vor der zweiten Korrektur fehl, von den zehn Tests zu N3 sieben auf dem Stand davor; die übrigen drei sind Gegenproben.

**Testlauf 23.11.2026:** 425 Backend-Tests bestanden, alle Schwärzungstests eingeschlossen. Zwei Tests sind übersprungen, weil `tabula` Java braucht und Java hier fehlt. Fünf Tests schlagen in dieser Umgebung fehl, keiner betrifft die Schwärzung:

- vier in `test_form_advanced` (Formularberechnung), schon vor diesen Änderungen rot;
- `test_scan_optimize`, weil Tesseract hier nicht installiert ist.

`vue-tsc` und der Produktions-Build laufen ohne Fehler. Ein auditcore-runner-Prüfprofil hat das Repository nicht.

