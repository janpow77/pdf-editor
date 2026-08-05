# Frontend-Refactoring 2026

## Zielbild

Die PDF-Werkzeug-Anwendung wurde auf eine modulare, Apple-nahe Oberfläche mit zentraler Theme-, Workspace-, Vorschau- und Fehlersteuerung umgestellt. Das Raster ist auf Desktop-Systemen die platzsparende Standardansicht. Das bestehende Rolodex bleibt als alternative, lokal gespeicherte Darstellung erhalten.

## Angepasste Architektur

### Globale UI-Zustände

- `frontend/src/composables/useTheme.ts` verwaltet Systempräferenz, manuelle Auswahl und die globale `dark`-Klasse. Ein blockierter Browser-Speicher verhindert die Theme-Nutzung nicht.
- `frontend/src/composables/useWorkspace.ts` enthält ausschließlich die Metadaten des aktiven Werkzeugs. Ein Revisionszähler verwirft beim globalen Schließen zusätzlich lokale Datei-, Canvas- und Komponentenstates.
- `frontend/src/composables/useNotifications.ts` stellt Erfolg, Information, Warnung und Fehler anwendungsweit bereit. Duplikate werden zusammengeführt und maximal vier Meldungen gleichzeitig angezeigt.
- `frontend/src/components/NotificationHost.vue` rendert die Meldungen als barrierefreie Live-Region in einer kompakten, Apple-nahen Glasoberfläche.

### Gemeinsame Metadaten und Upload-Prüfung

- `frontend/src/lib/toolCatalog.ts` ist die gemeinsame Quelle für Raster, Rolodex, Suche, Fokus-Header und Breadcrumbs.
- `frontend/src/lib/fileValidation.ts` prüft PDF-Endung, Dateigröße, Gesamtgröße und eine `%PDF-`-Signatur innerhalb der ersten 1.024 Bytes.
- `frontend/src/lib/pdfFactory.ts` erzeugt eine leere DIN-A4-PDF vollständig lokal und ohne zusätzliche Bibliothek.
- `frontend/src/lib/api.ts` fängt Netzwerk-, Server- und Timeoutfehler zentral ab und meldet erfolgreiche Downloads.

## Geänderte Oberflächen

### Startseite und Navigation

- `frontend/src/views/LandingView.vue`: Spotlight-artige Werkzeugsuche, typografische Hierarchie, Halbgeviertstriche und vollständiger Workspace-Reset.
- `frontend/src/components/ToolGrid.vue`: responsives Raster als Standard, optionales Rolodex, kontraststarke Kategorien, Breadcrumbs und Fokus-Arbeitsfläche.
- `frontend/src/App.vue`: kompakter Fokus-Header mit Logo, aktivem Werkzeug und Theme-Schalter sowie globaler Notification-Host.
- `frontend/src/components/AppFooter.vue`: Datenschutz und Open Source als kompakte Akkordeons statt großer Hinweisflächen.

### Apple-nahes Designsystem

- `frontend/src/style.css`: Systemschrift, Glasmaterialien, weiche Radien, mehrstufige Schatten, Fokusindikatoren, Inline-Fehler und Reduced-Motion-Regeln.
- `frontend/tailwind.config.js`: klassenbasierter Dark Mode, wiederverwendbare Apple-Schattenstufen sowie die fein abgestuften Material-Deckkraftwerte (15/35/45/65/82/85) außerhalb der Tailwind-Standardskala. (Eine früher hier genannte `apple-utilities.css` wurde nie angelegt — die Werte liegen vollständig in der Tailwind-Konfiguration.)
- `frontend/src/components/FileDrop.vue`: gemeinsame Uploadfläche mit Inline-Validierung; übernimmt zusätzlich per Handoff übergebene Ergebnisse anderer Werkzeuge. Der Leerstart des Formular-Designers liegt im Designer selbst (A4 hoch/quer, eine Quelle: `lib/pdfFactory.ts`).

## PDF-State und Vorschauen

### Teilen

`frontend/src/components/tools/PdfSplit.vue` verwirft beim Dokumentwechsel sofort:

- vorherige Thumbnails,
- vorherige Seitenzahl,
- vorherige Bereichseingaben,
- laufende Preview-Zuordnung.

Ein monotoner Request-Zähler verhindert, dass eine verspätete Antwort der alten Datei den aktuellen Zustand überschreibt. Ein Komponenten-Schlüssel erzeugt zusätzlich eine neue Thumbnail-Rasterinstanz.

