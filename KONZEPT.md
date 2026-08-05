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
| PDF | Zusammenführen, Teilen, Rotieren, PDF→Bilder, Komprimieren, Wasserzeichen, Bilder→PDF, Seiten ordnen, Vergleich, OCR, Metadaten, Schützen/Entsperren (AES-256), PDF→Word, PDF→Excel, **Text bearbeiten (WYSIWYG, blockbasiert)**, **PDF→Text**, **Suchen & Ersetzen**, **Schwärzen (echte Redaction)**, **Seitenzahlen**, **Kopf-/Fußzeile**, **Bates-Nummerierung**, **Formulare ausfüllen (AcroForm)**, **Bild-Signatur**, **PDF/A (Ghostscript)**, **Einbrennen/Flatten**, **Anmerkungen interaktiv (Markieren/Rechteck/Linie/Freitext/Kommentar/Stempel/Freihand/Schwärzen per Maus)**, **Digitale Signatur (PAdES via pyHanko, eigenes PKCS#12-Zertifikat)**, **Scan-Optimierung (OCRmyPDF: Geraderücken, Auto-Drehen, OCR-Ebene)**, **Batch-Verarbeitung (bis 50 Dateien → ZIP, Bates fortlaufend über Dateigrenzen)** |
| Word | Word→PDF, Word verbinden, Word-Vergleich, Word-Metadaten |
| Excel | Excel-Metadaten |
| Auslieferung | Direkt-Download je Werkzeug, **ZIP-Download** aller Sitzungs-Ergebnisse (client-seitig via JSZip), **Mailversand** der Ergebnisse |
| Konten | **Optionale Anmeldung** (offene Registrierung, erster Admin per Env-Seed), höhere Limits für Angemeldete (100/400 MB, 60/min), gespeicherte Werkzeug-Einstellungen, Konto-Selbstlöschung (Art. 17 DSGVO), Admin-Bereich (Nutzer verwalten, Konfiguration einsehen) |

Die Ergebnisliste („Ergebnisse dieser Sitzung") existiert ausschließlich im Browser:
jede heruntergeladene Datei wird dort vorgemerkt und kann gebündelt als ZIP geladen
oder per Mail versendet werden. Ein Reload leert die Liste.

**WYSIWYG-Textbearbeitung**: eigene, neu gebaute Ansicht (nicht der defekte
audit_designer-Editor): Seitenansicht mit klickbarem Textblock-Overlay,
Änderungen werden serverseitig per weißer Redaction + `insert_textbox` in die
Original-Box geschrieben (Auto-Verkleinerung bei Überlauf, Latin-1-Sanitizing
für die Basis-Fonts). Bewusste Grenze gegenüber Adobe Acrobat: kein
seitenübergreifender Reflow — der Text bleibt in seiner Box.

### Annotations-Editor — umgesetzt

Interaktive Annotationen sind als eigene Neuentwicklung umgesetzt (nicht der
defekte audit_designer-Editor): Werkzeugpalette + Maus-Zeichnen auf der
Seitenansicht (Markieren, Rechteck, Linie, Freitext, Kommentar, Stempel,
Freihand, Schwärzen), SVG-Vorschau der ausstehenden Anmerkungen,
Arbeitskopie-Prinzip wie im Texteditor. Dabei behobener Vorlagen-Defekt:
`add_ink_annot` verlangte in aktuellen PyMuPDF-Versionen Float-Paare statt
`fitz.Point` (Regressionstest vorhanden).

### Restpunkte — umgesetzt

- **Lesezeichen-/TOC-Editor**: Tabellen-UI (Ebene/Titel/Seite, verschieben,
  löschen, hinzufügen) über die vorhandenen toc/read-, toc/write- und
  toc/auto-detect-Endpoints.
- **Asynchrone Verarbeitung** für OCR, Vergleich und Scan-Optimierung:
  In-Memory-Job-Queue (ThreadPool, TTL 15 min, Ergebnis einmalig abholbar,
  Jobs an Nutzer-ID/IP gebunden) mit Polling im Frontend — große Dateien
  laufen nicht mehr in Browser-Timeouts. Grenze: Der Job-Store ist
  prozesslokal; bei mehreren Backend-Replikas braucht es Sticky-Sessions
  oder einen externen Store.

### Modulkatalog-Ausbau (2026-07-29) — umgesetzt

Alle im Modulkatalog 2026 identifizierten Lücken, die ohne Datenspeicherung
und ohne Cloud machbar sind (Details: MODULKATALOG_2026.md):

- **Office → PDF**: Excel, PowerPoint, ODF, RTF, HTML, Text via LibreOffice
  (Dockerfile um libreoffice-calc/-impress erweitert).
- **PDF exportieren**: Markdown (Überschriften-Heuristik über Schriftgrößen),
  HTML (XHTML je Seite), JSON (Textblöcke mit Bounding-Boxes), CSV
  (Tabellenerkennung via PyMuPDF `find_tables`, kein Java nötig).
- **Bereinigen**: `doc.scrub()` — Metadaten, XMP, JavaScript, eingebettete
  Dateien, versteckte Inhalte; auch als Batch-Operation.
- **Rechteverwaltung**: pikepdf-Encryption ohne Öffnen-Passwort mit
  Besitzer-Passwort + Drucken/Kopieren/Ändern/Kommentieren-Flags.
- **Signaturprüfung mit Bericht**: pyHanko-Validation je Signaturfeld
  (Integrität, CMS-Gültigkeit, Unterzeichner, Signierzeitpunkt, Abdeckung);
  ehrlicher Hinweis, dass ohne Vertrauensanker kein Vertrauensurteil möglich ist.
- **TSA-Zeitstempel**: optionale RFC-3161-URL bei der digitalen Signatur
  (`HTTPTimeStamper`).
- **Leere Seiten einfügen**, **Prüfakte** (Merge + Lesezeichen pro Dokument +
  durchgehende Bates-Nummerierung), **Qualitätsprüfung** (leere Seiten, Scans
  ohne Textebene, Duplikat-Erkennung über Pixmap-Hashes).
- **OCR-Ausbau**: 7 Sprachen (deu/eng/fra/ita/spa/nld/pol) + Entrauschen
  (`clean`/unpaper) in OCR und Scan-Optimierung.
- **Batch-Ausbau**: Wasserzeichen und Bereinigen als weitere Operationen.
- **Lokale KI** (Zusammenfassen, Frage zum Dokument): ausschließlich über
  einen OpenAI-kompatiblen Endpoint der eigenen Infrastruktur
  (`PDFAPP_LLM_URL`, z.B. ai-router) — keine Cloud. Kachel und Endpoint sind
  ohne Konfiguration deaktiviert; Datenschutzerklärung weist die transiente
  Übertragung an das lokale LLM aus; Antworten sind als KI-Entwurf markiert.
- **Rolodex-Ansicht**: umschaltbare Dashboard-Ansicht (Raster ⇄ 3D-Karten-
  Karussell mit Tastatur-/Mausrad-Navigation), Wahl in localStorage persistiert.

### Formular-Designer — umgesetzt

Felder werden per Maus auf der Seitenvorschau aufgezogen (Klick = Standardgröße
des Feldtyps), Eigenschaften rechts bearbeitet: Name, Hilfetext, Vorbelegung,
Auswahlwerte, Schriftgröße, Pflichtfeld, Nur-lesbar; dazu Duplizieren, Löschen,
Feldliste über alle Seiten. Feldtypen: Textfeld, mehrzeilig, Kontrollkästchen,
Dropdown, Liste, Signaturfeld.

- **Koordinaten**: normiert auf 0–1 wie im Annotations-Editor, damit das Layout
  unabhängig von der Vorschauauflösung und auf andere Dokumente übertragbar ist.
- **Lokales Speichern ohne Server**: Autosave des Layouts in `localStorage`
  (Wiederherstellung beim nächsten Öffnen, mit Verwerfen-Option) plus Export als
  JSON-Datei (`<name>_formular-layout.json`, Schema `{version, document, fields}`).
- **Import**: Layout-JSON einlesen (akzeptiert Objekt oder bloße Feldliste, mit
  Normalisierung/Clamping und Feldzahl-Obergrenze) sowie Übernahme **vorhandener
  AcroForm-Felder aus dem PDF** — `form/fields` liefert dafür normierte Geometrie
  und Designer-Typen, sodass fremde Formulare weiterbearbeitet werden können.
- **Prüflauf** (`dry_run=true`) zeigt vor dem Erzeugen alle Hinweise im Klartext
  (falsche Seite, zu kleines Feld, fehlende Auswahlwerte, doppelter Name →
  automatische Nummerierung). Hinweise gehen bewusst nicht über HTTP-Header,
  weil deutsche Texte dort nicht verlustfrei transportierbar sind.
- **Robustheit**: Feldnamen werden für AcroForm saniert (Punkt/Klammern/
  Steuerzeichen → `_`), Namenskollisionen erhalten Suffixe, fehlerhafte
  Einzelfelder brechen den Vorgang nicht ab (Ergebnis + `warnings`).
- **Berechnung, Format, Wertebereich**: pro Textfeld Summe/Produkt/Mittelwert/
  Minimum/Maximum über ausgewählte Felder oder eine Formel über Feldnamen;
  Zahl-, Währungs- und Prozentformat mit deutschen Trennzeichen; Min/Max-Prüfung.
  Umgesetzt als PDF-Aktionen (`AFSimple_Calc`, `AFNumber_Format`,
  `AFRange_Validate`); PyMuPDF pflegt die Berechnungsreihenfolge `/CO`, zusätzlich
  wird `NeedAppearances` gesetzt. Rechenfelder sind standardmäßig schreibgeschützt.
  **Sicherheitsentscheidung**: freies JavaScript wird nicht übernommen — der
  Dienst kompiliert das Skript selbst aus einer geprüften Formel (nur Feldnamen,
  Zahlen, Grundrechenarten, Klammern, max. 200 Zeichen). Sonst wäre die App ein
  bequemer Weg, beliebiges JS in fremde PDFs zu schreiben; ein Regressionstest
  hält typische Angriffsformeln (`app.alert`, `submitForm`, `eval`) fest.
  Ausgeführt werden die Aktionen vom Viewer (Acrobat & Co.) — das UI sagt das.
- **CSV**: Feldwerte exportieren (Semikolon, UTF-8-BOM → Excel), leere Vorlage
  mit allen Feldnamen erzeugen und **Serienbefüllung** aus CSV — eine Zeile
  ergibt ein PDF, die Spalte `dateiname` bestimmt den Namen, mehrere Zeilen
  kommen als ZIP (max. 200 Zeilen, unbekannte Spalten werden als Hinweis
  gemeldet statt still verworfen).
- **Grenze (dokumentiert)**: Optionsfelder/Radio-Gruppen fehlen — PyMuPDF 1.28
  kann mehrere Radio-Widgets derselben Gruppe nicht anlegen („bad xref") und
  liefert keine getrennten On-States; das UI verweist auf Dropdown bzw.
  Kontrollkästchen.

### Konzept-Endausbau (2026-07-30) — umgesetzt

Alle übrigen Katalogpunkte ohne Speicher-/Cloud-Konflikt:

- **Stapelsignatur** und **Umbenennen** als Batch-Operationen (Zertifikat gilt
  für den ganzen Lauf, Muster `{name}`/`{n}` mit einstellbarer Stellenzahl).
- **Signaturprüfung mit Vertrauensankern**: eigene Wurzelzertifikate (PEM/DER)
  hochladbar; erst damit wird die Vertrauenskette bewertet, sonst weist der
  Bericht sie ehrlich als „nicht bewertet" aus.
- **Bild ersetzen**: alle Bilder mit Vorschau, Seite und Pixelmaß auflisten,
  eines auswählen und austauschen — Position und Layout bleiben erhalten.
- **KI-Modi erweitert**: neben Zusammenfassen und Fragen jetzt Übersetzen (freie
  Zielsprache), Schlagwörter und Gliederungsvorschlag — weiterhin ausschließlich
  über das lokale LLM.

Was bewusst offen bleibt (Zusammenarbeit/DMS/Cloud, Live-Webseiten→PDF wegen
SSRF, QES/EU-Trusted-Lists, XFA, Handschrift-OCR, PDF→PowerPoint/EPUB,
SDK/Plugin-System), steht mit Begründung in MODULKATALOG_2026.md.

### Abstand zu Acrobat verkleinert (2026-07-30) — umgesetzt

Drei Punkte aus der ehrlichen Selbsteinschätzung „guter Adobe-Klon?":

**1. Echte Anzeige im Browser (pdf.js).** Die Vorschau lief bisher über
serverseitig gerenderte Thumbnails: jede Seite ein Upload, ein Bild zurück,
Zoom nur als Hochskalierung. Jetzt rendert `components/PdfViewer.vue` das
Dokument lokal — vektorbasiert, mit Seitennavigation, Zoom (25–400 %) und
„Breite anpassen". Für die reine Ansicht verlässt die Datei den Browser nicht
mehr; Textbearbeitung, Anmerkungen und Formular-Designer teilen sich die
Komponente über einen Overlay-Slot (Kinder rechnen weiter in 0–1-Koordinaten).
Die Werkzeuge werden per `defineAsyncComponent` nachgeladen, damit pdf.js die
Startseite nicht belastet (Startbundle 227 kB statt 488 kB, pdf.js in eigenem
Chunk). Grenze bleibt: das Erzeugen der geänderten Datei läuft weiter über den
Server (PyMuPDF) — es ist kein Live-Editor wie Acrobat, aber alles außer dem
Schreibvorgang passiert lokal.

**2. Schrifteinbettung statt Basis-14.** Die Textbearbeitung nutzte die
eingebauten Schriften, die nur Latin-1 können — „—", „✓" oder „€" gingen als
„?" verloren. Jetzt wird eine echte TrueType-Schrift eingebettet: Liberation
(metrisch kompatibel zu Arial/Times/Courier, das Layout bleibt ähnlich),
DejaVu als Rückfall mit breiterer Zeichenabdeckung. Der Schriftname des
Originalblocks bestimmt Familie, Fett und Kursiv; fehlt ein Zeichen in der
gewählten Schrift, wird automatisch auf die breitere gewechselt. Ohne
Schriftdateien im System greift weiterhin Basis-14 mit sichtbarem Hinweis.

**3. Musterbasierte Schwärzung.** Neben dem Einzelbegriff gibt es jetzt neun
Muster (IBAN, E-Mail, Telefon, Steuer-ID, USt-IdNr., Kreditkarte, Datum,
IP-Adresse, Aktenzeichen) und Namenslisten (ein Begriff pro Zeile), jeweils
mit Optionen für Groß-/Kleinschreibung und ganze Wörter. Treffer werden über
Wort-Rechtecke gefunden, damit auch eine IBAN in Vierergruppen erfasst wird.
Weil Schwärzen unumkehrbar ist, gibt es eine **Vorschau**, die jede Fundstelle
mit Text, Muster und Seite auflistet, bevor etwas entfernt wird.

### Live-Editor: direkt auf der Seite tippen (2026-07-31) — umgesetzt

Der größte verbliebene Unterschied zu Acrobat war nicht die Funktion, sondern
die Bedienung: Text ändern hieß „Block anklicken → Dialog öffnet sich →
Textfeld ausfüllen → vormerken". Das ist ein Formular, kein Editor.

Jetzt liegt der Cursor dort, wo der Text steht. `PdfTextEditor.vue` setzt ein
`contenteditable`-Feld exakt auf die Blockposition der gerenderten Seite —
gleiche Schriftgröße, gleiche Farbe, gleiche Familie, skaliert mit dem Zoom.
Dazu:

- **Schwebende Leiste** am Block: Schriftgröße, Fett, Kursiv, Farbe. Fett und
  Kursiv werden als eingebettete Bold-/Italic-Schrift übernommen, nicht
  simuliert.
- **Verschieben und Größe ändern** per Anfasser, in Seitenkoordinaten.
- **Live-Vorschau**: geänderte Blöcke erscheinen sofort auf der Seite (grüner
  Rahmen), noch bevor der Server die Datei neu schreibt.
- **Esc oder Klick daneben** übernimmt; die Änderungsliste bleibt als
  Kontrolle daneben stehen.

Die Grenze bleibt bewusst bestehen und wird auch so benannt: Das *Schreiben*
der geänderten Datei macht weiterhin der Server (PyMuPDF). Ein PDF im Browser
zu schreiben hieße, eine zweite PDF-Bibliothek zu pflegen — für ein Ergebnis,
das der Server bereits korrekt liefert.

### Bearbeitung unterbrechen und fortsetzen (2026-07-30) — umgesetzt

Editoren halten einen Arbeitsstand: die Arbeitskopie des Dokuments **plus die
noch nicht angewandten Änderungen**. Ein reines PDF hätte nur den angewandten
Stand — genau die vorgemerkten Änderungen will man beim Unterbrechen aber
behalten. Zwei bewusst getrennte Wege (`lib/worksession.ts`,
`components/WorkSessionBar.vue`, eingebaut in Textbearbeitung, Anmerkungen und
Formular-Designer):

- **Im Browser** (IndexedDB, entprellt alle 1,5 s): Beim nächsten Öffnen bietet
  das Werkzeug „Fortsetzen" an, mit Zeitangabe und Zahl der offenen Änderungen.
  Die Daten bleiben auf dem Gerät, der Server sieht sie nie; „Browser-Sicherung
  löschen" entfernt sie sofort. Dokumente über 40 MB werden nicht lokal
  zwischengelagert (Quota) — das Werkzeug sagt das und verweist auf die Datei.
- **Als Sitzungsdatei** (.zip mit `dokument.pdf` + `arbeitsstand.json`): für
  Gerätewechsel und längere Pausen. Beim Laden werden auch einfache PDFs
  akzeptiert (dann ohne offene Änderungen); Dateien aus einem anderen Werkzeug
  oder mit fremder Version werden mit Begründung abgewiesen.

Zwei Fehler, die der E2E-Lauf aufgedeckt hat und die behoben sind: der Zustand
enthielt reaktive Vue-Proxys, die IndexedDB nicht klonen kann (die Sicherung
schlug ab der ersten Änderung still fehl → JSON-Normalisierung plus
aussagekräftiger Hinweis statt stiller Fehlschlag), und der Knopf „Arbeitsstand
laden" war nur bei geöffnetem Dokument sichtbar — also genau dann nicht, wenn
man ihn braucht.

### Werkzeug-Freigabe durch den Administrator (2026-07-30) — umgesetzt

Der Betreiber entscheidet im Admin-Bereich pro Werkzeug, ob es allen offensteht
oder eine Anmeldung verlangt. Auslieferungszustand: **nichts beschränkt.**

- **Oberfläche**: beschränkte Kacheln erscheinen für nicht angemeldete Besucher
  ausgegraut, mit Schloss-Symbol und „Nur mit Anmeldung" statt der
  Beschreibung — im Raster wie in der Rolodex-Ansicht. Ein Klick führt auf die
  Anmeldeseite, die erklärt, warum. Der Hinweisbanner zählt die gesperrten
  Werkzeuge, damit die Aussage „keine Registrierung erforderlich" nicht
  unbemerkt falsch wird.
- **Durchsetzung serverseitig**: Ausgrauen allein wäre wirkungslos (jeder könnte
  die API direkt aufrufen). Eine Router-Dependency ordnet jeden Request über
  einen Werkzeug-Katalog (`app/tool_catalog.py`) einem Werkzeug zu und
  beantwortet gesperrte Aufrufe ohne Anmeldung mit **403**. Werkzeuge mit
  mehreren Endpunkten (z.B. Schützen/Entsperren, KI-Modi) sind vollständig
  gesperrt; gemeinsam genutzte Vorschau-Endpunkte (Thumbnails, Metadaten lesen,
  Formularfelder lesen) gehören zu keinem Werkzeug und bleiben offen.
- **Speicherung**: eine Zeile in `app_settings` (JSON-Liste der Werkzeug-IDs),
  keine personenbezogenen Daten; Alembic-Migration `0002`.
- **Kein DB-Zugriff pro Anfrage**: die Liste liegt im Prozess-Cache und wird
  höchstens alle 30 Sekunden nachgeladen, bei Admin-Änderungen sofort. Ohne
  Datenbank wird gar nicht gelesen.
- **Fail-open bewusst**: ist die Datenbank nicht erreichbar, sperrt nichts. Ohne
  DB kann sich niemand anmelden — eine Sperre wäre dann eine Sperre für alle.
- **Konsistenz-Test**: ein pytest-Fall vergleicht die Werkzeug-IDs des Backends
  mit den Kacheln in `ToolGrid.vue`, ein zweiter prüft, dass jeder Katalog-Pfad
  einer echten Route entspricht. Damit kann die Zuordnung nicht unbemerkt
  auseinanderlaufen.

### Barrierefreiheit nach BITV 2.0 (2026-07-31) — umgesetzt

Für eine Anwendung der Landesverwaltung ist Barrierefreiheit keine Kür, sondern
Pflicht (BITV 2.0, § 3 HessBGG). Geprüft wurde automatisiert mit axe-core über
Startseite, Anmelden, Registrieren, Datenschutz, Passwort-Reset und die
Rolodex-Ansicht — jeweils in hellem **und** dunklem Farbschema, Regelsätze
WCAG 2.0 A/AA und 2.1 A/AA. **Ergebnis: 0 Verstöße.**

Behoben wurden dabei diese echten Befunde:

- **Kontrast**: Hilfetexte in `text-gray-400`/`text-gray-500` erreichten nur
  2,4:1 bzw. 3,2:1 statt der geforderten 4,5:1. Durchgängig auf `text-gray-600`
  mit passender Dunkelvariante angehoben (35 Dateien).
- **Links nur durch Farbe erkennbar** (WCAG 1.4.1): Inline-Links im Fließtext
  hatten 2,2:1 gegen den umgebenden Text. Jetzt zusätzlich unterstrichen.
- **Rolodex**: Das Ausblenden der hinteren Karten per `opacity` drückte deren
  Text unter die Kontrastschwelle. Die Tiefenwirkung entsteht nun allein über
  Skalierung, Drehung und Stapelreihenfolge.

Ergänzt:

- **Sprunglink** „Zum Hauptinhalt springen" als erstes Tab-Ziel; er setzt den
  Fokus tatsächlich auf `<main>` (ein reiner Anker verschiebt nur den Scroll,
  die nächste Tab-Taste landete sonst wieder in der Kopfzeile).
- **`prefers-reduced-motion`**: Wer im Betriebssystem reduzierte Bewegung
  eingestellt hat, bekommt keine Kartenrotation und keine Übergänge — die
  Anwendung bleibt vollständig bedienbar (WCAG 2.3.3).
- **Sichtbarer Tastaturfokus** global über `:focus-visible`.

Nicht abgedeckt und bewusst offen: Eine automatisierte Prüfung findet
erfahrungsgemäß etwa die Hälfte der Barrieren. Für die Erklärung zur
Barrierefreiheit braucht es zusätzlich einen manuellen Test mit Screenreader
(NVDA/JAWS) — das ist eine Aufgabe der einführenden Stelle, nicht des Codes.

### Geschwindigkeit (2026-07-31) — umgesetzt

Gemessen vor und nach der Änderung, nicht geschätzt:

| Messpunkt | vorher | nachher |
|---|---|---|
| `/api/health` (wird bei jedem Seitenaufruf gerufen) | 96 ms | 1,2 ms |
| Health-Latenz während vier parallelen Zusammenführungen | bis 242 ms | 1–2 ms |
| Werkzeug „Text bearbeiten" öffnen | ~385 kB nachgeladen | 10 kB, Oberfläche nach 128 ms bedienbar |
| Textextraktion, 60 Seiten (Übertragung) | 113 kB | 1,2 kB |
| Zweitbesuch der Startseite | voller Bundle-Download | 2 kB (Rest aus dem Cache) |

Was dahinter steckt:

1. **Erkennung der Zusatzprogramme wird gemerkt.** `check_features()` startete
   bei **jedem** `/api/health` einen `libreoffice --version`-Subprozess. Da die
   Startseite den Endpunkt beim Laden abfragt, kostete das jeden Besuch rund
   90 ms. Die Installation ändert sich zur Laufzeit nicht — jetzt wird sie
   einmal pro Prozess ermittelt.
2. **Rechenarbeit blockiert nicht mehr die Event-Loop.** Die Datei-Endpunkte
   sind `async def` (sie müssen `await file.read()` aufrufen), rechneten danach
   aber synchron mit PyMuPDF. Solange ein Dokument verarbeitet wurde, wartete
   *jede* andere Anfrage — auch die anderer Nutzerinnen und Nutzer. 45 Aufrufe
   laufen jetzt über `app/offload.py` im Thread-Pool (PyMuPDF und pikepdf geben
   dabei das GIL frei, es wird also echt parallel gerechnet).
3. **Textantworten werden komprimiert, Binärdateien nicht.** `JsonGZipMiddleware`
   komprimiert nur JSON/Text/CSV/SVG. Starlettes eingebautes `GZipMiddleware`
   hätte auch PDFs und Bilder erfasst — die sind bereits komprimiert, ein
   zweiter Durchlauf kostet bei einer 100-MB-Datei mehrere Sekunden CPU für
   unter 2 % Ersparnis. Große Downloads bleiben zudem Streams und landen nie
   vollständig im Speicher.
4. **pdf.js lädt erst, wenn es gebraucht wird.** Der Viewer (≈370 kB) hing fest
   in den drei Editor-Werkzeugen. Jetzt eigener Chunk plus
   `defineAsyncComponent`: die Werkzeug-Oberfläche ist sofort da, pdf.js kommt
   parallel und nur, wenn wirklich ein Dokument geöffnet wird.
5. **Gehashte Assets ein Jahr im Cache, `index.html` nie.** Dazu `gzip_static`
   mit im Build vorkomprimierten Dateien, damit nginx nicht bei jedem Abruf neu
   komprimiert.
6. **`/api/health` wird nicht mehr doppelt abgefragt.** Kachelraster und
   Hinweisleiste teilen sich über `lib/health.ts` eine Anfrage (60 s gültig,
   nach Admin-Änderungen sofort verworfen).

Bewusst **nicht** gemacht: mehrere uvicorn-Worker. Die Auftragsverwaltung für
lange Läufe (OCR, Vergleich) hält ihre Ergebnisse prozesslokal im
Arbeitsspeicher — mit mehreren Prozessen fände die Abholung ihren Auftrag nicht
mehr. Skalierung über Replikas erfordert vorher einen gemeinsamen Auftragsspeicher
(im Hardening-Backlog vermerkt).

### Kapselung der Fremdbibliotheken (2026-07-31) — umgesetzt

Anlass war die Frage, ob man die Fremdbibliotheken nicht selbst schreiben und
pflegen könnte. Die ehrliche Antwort für den PDF-Kern ist nein: PyMuPDF sind
101.000 Zeilen Python über 15 MB kompiliertem C (MuPDF); dahinter stehen rund
tausend Seiten PDF-Spezifikation plus Schriftinterpretation, Bildkodierungen,
Farbprofile und Verschlüsselungsverfahren. Ein selbst gebauter Parser wäre
gegenüber diesen gehärteten Implementierungen auch sicherheitstechnisch ein
Rückschritt — Formatparser sind das klassische Ziel für Speicherfehler.

Die Abhängigkeit wird deshalb nicht vermieden, sondern **eingefasst**
(`backend/app/pdf_backend.py`):

1. **Ein Importpunkt.** Vorher importierten sechs Service-Dateien und ein
   Router `fitz` bzw. `pikepdf` selbst, zwei davon sogar lokal innerhalb von
   Funktionen. Jetzt: null Direktimporte außerhalb des Kapselungsmoduls, von
   einem Test erzwungen. Ein Versionswechsel oder Austausch trifft eine Datei
   statt sieben.
2. **Eine Verfügbarkeitserkennung.** Statt sechs eigener
   `try/except ImportError`-Blöcke mit eigenen Flags steht die Erkennung
   einmal zentral, samt der externen Programme (Ghostscript, LibreOffice,
   Tesseract, qpdf). Nebeneffekt: Der LibreOffice-Test startet gar keinen
   Subprozess mehr, wenn das Programm nicht im PATH liegt.
3. **Ein Register.** `DEPENDENCIES` führt zu jeder Komponente Zweck, Lizenz,
   Quelle und möglichen Ersatz. Das Register speist `/api/licenses` und damit
   die Lizenzseite — die Angabe kann nicht veralten, ohne dass die Funktion
   mit veraltet.

Bewusste Grenze: Das ist **keine** Fassade, die jede PyMuPDF-Funktion nachbaut.
Die Services rufen `fitz` weiterhin direkt auf (146 Stellen). Eine vollständige
Abstraktionsschicht wäre eine zweite Bibliothek mit eigenen Fehlern und würde
die Abhängigkeit verstecken statt verringern. Eingefasst sind Zugang, Erkennung
und Buchführung.

Nebenbei behoben: `/pdf-tools/thumbnails` öffnete das Dokument im Router selbst,
um die Seitenzahl zu bestimmen — Geschäftslogik in der Schnittstellenschicht,
gegen die eigene Konvention. Das liegt jetzt in `thumbnails_for_spec()`.

### Lizenzlage und Quelltextpflicht (2026-07-31) — umgesetzt

**PyMuPDF und Ghostscript stehen unter „AGPL-3.0 oder kommerzielle
Artifex-Lizenz".** Bei einer öffentlich erreichbaren Weboberfläche greift
AGPL § 13: Wer den Dienst über das Netz nutzt, muss den vollständigen Quelltext
erhalten können — auch ohne dass Software verteilt wird.

Für dieses Vorhaben ist das eher Rückenwind als Hindernis; der Quelltext liegt
ohnehin offen. Es ist aber eine bewusste Entscheidung mit zwei Folgen:

- Die Anwendung **muss** den Quelltext benennen. Deshalb: Hinweis auf der
  Startseite (nicht nur im Fußbereich — eine Angabe, die man erst suchen muss,
  erfüllt die Bedingung nur formal), dauerhafter Fußzeilen-Link „Open Source",
  Abschnitt im Impressum und eine eigene Seite `/lizenzen` mit allen 15
  Komponenten, Lizenzen, Zweck und möglichem Ersatz.
- Eine spätere Weitergabe an Dritte **ohne** Quelloffenlegung wäre
  ausgeschlossen; dafür bräuchte es die kommerzielle Artifex-Lizenz.

Technisch hängt der Hinweis an der Wirklichkeit, nicht an einem festen Text:
`requires_source_disclosure()` prüft, ob eine AGPL-Komponente tatsächlich
verfügbar ist. Würde PyMuPDF eines Tages ersetzt, verschwindet der Hinweis von
selbst, statt als falsche Angabe stehen zu bleiben. Fehlt die Adresse
(`PDFAPP_SOURCE_URL`), weist die Lizenzseite den Betreiber sichtbar darauf hin,
dass die Bedingung noch nicht erfüllt ist.

### Härtung gegen Angriffe (2026-07-31) — umgesetzt

Durchgang über die Angriffsflächen einer öffentlich erreichbaren Anwendung, die
fremde Dateien verarbeitet. Sieben Befunde, alle behoben; jeder mit Test.

**1. Es gab keine einzige Sicherheitskopfzeile.** Kein CSP, kein
X-Frame-Options, kein nosniff. Weil das Anmeldetoken im localStorage liegt,
wäre jede Cross-Site-Scripting-Lücke eine Kontoübernahme gewesen — und die
Werkzeugseiten ließen sich in einen fremden Rahmen einbetten (Clickjacking).

Jetzt gesetzt: Content-Security-Policy, X-Content-Type-Options,
X-Frame-Options, Referrer-Policy, Permissions-Policy, Cross-Origin-Opener und
-Resource-Policy, optional HSTS. **Doppelt** — in nginx für die Oberfläche
(`frontend/security-headers.conf`) und im Backend für die API
(`backend/app/hardening.py`). Ein Schutz nur im Reverse-Proxy fällt genau dann
aus, wenn jemand die Aufstellung ändert.

Zwei bewusste Lockerungen, beide begründet: `style-src 'unsafe-inline'`, weil
Vue gebundene Stile als Inline-Attribut schreibt (Live-Editor und
Rolodex-Karten positionieren sich so) — Inline-*Styles* sind kein
Skriptausführungspfad, `script-src` bleibt strikt ohne `unsafe-inline` und ohne
`unsafe-eval`. Und die feste Turnstile-Domain, sonst ließe sich der Bot-Schutz
nicht laden.

**2. Uploadgröße wurde erst nach dem vollständigen Einlesen geprüft.** Bis zur
ersten Prüfung lag die Datei komplett im Arbeitsspeicher — bei 400 MB
Obergrenze und ein paar gleichzeitigen Anfragen ein Erschöpfungsangriff mit
einer curl-Zeile. `BodySizeLimitMiddleware` weist jetzt anhand von
Content-Length ab, bevor der Körper gelesen wird: gemessen **413 nach 11 ms**
statt 450 MB im Speicher. Fehlt die Längenangabe (chunked), zählt die
Middleware mit — sonst wäre die Schranke durch Weglassen eines Kopfes zu
umgehen.

**3. LibreOffice-Konvertierung ohne Isolation.** Eine hochgeladene HTML-Datei
mit `<img src="file:///etc/passwd">` hätte den Inhalt in das erzeugte PDF
gezogen; eine Verknüpfung auf einen internen Dienst wäre eine Anfrage aus dem
Serverkontext heraus gewesen. Jetzt: eigenes Benutzerprofil je Aufruf
(behebt nebenbei Sperrfehler bei parallelen Läufen), Verknüpfungsaktualisierung
aus, Makroausführung aus, keine Wiederherstellung.

**Restrisiko, das im Code nicht zu schließen ist:** Der Import eingebetteter
Bilder ist Teil des Formats. Vollständig ausgeschlossen ist der Zugriff erst,
wenn die Konvertierung ohne Netzzugang und ohne Lesezugriff auf das übrige
Dateisystem läuft — ein eigener Container ohne Egress. Das gehört ins
Betriebskonzept, nicht in den Quelltext.

**4. Keine Schranke gegen Dekompressionsbomben.** Pillow griff erst bei rund
178 Millionen Pixeln (allein 715 MB Bilddaten). Jetzt 64 Megapixel — das
entspricht DIN A3 bei 600 dpi und deckt jeden realistischen Scan ab.

**5. Keine Seitenzahl-Grenze.** Ein PDF von wenigen hundert Kilobyte kann
zehntausende Seiten enthalten; seitenweise Verarbeitung bindet dann minutenlang
einen Arbeits-Thread. Die Grenze (5.000 Seiten) hängt an `open_pdf()` — also am
Kapselungspunkt und damit automatisch an jedem Werkzeug, auch an künftigen.

**6. Offene Weiterleitung nach der Anmeldung.** `/login?redirect=` wurde
ungeprüft übernommen. Ein Link auf `?redirect=https://phishing.example` hätte
nach *echter* Anmeldung auf eine Fälschung geführt — der gefährlichste Moment,
weil die Nutzerin der Seite gerade vertraut. Jetzt sind nur seiteninterne Pfade
zugelassen; `//host` und `javascript:` werden ebenfalls abgewiesen.

**7. Ausnahmetexte in Fehlerantworten.** Zwei Stellen gaben `str(e)` nach außen
— das verrät Pfade und Bibliotheksinterna. Jetzt: Aussage nach außen,
vollständiger Eintrag im Log.

Was **schon vorher** in Ordnung war und geprüft wurde: ZIP-Dateien werden nur
geschrieben, nie entpackt (kein Zip-Slip); Dateinamen werden für
Content-Disposition bereinigt; CORS und das Vertrauen in `CF-Connecting-IP`
sind standardmäßig aus; Formelfelder laufen über einen eigenen Übersetzer statt
über freies JavaScript im PDF.

Nachweis: 16 pytest-Fälle in `test_hardening.py` plus ein Browser-Lauf, der die
Angriffe tatsächlich ausführt (`e2e_haertung.mjs`): Fremdskript, eingeschleustes
Inline-Skript, Datenabfluss an eine fremde Domain, Clickjacking und zwei
Weiterleitungsvarianten — alle sechs abgewehrt. Und, genauso wichtig: alle
sieben bestehenden E2E-Suiten laufen **unter der CSP** ohne Konsolenfehler, die
Richtlinie bremst die Anwendung also nicht aus.

#### Nachprüfung mit echtem nginx — vier weitere Befunde

Die erste Prüfung lief gegen einen Behelfsserver, der die Direktiven aus der
Konfigurationsdatei las. Das prüft die Werte, aber nicht das Verhalten von
nginx. Mit echtem nginx (1.24) kamen vier Mängel ans Licht, die alle behoben
sind:

1. **Der pdf.js-Worker wurde unbrauchbar.** Er ist eine `.mjs`-Datei; nginx'
   mitgelieferte `mime.types` kennt die Endung nicht und antwortet mit
   `application/octet-stream`. Zusammen mit dem neuen `nosniff` verweigert der
   Browser die Ausführung — Anzeige, Textbearbeitung, Anmerkungen und
   Formular-Designer wären in Produktion leer geblieben. Vorher fiel das nicht
   auf, weil der Browser den Typ erriet: **die Härtung selbst erzeugte den
   Fehler**, und nur der Lauf gegen echtes nginx machte ihn sichtbar. Behoben
   über einen eigenen `location`-Block mit `default_type text/javascript`.
2. **Zwei `Cache-Control`-Kopfzeilen auf `/assets/`** — `expires 1y` setzt eine
   eigene, zusätzlich zur ausdrücklichen. Jetzt eine einzige Angabe.
3. **Die von nginx selbst erzeugten Fehlerseiten trugen keine Kopfzeilen.**
   Bei 502 (Backend aus) und 413 (Körper zu groß) unter `/api/` antwortet nginx
   ohne das Backend — vorher null Sicherheitskopfzeilen, jetzt vollständig.
4. **API-Antworten waren cachefähig.** Ohne `Cache-Control` dürfen Browser und
   vorgelagerte Proxys verarbeitete Dokumente und Kontoauskünfte ablegen — das
   widerspricht dem Versprechen „keine Datenspeicherung" direkt. Jetzt
   `no-store` auf jeder API-Antwort, gesetzt in nginx **und** im Backend.

Zusätzlich: `Server: uvicorn` wird ausgeblendet, `X-Permitted-Cross-Domain-Policies`
ergänzt (die Anwendung liefert PDFs aus), und der überholte
`interest-cohort`-Eintrag ist entfernt.

Zwei Tests halten das zusammen: einer vergleicht die Kopfzeilenliste in nginx
mit der im Backend (sie stehen an zwei Orten und dürfen nicht auseinanderlaufen),
einer prüft, dass **jeder** `location`-Block das Schnipsel einbindet — in nginx
ersetzt ein `add_header` im Block alle geerbten Angaben, ein vergessenes
`include` liefert also gar keine Kopfzeilen. Beide wurden gegengeprüft, indem
die Abweichung absichtlich erzeugt wurde; beide schlagen an.

Alle acht E2E-Suiten und der axe-Lauf sind anschließend gegen echtes nginx
wiederholt worden — grün. Am Prüfskript selbst war dafür eine Änderung nötig:
Es schleuste axe-core als Inline-Skript ein, was die CSP zu Recht verweigert.
Angepasst wurde das Skript, nicht die Richtlinie.

### Optionale Konten — vorgezogen und umgesetzt

Ursprünglich Phase 3, auf Nutzerwunsch vorgezogen. Grundsätze (alle eingehalten):

- Anonyme Nutzung bleibt im Auslieferungszustand vollwertig — kein Feature-Gating
  hinter Login; ohne erreichbare Datenbank läuft die App automatisch rein anonym
  weiter (`/api/health` → `accounts: false`). Der Betreiber kann einzelne
  Werkzeuge bewusst auf Angemeldete beschränken (siehe „Werkzeug-Freigabe").
- Ausdrückliche Einwilligung per Pflicht-Checkbox bei der Registrierung; die
  Datenschutzerklärung ist differenziert (ohne Konto wird nichts gespeichert; mit
  Konto nur E-Mail, bcrypt-Hash, Einstellungen, Zeitstempel).
- Datensparsames Modell: keine IP-Speicherung, kein Klarnamen-Zwang.
- Anonyme Tool-Requests öffnen keine DB-Session (tokenloser Pfad DB-frei).
- Sicherheit: Passwort-Policy (12+ Zeichen, gemischt), Lockout nach 10
  Fehlversuchen (30 min), identische Login-Fehlermeldung gegen User-Enumeration,
  Selbstschutz im Admin-Bereich (letzter aktiver Admin nicht entfernbar).

### Hardening — Stand

- ✅ **Alembic**: Scaffold + idempotente Initial-Migration (`alembic upgrade head`
  gegen `PDFAPP_DATABASE_URL`); `create_all` bleibt als Fallback für frische
  Datenbanken im Lifespan.
- ✅ **E-Mail-Verifikation**: Bestätigungs-Mail bei Registrierung (Token-Hash,
  24 h gültig), `is_verified`-Status, Nachfordern über die Konto-Seite. Aktiv,
  sobald SMTP + `PDFAPP_PUBLIC_BASE_URL` gesetzt sind; ohne Konfiguration
  läuft die Registrierung unverändert.
- ✅ **Passwort-Reset**: Anfrage antwortet immer 202 (keine User-Enumeration),
  Token-Hash 2 h gültig, Reset resettet auch Lockout-Zähler.
- ✅ **Turnstile**: optionaler Bot-Schutz für Registrierung und Mailversand —
  aktiv, sobald `PDFAPP_TURNSTILE_SITE_KEY/SECRET` gesetzt sind; Widget lädt
  nur dann.
- Offen: Refresh-Tokens / kürzere Access-Token-Laufzeit (bewusst zurückgestellt,
  24-h-JWT für dieses Angebot akzeptiert).

### 360°-Security-Review (2026-07-29) — alle 10 Befunde behoben

Thumbnail-DoS (Auflösung ungedeckelt + Rendern aller Seiten → clamp 32–1400 px,
Seiten-Vorfilter, Cap 50), Event-Loop-Blocking der schweren Endpoints
(scan-optimize/to-pdfa/batch → Threadpool), spoofbarer CF-Connecting-IP-Header
(→ nur bei `PDFAPP_TRUST_CF_HEADER=true`), fehlendes globales Job-/RAM-Limit
(→ 20 aktive Jobs, 512 MB Ergebnis-Budget), Login-Timing-Seitenkanal
(→ Dummy-bcrypt), Default-SECRET_KEY (→ Konten deaktiviert + kritisches Log),
Header-Injection über Dateinamen (→ Sanitizing in allen Response-Helfern),
OCRmyPDF ohne Timeout (→ tesseract_timeout 120 s/Seite), SMTP-Header-Injection
über Betreff (→ CR/LF-Filter), blockierender Turnstile-Call (→ Threadpool).
Zusätzlich behoben: Bestands-DB ohne neue Spalten deaktivierte Konten
(→ idempotente Spalten-Nachziehung im Lifespan, Regressionstest).

### Design-Leitlinie (nach 360°-Review, 2026-07-29)

Apple-orientierte Reduktion umgesetzt: EINE Akzentfarbe (`primary`, Apple-nahes
Blau #0071e3) statt Purple/Blue/Green-Mix; neutrale Werkzeug-Kacheln
(Farbe nur im Icon) statt 16 Pastelltöne; kurze Headline mit `tracking-tight`;
Kernbotschaft nur noch im Banner + Footer statt vierfach; Sticky-Header mit
`backdrop-blur`; Kachel-Hover mit Schatten/Lift; Fokus-Ringe und angehobene
Kontraste im Grid; doppelte Zurück-Navigation entfernt. Offen (bewusst):
Emoji-Icons durch ein SVG-Icon-Set ersetzen, Werkzeug-Suche/Gruppierung im
Grid, Tool-Routing mit Deep-Links (`/werkzeug/:id`), Komponentenklassen-System.

## 4. Architektur

```
Browser (Vue 3 + Tailwind, deutsch)
  ├─ Tool-Komponenten (Kopien aus audit_designer, Import-Swap auf lib/api.ts)
  ├─ lib/results.ts   Sitzungs-Ergebnisse (nur RAM im Browser)
  ├─ lib/zip.ts       ZIP-Bündelung client-seitig (JSZip)
  └─ fetch /api/*  ──────────────┐
                                 ▼
nginx (static + Proxy /api, client_max_body_size 410m)
                                 ▼
FastAPI-Backend (Datei-Verarbeitung zustandslos; Konten optional in Postgres)
  ├─ api/pdf_tools.py    Kopie + Auth-Strip + Protect/Unlock (22 Endpoints)
  ├─ api/pdf_editor.py   Kopie + Auth-Strip (12 Endpoints)
  ├─ api/pdf_converter.py Kopie + Auth-Strip (PDF→Word/Excel, 7 Endpoints)
  ├─ api/{auth,me,admin}.py  optionale Konten (JWT, Preferences, Verwaltung)
  ├─ api/mail.py         Mailversand (aiosmtplib, transient)
  ├─ ratelimit.py        gestufte Default-Limits in eigener ASGI-Middleware
  │                      (limits-Bibliothek); slowapi nur für per-Route-Limits
  └─ services/           1:1-Kopien (PyMuPDF, pikepdf, Pillow, python-docx,
                         openpyxl, pytesseract, tabula/Java, LibreOffice)
                                 ▼
PostgreSQL 16 (nur users-Tabelle; bei Ausfall läuft die App anonym weiter)
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
die Anbieterdaten sind inzwischen eingetragen (`ImpressumView.vue` /
`DatenschutzView.vue`, Stand 2026-08). Der Konto-Abschnitt der
Datenschutzerklärung ist umgesetzt (Datenminimierung, Art. 6 Abs. 1 lit. b,
Selbstlöschung nach Art. 17).

## 6. Missbrauchsschutz

| Maßnahme | Umsetzung |
|---|---|
| Rate-Limiting gestuft | Eigene ASGI-Middleware (limits-Bibliothek): anonym pro IP `30/minute;500/day`, angemeldet pro Nutzer-ID `60/minute;2000/day` (env-konfigurierbar). IP aus `CF-Connecting-IP`, Fallback `request.client.host`; `/api/health` exempt. Zusätzlich strengere per-Route-Limits via slowapi: Login `10/15minutes`, Registrierung `10/hour`, Mail `5/hour` |
| Dateigrößen | anonym 50 MB/Datei + 200 MB/Operation; angemeldet 100/400 MB |
| Mail-Anhänge | 20 MB gesamt, sonst Verweis auf ZIP-Download |
| Timeouts | 5-Minuten-Timeout client-seitig; nginx `proxy_read_timeout 300s` |
| Eskalation (bei Bedarf) | Cloudflare-WAF/Bot-Fight-Mode; Phase 3: Turnstile vor Mailversand |

## 7. Bekannte Defekte der Vorlage (vor Phase-2-Port zu beheben)

Aus `docs/reviews/funktions_prozessreview_2026-07-11.md` (Abschnitt 4.6) und eigener
Analyse — betreffen den **visuellen Editor**, nicht die in Phase 1 übernommenen Tools:

1. `PdfEditor.vue` umgeht an ~9 Stellen das Composable und ruft `fetch('/api/pdf-editor/…')` roh auf (Befund P1-10).
2. `usePdfEditor.ts` ruft `POST /api/pdf-editor/export` auf — der Endpoint existiert nicht (toter Pfad). Im Scaffold wurde das Composable deshalb gar nicht erst übernommen; OCR/Compare rufen `apiPost` direkt.
3. Text-Ersetzen-Bug (Replace), fehlende Tests für echte Schwärzung (Redaction), fehlende Passwort-/Signatur-/PDF-A-Erkennung. — *Replace-Bug 2026-08-05 behoben (Ersatztext wird jetzt getrennt von der Redaktion geschrieben statt bei Platzmangel stillschweigend zu entfallen; zugleich `match_case` erstmals wirksam) und mit Tests belegt (`test_pdf_editor_werkzeuge.py`).*
4. OCR/Compare synchron — für große Dateien asynchron machen (SSE oder Polling).

## 8. Deployment

- **Stack**: `docker-compose.yaml` mit `backend` (python:3.12-slim + tesseract + LibreOffice, non-root, Healthcheck `/api/health`), `frontend` (Node-Build → nginx) und `cloudflared` (nur compose-Profil `prod`).
- **Hetzner**: Ablage nach dem Muster von `docs/HETZNER_DEPLOY.md` — `/opt/pdf-editor/compose.yaml`, Secrets in `/etc/pdf-editor/env` (0600). Eigener Cloudflare-Tunnel bzw. zusätzliches Hostname-Mapping `pdf.flowaudit.de → http://frontend:80`.
- **Später** (nach Repo-Extraktion): GitHub-Actions-Build nach ghcr (`…-pdf-backend`/`…-pdf-frontend`), Deploy per `docker compose pull && up -d`, Rollback über Image-Tag wie im Hauptprojekt.

## 8a. Entscheidungsvorlage: Anmeldung mit der Windows-Kennung (offen)

**Stand 2026-07-30 — bewusst nicht umgesetzt, Entscheidung liegt bei der IT.**

### Die eine Sache, die nicht geht

Eine Webseite kann die Windows-Kennung **nicht** von sich aus auslesen. Browser
geben sie nicht an JavaScript heraus — sonst könnte jede beliebige Seite
feststellen, wer am Rechner sitzt. Es gibt dafür keine Schnittstelle; die
gelegentlich zitierten Auslese-Verfahren sind ActiveX-Relikte des Internet
Explorer. „Automatisch erkennen" ist also nur über die **Authentifizierung auf
HTTP-Ebene** möglich, nicht über Programmcode in der Anwendung.

### Drei mögliche Wege

| Weg | Nutzererlebnis | Voraussetzungen | Eignung |
|---|---|---|---|
| **1. Kerberos/SPNEGO** (Integrierte Windows-Authentifizierung) | keine Eingabe, kein Klick | Dienstkonto + SPN + Keytab im AD; Reverse-Proxy mit GSSAPI (nginx `spnego-http-auth`, Apache `mod_auth_gssapi`, IIS); domänengebundene Clients; Seite in der Intranet-Zone | nur Hausnetz — **nicht** über den Cloudflare-Tunnel |
| **2. Entra ID (Azure AD) per OIDC** | ein Klick, danach meist ohne Eingabe (Windows-SSO über den Primary Refresh Token) | App-Registrierung im Tenant: Tenant-ID, Client-ID, Redirect-URI, Secret bzw. PKCE | funktioniert intern **und** extern, auch hinter Cloudflare |
| **3. Proxy-Header** (`X-Remote-User`; der Proxy erledigt Weg 1 oder 2) | wie der jeweilige Proxy | App **ausschließlich** über diesen Proxy erreichbar; Proxy muss den Header von außen zwingend überschreiben | nur Intranet, mit Auflagen |

### Sicherheitsauflagen

- **Weg 3 ist die gefährlichste Variante**: Ist die App auch direkt erreichbar,
  kann jeder den Header setzen und sich als beliebige Person ausgeben — inklusive
  Administrator. Umsetzung nur mit ausdrücklichem Opt-in (eigene
  Umgebungsvariable, Vorbild: `PDFAPP_TRUST_CF_HEADER`), Bindung an die
  Proxy-IP und deutlicher Warnung in der Doku.
- **Weg 2** braucht saubere Prüfung von `state`, `nonce`, Signatur, `iss`, `aud`
  und Ablauf des ID-Tokens; die Rolle darf nicht aus dem Token übernommen
  werden, ohne dass festgelegt ist, welche Gruppe Administratorrechte erhält.
- Für alle Wege zu klären: Wird beim ersten Anmelden **automatisch ein Konto
  angelegt**? Bleibt die offene Registrierung mit Passwort daneben bestehen?
  Werden Konten anhand der E-Mail-Adresse zusammengeführt (Achtung:
  Kontoübernahme, wenn die Adresse nicht verifiziert ist)?

### Auswirkung auf das Datenschutzversprechen

Keine auf die Dateiverarbeitung — die bleibt speicherfrei. Gespeichert würde
weiterhin nur, was heute schon in `users` steht (Kennung/E-Mail, Rolle, Flags,
Einstellungen, Zeitstempel); statt des bcrypt-Hashes käme die Kennung vom
Identitätsanbieter. Die Datenschutzerklärung müsste den Abschnitt
„Benutzerkonten" um den Anbieter und die übernommenen Angaben ergänzen.

### Empfehlung

- **Aktuelles Deployment** (Hetzner + Cloudflare, öffentlich erreichbar):
  Weg 2 (Entra ID). Weg 1 scheidet technisch aus.
- **Falls die App später im Hausnetz betrieben wird**: Weg 1 im Proxy plus
  Weg 3 in der Anwendung — dann ist wirklich keine Eingabe mehr nötig.
- Ohne Konfiguration bleiben beide Wege inaktiv, die anonyme Nutzung und die
  bestehende Anmeldung ändern sich nicht.

### Aufwand (geschätzt, wenn die Zugänge vorliegen)

| Baustein | Aufwand |
|---|---|
| Weg 2: OIDC-Anbindung (Discovery, Authorization Code + PKCE, `state`/`nonce`, Kontoanlage/-verknüpfung, Rollenzuordnung, Tests, Anmelde-Knopf, Callback-Ansicht) | 1–2 Tage |
| Weg 3: Header-Vertrauen inkl. IP-Bindung, Opt-in, Tests, Doku | 0,5 Tage |
| Voraussetzung durch die IT: App-Registrierung im Tenant bzw. SPN/Keytab und Proxy-Konfiguration | nicht im Projekt |

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
| F7 | Gestufte Limits: anonym 50/200 MB + 30/min, angemeldet 100/400 MB + 60/min | `test_auth.py` (Größe + Rate-Regression) + Live-Test | ✅ automatisiert + live geprüft |
| F8 | Preferences je Konto, Tools übernehmen Defaults, >16 KB → 413 | `test_auth.py` + manuell OCR-Default | ✅ automatisiert |
| F9 | `DELETE /me` mit Passwort → 204, Login danach 401 | `test_auth.py` | ✅ automatisiert |
| F10 | Schützen: fitz `needs_pass=True`; Entsperren korrekt; falsches Passwort 400 | `test_pdf_protect.py` | ✅ automatisiert |
| F11 | PDF→Word valides DOCX; `/api/pdf-convert/status` im Container `tabula: true` | `test_pdf_converter.py` + Container-curl | ✅ automatisiert |
| F12 | Formular-Designer: alle 6 Feldtypen landen als AcroForm im PDF (Typ, Auswahlwerte, Flags, Position maßstabsgetreu), erzeugte Felder sind mit „Formular ausfüllen" befüllbar | `test_form_designer.py` (10 Fälle) + Browser-E2E mit Feld-Prüfung im erzeugten PDF | ✅ automatisiert + live geprüft |
| F13 | Layout lokal: Autosave in localStorage, JSON-Datei-Export, Import von JSON und von vorhandenen PDF-Feldern — ohne jede Server-Speicherung | Browser-E2E (11 Schritte: ziehen → autosave → prüfen → JSON speichern → erzeugen → leeren → importieren → PDF-Felder übernehmen) | ✅ live geprüft |
| F14 | Formular-Berechnungen: Rechen-, Format- und Prüfaktion stehen normkonform im PDF (inkl. `/CO`), Rechenfeld schreibgeschützt | `test_form_advanced.py` + Browser-E2E mit Auslesen der Aktionen aus dem erzeugten PDF | ✅ automatisiert + live geprüft |
| F15 | Kein freies JavaScript im PDF: `app.alert`, `submitForm`, `eval` u.ä. werden abgelehnt, Feld bleibt ohne Skript | `test_form_advanced.py::test_formula_rejects_javascript` | ✅ automatisiert |
| F16 | CSV: Werte-Export, Vorlage, Serienbefüllung (Zeile → PDF, `dateiname`, ZIP ab zwei Zeilen, 200-Zeilen-Grenze, Hinweis bei unbekannten Spalten) | `test_form_advanced.py` (7 Fälle) + Browser-E2E mit Prüfung der befüllten Werte im ZIP | ✅ automatisiert + live geprüft |
| F17 | Stapelsignatur und Umbenennen im Batch; Bild ersetzen behält Position; Vertrauensanker liefern echtes Vertrauensurteil | `test_form_advanced.py` + Browser-E2E (Umbenennen, Bildaustausch im PDF nachgemessen) | ✅ automatisiert + live geprüft |
| F23 | Bearbeitung unterbrechen: Arbeitskopie + offene Änderungen werden im Browser gesichert, „Fortsetzen" stellt beides wieder her, Ergebnis landet korrekt im PDF | Browser-E2E (IndexedDB direkt ausgelesen, Neuladen, Anwenden, Textprüfung im PDF) | ✅ live geprüft |
| F24 | Sitzungsdatei: ZIP enthält dokument.pdf + arbeitsstand.json, lässt sich in einem anderen Browser laden; fremdes Werkzeug wird abgewiesen; Browser-Sicherung löschbar | Browser-E2E (9 Schritte, zweiter Browser-Kontext, manipulierte Datei) | ✅ live geprüft |
| F20 | Anzeige im Browser: pdf.js rendert lokal (Canvas bemalt), keine Thumbnail-Anfrage mehr, Zoom rendert neu statt zu skalieren, Seitenwechsel ohne Server | Browser-E2E (Canvas-Pixelprüfung, Netzwerk-Mitschnitt, Zoom-Vergleich) | ✅ live geprüft |
| F21 | Textbearbeitung erhält Sonderzeichen (—, „", m², €) und führt Fett/Kursiv fort; ohne Schriftdateien Rückfall mit Hinweis | `test_redact_fonts.py` (5 Fälle) + Browser-E2E mit Prüfung im erzeugten PDF | ✅ automatisiert + live geprüft |
| F22 | Musterschwärzung: neun Muster + Namenslisten, IBAN über Leerzeichen hinweg, Vorschau ändert nichts, Schwärzung entfernt Text und lässt Umfeld stehen | `test_redact_fonts.py` (11 Fälle) + Browser-E2E | ✅ automatisiert + live geprüft |
| F18 | Werkzeug-Freigabe: Admin sperrt Werkzeuge; anonym → Kachel ausgegraut mit Anmelde-Hinweis, API antwortet 403; angemeldet nutzbar; Aufheben wirkt sofort | `test_tool_access.py` (15 Fälle) + Browser-E2E (9 Schritte, inkl. direktem API-Aufruf aus der Seite) | ✅ automatisiert + live geprüft |
| F19 | Katalog-Konsistenz: Backend-Werkzeug-IDs = Kacheln der Oberfläche; jeder Katalog-Pfad ist eine echte Route; gemeinsame Vorschau-Endpunkte bleiben frei | `test_tool_access.py::test_catalog_matches_frontend_tiles` / `::test_catalog_paths_exist_in_app` / `::test_shared_preview_endpoint_stays_open` | ✅ automatisiert |
| F25 | Live-Editor: Eingabefeld liegt in Seitenkoordinaten auf dem Textblock, Schriftgröße/Fett/Kursiv/Farbe wirken, Verschieben und Größenänderung übernehmen, Fettung landet als eingebettete Bold-Schrift im PDF | Browser-E2E `e2e_liveeditor.mjs` (9 Schritte, Positionsvergleich in px, Schriftprüfung im erzeugten PDF) | ✅ live geprüft |
| F26 | Barrierefreiheit BITV 2.0: 0 axe-core-Verstöße (WCAG 2.0/2.1 A+AA) auf sechs Ansichten in hellem und dunklem Schema; Sprunglink ist erstes Tab-Ziel und setzt den Fokus auf den Hauptinhalt; reduzierte Bewegung wird respektiert | Browser-Audit `a11y.mjs` (axe-core, beide Farbschemata, Tastaturprüfung) | ✅ automatisiert geprüft |
| F27 | Geschwindigkeit: `/api/health` unter 5 ms statt 96 ms; Health bleibt unter Last antwortfähig; Textantworten komprimiert, PDFs unverändert durchgereicht; Werkzeug öffnet ohne pdf.js-Download | Messläufe `perf_web.mjs` + curl-Serie vor/nach der Änderung; gesamte pytest-Suite und alle vier E2E-Suiten unverändert grün | ✅ gemessen |
| F28 | Kapselung: kein Direktimport von fitz/pikepdf/pymupdf außerhalb von `app/pdf_backend.py`, keine eigenen Verfügbarkeits-Flags in Services | `test_pdf_backend.py` (Quelltext-Scan über alle Module, auch lokale Importe in Funktionen) | ✅ automatisiert erzwungen |
| F29 | Register: jede Komponente mit Zweck, Lizenz, Quelle; AGPL-Komponenten als Netzwerk-Copyleft markiert; `/api/licenses` liefert dieselbe Liste | `test_pdf_backend.py` (7 Fälle) | ✅ automatisiert |
| F30 | Quelltextpflicht sichtbar: Hinweis auf der Startseite nennt die AGPL-Komponenten und verlinkt den Quelltext, Fußzeile auf jeder Seite, Impressum-Abschnitt, Lizenzseite mit 15 Komponenten; fehlende Adresse wird als unerfüllte Bedingung angezeigt | Browser-E2E `e2e_lizenzen.mjs` (7 Schritte) + axe-Audit über Lizenz- und Impressumsseite in beiden Farbschemata | ✅ live geprüft |
| S5 | Sicherheitskopfzeilen auf jeder Antwort (auch Fehlerseiten), CSP ohne `unsafe-inline`/`unsafe-eval` im script-src, in nginx und Backend gesetzt | `test_hardening.py` (5 Fälle) + Browser-Lauf gegen eine Auslieferung mit den echten nginx-Kopfzeilen | ✅ automatisiert + live geprüft |
| S6 | Angriffe werden tatsächlich abgewehrt: Fremdskript, Inline-Skript, Datenabfluss, Clickjacking, offene Weiterleitung (absolut und protokollrelativ) | Browser-E2E `e2e_haertung.mjs` (6 Angriffe ausgeführt) | ✅ live geprüft |
| S7 | Zu große Anfrage wird vor dem Einlesen abgewiesen (413), auch ohne Content-Length | `test_hardening.py` + Messung: 450 MB → 413 nach 11 ms | ✅ automatisiert + gemessen |
| S8 | Ressourcengrenzen: höchstens 5.000 Seiten je Dokument (zentral an `open_pdf`), Bildbomben ab 64 Megapixel abgewiesen | `test_hardening.py` (2 Fälle) | ✅ automatisiert |
| S9 | Office-Konvertierung isoliert: eigenes Profil je Aufruf, Verknüpfungen und Makros aus | Quelltextprüfung; vollständige Absicherung erfordert Netz-Isolation des Konvertierungsprozesses (Betriebskonzept) | 🟡 gemindert, Restrisiko dokumentiert |
| S10 | Fehlerantworten ohne Pfade, Bibliotheksnamen oder Rückverfolgung | `test_hardening.py::test_error_messages_do_not_leak_internals` | ✅ automatisiert |
| S11 | Kopfzeilen gegen echtes nginx geprüft: keine doppelten Namen, Fehlerseiten (404/413/502) tragen sie ebenfalls, `Cache-Control: no-store` auf jeder API-Antwort | nginx 1.24 lokal mit der echten Konfiguration; `test_hardening.py` (Duplikat- und no-store-Fall) | ✅ automatisiert + live geprüft |
| S12 | nginx- und Backend-Kopfzeilen laufen nicht auseinander; jeder location-Block bindet das Schnipsel ein | `test_hardening.py` (2 Fälle, beide durch absichtliche Abweichung gegengeprüft) | ✅ automatisiert |
| S13 | `.mjs` wird als JavaScript ausgeliefert — sonst verweigert der Browser wegen nosniff den pdf.js-Worker und die Vorschau bleibt leer | `test_hardening.py::test_nginx_serves_mjs_as_javascript` + acht E2E-Suiten gegen echtes nginx | ✅ automatisiert + live geprüft |
| D1 | Keine Datei-Persistenz nach Verarbeitung | Dateisystem-Diff vor/nach 7-Operationen-Serie | ✅ live geprüft (0 neue Dateien) |
| D2 | users-Tabelle nur E-Mail/Hash/Rolle/Flags/Prefs/Zeitstempel — keine IP | `\d users` + Code-Review models.py | ✅ per Modell |
| D3 | Mail-Adresse nie in Logs (Erfolg + Fehlerpfade) | Log-Grep nach Testversand gegen Debug-SMTP | ✅ live geprüft (0 Treffer, SMTP-Gegenprobe positiv) |
| D4 | Anonyme Verarbeitung ohne DB-Zugriff; App läuft bei gestopptem Postgres weiter. Einzige DB-Berührung im anonymen Pfad ist das Nachladen der Werkzeug-Freigabe (max. alle 30 s, ohne DB gar nicht, fail-open) | Live-Test mit nicht erreichbarer DB + `test_tool_access.py::test_without_database_nothing_is_restricted` | ✅ live geprüft (accounts:false, Register 503, Merge 200) |
| D5 | Registrierung nur mit Pflicht-Checkbox + Datenschutz-Link | Browser-Prüfung RegisterView | ✅ umgesetzt |
| D6 | Hinweis konsistent (Banner/Badge/Footer + Konto-Absatz) | Review der vier Hinweis-Stellen | ✅ umgesetzt |
| S1 | Anonyme Regression: Tools ohne Login byte-identisch | Smoke-Tests unverändert grün | ✅ automatisiert |
| S2 | Alle neuen Endpoints mit mindestens einem Test, Suite grün | `pytest tests/ -q` → 0 failed | ✅ (21 Tests) |
| S3 | `npm run type-check` + `build` fehlerfrei; keine Konsolen-Fehler | CI-Befehle + Playwright-Browserdurchlauf | ✅ live geprüft |
| S4 | Compose healthy; Konten überleben Neustart (pgdata) | `compose ps` + Konto → restart → Login | offen — beim Erst-Deploy prüfen (kein Docker-Daemon in der Dev-Sandbox) |
| SEC1 | SECRET_KEY + DB-Passwort Pflicht (`:?`), keine Secrets im Repo | `docker compose config` ohne .env → Fehler | ✅ umgesetzt |
| SEC2 | Ungültiger Token → 401, kein stilles Anonym-Downgrade | `test_auth.py` | ✅ automatisiert |
| SEC3 | Identische Login-Fehlertexte (keine User-Enumeration) | `test_auth.py` | ✅ automatisiert |

## 9a. Betrieb und Extraktion

Inbetriebnahme auf der NUC, Überführung in ein eigenes Repository,
Hetzner-Deployment sowie Sicherung, Aktualisierungsfristen, Verfügbarkeit und
Zuständigkeiten stehen in @BETRIEB.md.

Zwei Punkte daraus gehören auch hierher, weil sie Entscheidungen sind und keine
Handgriffe:

- **Die Extraktion ist erprobt.** `git subtree split --prefix=pdf-editor-app`
  erzeugt 154 Dateien in 22 Commits mit vollständiger Historie; der geklonte
  Ast baut und testet grün. Dafür trägt der Ordner seit dem 2026-08-01 eine
  **eigene `.gitignore`** — die im Wurzelverzeichnis wandert beim Split nicht
  mit, und ohne Ignoriermuster landete beim ersten `git add .` auch die `.env`
  in der Versionsverwaltung.
- **Nach der Extraktion muss `PDFAPP_SOURCE_URL` auf das neue Repository
  zeigen.** Die Angabe erfüllt eine Lizenzbedingung (AGPL § 13), keine
  Formalie: Zeigt sie auf einen Quelltext, der die Anwendung nicht mehr
  enthält, ist die Bedingung verletzt.

## 10. Roadmap

| Phase | Inhalt | Status |
|---|---|---|
| 1 | Scaffold: 16 Werkzeuge, Landing + Hinweis, ZIP-Download, Mailversand, Rate-Limiting, Docker, Impressum/Datenschutz-Gerüst | ✅ |
| 1.5 | Schützen/Entsperren, PDF→Word/Excel, optionale Konten (Nutzer + Admin), gestufte Limits, Postgres | ✅ |
| 1.6 | Adobe-Lücken: WYSIWYG-Textbearbeitung, Formulare, Schwärzen, Seitenzahlen/Kopf-Fußzeile, Bates, PDF/A, Bild-Signatur, PDF→Text, Suchen/Ersetzen, Flatten | ✅ |
| 1.6b | Annotations-Editor (Maus), digitale Signatur (pyHanko), Scan-Optimierung (OCRmyPDF), Batch-Verarbeitung | ✅ |
| 1.6c | Restpunkte: TOC-Editor, Async-Jobs, E-Mail-Verifikation, Passwort-Reset, Turnstile, Alembic | ✅ |
| 1.6d | Modulkatalog-Ausbau: Office→PDF, Exporte (MD/HTML/JSON/CSV), Bereinigen, Rechte, Signaturprüfung, TSA, Prüfakte, Qualitätsprüfung, lokale KI, Rolodex-Dashboard | ✅ |
| 1.6e | Formular-Designer (Felder aufziehen, Prüflauf, Layout lokal speichern + importieren, Übernahme vorhandener Felder) | ✅ |
| 1.6f | Endausbau: Formular-Berechnungen/Format/Wertebereich, CSV-Export + Serienbefüllung, Stapelsignatur, Umbenennen, Vertrauensanker, Bild ersetzen, KI-Modi | ✅ |
| 1.6g | Werkbank (eigene Rubrik „PDF-Editor": Multi-PDF-Seitenkomposition mit Mischen/Schneiden/Drehen/Leerseiten, Übergabe an alle Einzelwerkzeuge); Event-Loop-Auslagerung flächendeckend; Suchen/Ersetzen-Defekte behoben; 34 nachgezogene Endpunkt-Tests | ✅ |
| 1.7 | Anbieterdaten eintragen ✅, Erst-Deploy ✅ (produktiv auf pdf.flowaudit.de, 2026-08-05); SMTP-Zugang und Tunnel gemäß BETRIEB.md | 🟡 |
| 1.8 | Repo-Extraktion + CI (ghcr-Images, Smoke-Test-Gate) | offen |
| 2 | Plattform-Entscheidung: Zusammenarbeit/DMS/Cloud nur als getrenntes Opt-in-Modul mit Dokumentablage — oder dem Ökosystem überlassen und die App als dessen Verarbeitungs-API positionieren (Empfehlung) | offen |
| 2a | Anmeldung mit der Windows-Kennung (SSO) — Entscheidungsvorlage in Abschnitt 8a, Umsetzung nach Klärung mit der IT | offen (bewusst) |