### Zusammenführen

`frontend/src/components/tools/PdfMerge.vue` verwendet stabile Listeneinträge mit:

- eindeutiger ID,
- PDF-Datei,
- Thumbnail der ersten Seite,
- Lade- und Fehlerzustand.

Beim Umsortieren bewegen sich Datei und Vorschau als eine Einheit. Neben Drag & Drop stehen tastaturbedienbare Schaltflächen „nach oben“ und „nach unten“ zur Verfügung. Einzelgröße, Gesamtgröße und die serverseitige Höchstzahl von 50 Dateien werden bereits im Browser geprüft.

### Globale Darstellungsgröße

- `frontend/src/composables/usePdfTools.ts`: Thumbnail-Breite von 200 auf 320 Pixel erhöht, also um 60 Prozent.
- `frontend/src/components/tools/PageThumbnailGrid.vue`: Standardraster von sechs auf vier Spalten reduziert; auf kleinen Displays automatisch zwei Spalten.
- `frontend/src/components/PdfViewer.vue`: auf großen Arbeitsflächen mindestens 150 Prozent Startskalierung; auf kleinen Displays weiterhin eingepasste Breite. Ein Dokument-Generationszähler schützt auch hier vor veralteten Renderantworten.

### Formular-Designer

Der Formular-Designer erhält über die gemeinsame Upload-Komponente eine zweite, gleichwertige Einstiegskarte „Leeres Formular erstellen“. `pdfFactory.ts` erzeugt dafür eine weiße DIN-A4-Seite im Hochformat im Browser-Arbeitsspeicher und übergibt sie als reguläre `File`-Instanz an den bestehenden Editor. Ein zuvor lokal gespeichertes Formularlayout wird bei diesem ausdrücklich leeren Einstieg nicht automatisch übernommen.

## Barrierefreiheit

- deutliche Fokusindikatoren mit Innen- und Außenkontrast,
- Sprunglink zum Hauptinhalt,
- semantische Breadcrumbs,
- Tastaturnavigation für Rolodex und auswählbare Thumbnails,
- tastaturbedienbare Reihenfolge im Zusammenführen-Modul,
- Live-Regionen für Status und Fehler,
- kontraststärkere inaktive Tabs und Flächengrenzen,
- Beachtung von `prefers-reduced-motion`,
- erklärende Inline-Fehler direkt am Eingabekontext.

## Validierung

- Es wurde keine GitHub-Action und keine Workflow-Datei hinzugefügt oder verändert.
- Der Draft-PR nutzt ausschließlich bereits im Repository vorhandene Prüfungen.
- Für den PR-Head wurden keine vorhandenen Workflow-Runs oder Statuschecks gefunden; das Repository stellt derzeit somit keine automatische Pull-Request-Buildprüfung bereit.
- Das lokal erzeugte DIN-A4-PDF wurde mit PyMuPDF erfolgreich geöffnet: eine Seite mit 595,28 × 841,89 PDF-Punkten.
- Ein vollständiger lokaler `npm run build` war in der Ausführungsumgebung nicht möglich, weil der GitHub-Checkout wegen fehlender DNS-Auflösung nicht erreichbar war und die interne npm-Registry die benötigten Pakete nicht vollständig bereitstellte.

## Geänderte Dateien

- `FRONTEND_REFACTORING.md`
- `frontend/src/App.vue`
- `frontend/src/components/AppFooter.vue`
- `frontend/src/components/FileDrop.vue`
- `frontend/src/components/NotificationHost.vue`
- `frontend/src/components/PdfViewer.vue`
- `frontend/src/components/ToolGrid.vue`
- `frontend/src/components/tools/PageThumbnailGrid.vue`
- `frontend/src/components/tools/PdfMerge.vue`
- `frontend/src/components/tools/PdfSplit.vue`
- `frontend/src/composables/useNotifications.ts`
- `frontend/src/composables/usePdfTools.ts`
- `frontend/src/composables/useTheme.ts`
- `frontend/src/composables/useWorkspace.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/fileValidation.ts`
- `frontend/src/lib/pdfFactory.ts`
- `frontend/src/lib/toolCatalog.ts`
- `frontend/src/main.ts`
- `frontend/src/style.css`
- `frontend/src/views/LandingView.vue`
- `frontend/tailwind.config.js`
