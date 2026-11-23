# Schwärzung: Ablauf und Plan-Format

Stand: 20.11.2026. Gehört zum [Prüfplan](pruefplan-schwaerzung.md) und zum [Plan für auditcore](plan-schwaerzung-auditcore.md). Das hier beschriebene Format ist der Vertrag, den `auditcore_pdf` 0.2.0 und die Oberflächenbausteine übernehmen sollen.

## Ablauf

1. **Plan** (`POST /api/pdf-extras/redact/plan`): Die Datei wird durchsucht, verändert wird nichts. Die Antwort enthält jede Fundstelle mit fester Kennung.
2. **Auswahl** (Oberfläche): Fundstellen ab- oder wieder anwählen, eigene Bereiche aufziehen.
3. **Anwendung** (`POST /api/pdf-extras/redact/apply`): Der Server sucht mit denselben Kriterien erneut und prüft dabei zwei Dinge: Der SHA-256 muss zur Datei passen, und jede übergebene Kennung muss vorhanden sein. Passt eines davon nicht, antwortet er mit HTTP 409. Danach schwärzt er genau die übergebenen Kennungen und Bereiche. Die erneute Suche dient nur der Absicherung, weil der Server keinen Zustand speichert. Was geschwärzt wird, bestimmt allein die Auswahl.
4. **Nachprüfung**: Die Ausgabe wird erneut durchsucht, im Seitentext, in den versteckten Ablagen und in den entpackten Rohdaten. Bleibt ein ausgewählter Text öfter lesbar als zulässig oder steht er noch in den Rohdaten, wird keine Datei ausgeliefert (HTTP 422).

   Gezählt wird je Gruppe, nämlich je Seite und einmal für alle versteckten Ablagen zusammen. Verglichen wird in einer flachen Form: NFKC, ohne Groß-/Kleinschreibung, ohne Leerraum. Zulässig ist die Zahl der Vorkommen vorher abzüglich derer, die ganz in ausgewählten Fundstellen oder eigenen Bereichen liegen. Im Seitentext entscheidet die Lage: Überlappen sich ausgewählte Stellen, etwa ein Begriff in einer ausgewählten E-Mail-Adresse oder eine Fundstelle unter einem eigenen Bereich, zählt jedes Vorkommen nur einmal. Ist die Lage einer Fundstelle unsicher, wird für diese Seite über die Texte gezählt; das ist strenger und kann nur zu viel melden, nie zu wenig. Dadurch zählen Schreibvarianten („Mustermann“, „MUSTERMANN“) und verschachtelte Begriffe („Max Mustermann“ und „Mustermann“) mit. Abgewählte gleiche Texte bleiben erlaubt. Eine Fundstelle über mehrere Zeilen wird zusätzlich je Zeile gezählt, damit ein Teilausfall auffällt. In den Rohdaten gilt ein Treffer nur dann nicht als Fehler, wenn derselbe Text als ganzes Wort in der Ausgabe lesbar bleibt, auf einer Seite oder in einer versteckten Ablage; „Krausestr.“ entschuldigt „Krause“ also nicht. In Inhaltsströmen von Seiten und Form-XObjects genügt es, dass der Text Teil des Sichtbaren ist, weil Wörter dort oft in Stücken stehen. Eingebettete Schriftdateien zählen nicht zu den Rohdaten. Alternativ- und Ersatztexte (`Alt`, `ActualText`, `E`, `TU`, auch als eigenes Objekt) werden immer ersetzt, sobald sie einen geschwärzten Text enthalten (Begriffe unter drei Zeichen nur als ganzes Wort), auch wenn derselbe Text an anderer Stelle abgewählt ist; andere versteckte Ablagen nur, wenn der Text überall ausgewählt ist. Geprüft werden dabei die Kodierungen UTF-8, Latin-1, CP1252, UTF-16 sowie Hex- und Oktal-Schreibweise.

   Die Meldung nennt nur die ersten drei Zeichen und die Seite, etwa „„Kra…“ noch 1× lesbar (Seite 2)“.

Bei mehreren Dateien gilt dasselbe über `POST /api/pdf-extras/redact/apply-batch`: je Datei ein Plan in derselben Reihenfolge (`plans` oder `plans_file`), Ergebnis als ZIP mit `schwaerzungen.txt`. Schlägt eine Datei fehl, wird keine Datei ausgeliefert. Dateinamen im ZIP:

- `<name>_geschwaerzt.pdf`: Es wurde etwas geschwärzt.
- `<name>_bereinigt.pdf`: Nichts ausgewählt, aber `sanitize` ist an. Die Datei wird bereinigt und ebenfalls nachgeprüft; im Protokoll steht „nichts ausgewählt, nur bereinigt“.
- `<name>.pdf`: Nichts ausgewählt und `sanitize` aus. Die Datei bleibt unverändert.
- Gleiche Namen erhalten `_1`, `_2` usw.

Die alten Endpunkte `/redact`, `/redact-patterns` (ohne `preview`) und `/batch` mit `operation=redact` schwärzen ohne Vorschau. Sie antworten deshalb standardmäßig mit HTTP 410. Nur mit `PDFAPP_REDACT_WITHOUT_PREVIEW=true` sind sie für Skripte wieder offen; sie nutzen dann dieselbe Suche und dieselbe Nachprüfung. Die Vorschau von `/redact-patterns` (`preview=true`) bleibt immer erreichbar. Die Oberfläche verwendet die alten Endpunkte nicht.

## Plan (Antwort von `/redact/plan`)

```json
{
  "version": 1,
  "sha256": "…64 Hexzeichen…",
  "criteria": {"patterns": ["iban", "email"], "terms": ["Mustermann"], "case_sensitive": false, "whole_word": true},
  "page_count": 2,
  "pages": [{"page": 1, "width": 595.0, "height": 842.0, "rotation": 0, "has_text": true}],
  "pages_without_text": [],
  "total": 9,
  "by_source": {"begriff:Mustermann": 3, "email": 2},
  "candidates": [
    {
      "id": "3f2a…(16 Hexzeichen)",
      "kind": "text",
      "source": "email",
      "label": "E-Mail-Adresse",
      "text": "max.mustermann@example.org",
      "page": 1,
      "rects": [[0.171, 0.087, 0.330, 0.105]],
      "pdf_rect": [103.4, 73.2, 196.5, 88.3],
      "location": "Seitentext",
      "outside_view": false,
      "selected": true
    },
    {
      "id": "…", "kind": "hidden", "source": "begriff:Mustermann", "label": "Begriff „Mustermann“",
      "text": "Mustermann", "page": null, "rects": [], "pdf_rect": null,
      "location": "Metadaten (author)", "outside_view": false, "selected": true
    }
  ],
  "cleanup": {"metadata_fields": ["author"], "xmp": false, "attachments": 0, "javascript": false}
}
```

- `id` ist deterministisch: ein Hash aus Seite, Quelle, Textposition und normalisiertem Fundtext. Gleiche Datei und gleiche Kriterien ergeben dieselben Kennungen.
- `rects` sind Anzeigekoordinaten von 0 bis 1, bezogen auf die Seite, wie sie angezeigt wird. Drehung und CropBox sind also schon eingerechnet. Es gibt ein Rechteck je Textzeile. `pdf_rect` umfasst alle Zeilen in PDF-Koordinaten und ist nur für ältere Aufrufer gedacht.
- `kind: "hidden"` sind Fundstellen außerhalb des Seitentexts. Sie liegen in Metadaten, XMP, Lesezeichen, Kommentaren, Links, Formularfeldern oder Dateianhängen; `location` nennt die Stelle.
- `outside_view: true` sind Fundstellen außerhalb der CropBox. Sie werden mitgeschwärzt, sind in der Ansicht aber nicht zu sehen.
- `pages_without_text` sind Seiten mit Bild- oder Vektorinhalt ohne Textebene. Dort kann nichts automatisch gefunden werden.
- **Datenschutz:** Der Plan enthält Klartext der Fundstellen. Er wird nur übertragen, nirgends gespeichert und nicht protokolliert. Fehlermeldungen der Nachprüfung nennen höchstens die ersten drei Zeichen eines Treffers.

## Auswahl (Feld `plan` oder Datei-Teil `plan_file` von `/redact/apply`)

Die Auswahl kann als Formularfeld `plan` oder als Datei-Teil `plan_file` (JSON) kommen. Formularfelder begrenzt der Server auf 1 MB. Die Oberfläche schickt die Auswahl deshalb immer als Datei-Teil; dafür gilt eine Obergrenze von 8 MB. Für den Stapel heißen die Felder `plans` und `plans_file`. Die Auswahl enthält Fundstellen im Klartext. Der Server protokolliert sie nicht und speichert sie nicht. Erlaubt ist nur gültiges JSON ohne `NaN`, `Infinity` und Zahlen außerhalb des Wertebereichs; `page` ist eine ganze Zahl. Sonst antwortet der Server mit HTTP 400.

```json
{
  "sha256": "…aus dem Plan…",
  "criteria": {"…unverändert aus dem Plan…": true},
  "selected": ["3f2a…", "…"],
  "areas": [{"page": 1, "rect": [0.42, 0.08, 0.61, 0.10]}],
  "sanitize": true
}
```

- `selected` enthält die Kennungen, die geschwärzt werden sollen. Fehlt eine Kennung, bleibt die Stelle lesbar.
- `areas` sind eigene Bereiche, ebenfalls in Anzeigekoordinaten von 0 bis 1. Erlaubt sind höchstens 500 insgesamt und 100 je Seite. Die Oberfläche setzt dieselben Grenzen.
- `criteria` muss ein Objekt sein, `patterns` und `terms` Listen von Zeichenketten. Sonst antwortet der Server mit HTTP 400.
- `sanitize` (Vorgabe `true`) entfernt Metadaten einschließlich eigener Info-Schlüssel, XMP auch auf Seitenebene, `PieceInfo`, Dateianhänge, JavaScript, Vorschaubilder und Formular-Antworten. Unsichtbare Textebenen bleiben erhalten, damit OCR-Ebenen nicht verloren gehen.
- Unabhängig von `sanitize` entfernt jede Anwendung Folgendes:
  - XFA-Formulardaten, wie Acrobat beim Schwärzen;
  - Formularfelder und Kommentare, die eine Schwärzung berühren;
  - `ActualText`, `Alt` und `E` mit geschwärztem Text, im Strukturbaum und im Inhaltsstrom;
  - XMP-Pakete, die einen geschwärzten Text enthalten.

Antwort-Header von `/redact/apply`:

| Header | Inhalt |
|---|---|
| `X-Redactions` | Zahl der geschwärzten Fundstellen im Seitentext |
| `X-Redaction-Areas` | Zahl der eigenen Bereiche |
| `X-Redaction-Hidden` | Zahl der entfernten versteckten Fundstellen |
| `X-Redaction-Verified` | `true`; ohne bestandene Nachprüfung gibt es keine Datei |

## Statuscodes

| Code | Bedeutung |
|---|---|
| 400 | Eingabe ungeeignet: keine PDF, passwortgeschützt, unbekanntes Muster, mehr als 200 Begriffe, fehlerhafte Auswahl, zu viele Bereiche, Seite eines Bereichs gibt es nicht |
| 409 | Plan passt nicht zur Datei oder zu den Fundstellen, deshalb neu suchen |
| 410 | Alter Endpunkt ohne Vorschau, abgeschaltet (siehe oben) |
| 422 | Nachprüfung fand noch lesbare Fundstellen; keine Datei |
| 502 | KI-Namenserkennung lieferte ein ungültiges Ergebnis oder ist fehlgeschlagen (Meldung in `detail`) |
| 503 | KI-Namenserkennung gewählt, aber auf dem Server nicht installiert |

## Suche

- **Text:** Die Suche arbeitet zeichengenau auf dem Seitentext. Ein gewöhnlicher Zeilenumbruch im Fließtext zählt als Leerzeichen. Spalten- und Absatzwechsel trennen hart, sodass kein Treffer darüber hinwegläuft. Bei Begriffen wird die Silbentrennung („Muster-/mann“) aufgelöst.
- **Rechtecke:** Geschwärzt wird je Zeile die Vereinigung der Zeichenrechtecke. Nachbarzeichen wie Klammern, Kommas oder der Rest eines Wortes bleiben stehen.
- **Muster:** Sie werden ohne Rücksicht auf `case_sensitive` ausgewertet; der Schalter gilt nur für Begriffe. Folgende Prüfungen gelten:
  - IBAN: Modulo 97
  - Kreditkarte: Luhn
  - Steuer-ID: ISO 7064 MOD 11,10
  - Datum: echtes Kalenderdatum
  - IP-Adresse: Oktette bis 255, nicht nach „Version“, „Kapitel“ usw.
  - Aktenzeichen: nicht bei Rechtsgrundlagen wie „VO 2021/1060“
  - Telefon: ohne `/` oder `-` nur nach „Tel.“, „Telefon“, „Fax“ o. Ä.
- **Überlappungen:** Überlappen sich Treffer, gewinnt der längere. Bei gleicher Länge gilt die Rangfolge Begriff vor Muster vor KI. So zählt eine IBAN einmal und nicht zusätzlich als Telefon- oder Kartennummer. Eigene Begriffe weichen nur anderen Begriffen. Ein Begriff innerhalb einer E-Mail-Adresse bleibt deshalb eine eigene Fundstelle und bleibt nicht lesbar, wenn die Adresse abgewählt wird.
- **Normalisierung:** Ligaturen („ﬁ“) werden in Einzelbuchstaben zerlegt, zerlegte Umlaute (NFD) zusammengesetzt, Zeichen ohne Breite und weiche Trennzeichen in der Zeile entfernt. Ohne `case_sensitive` findet „Straßer“ auch „STRASSER“. Ein Bindestrich im Begriff darf von einem Zeilenumbruch gefolgt sein („Müller-/Lüdenscheidt“). Teilt MuPDF eine Zeile wegen großer Abstände, etwa im Blocksatz, wird über die Lücke hinweg gesucht.
- **Versteckte Seiteninhalte:** Gesucht und geschwärzt wird auch Text auf ausgeblendeten Ebenen (optionale Inhalte), außerhalb von CropBox und MediaBox, in weißer Schrift und im unsichtbaren Darstellungsmodus. Ebenen bleiben dabei ausgeblendet, die CropBox bleibt erhalten.
- **KI-Namenserkennung:** Sie läuft je Seite auf dem ganzen Seitentext; Treffer werden an harten Grenzen (Zellen, Spalten) geteilt. Kurze Abschnitte bis sechs Wörter (Tabellenzellen, Listeneinträge) prüft sie zusätzlich einzeln, führende Titel wie „Prof. Dr.“ vorher entfernt. „Nachname, Vorname“ gilt als Name, wenn die KI „Vorname Nachname“ als Person erkennt. Alles, was die KI meldet, ist Fundstelle (Quelle `ki_namen`). Die Bestandteile belegter Namen (mindestens zwei Bestandteile oder bestätigte Listenform; Doppelnamen als Ganzes) werden im ganzen Dokument wortgenau nachgesucht, nicht nach einem Artikel und nicht bei Monatskürzeln im Datum. Steht der Beleg nicht in einem Satz (kein kleingeschriebenes Wort in derselben Zelle, in der Zeile des Treffers oder direkt davor oder danach; Wörter wie „in“, „je“, „und“, „inkl“ zählen nicht) und bestätigt die KI ihn nicht vollständig im Mustersatz „Gestern habe ich … getroffen.“, wird ein Wort höchstens max(10, 4 × verschiedene direkte Fundstellentexte) Mal nachgesucht. Mindestens 50 gelten für Belege über Zellgrenzen mit Bestätigung und für Zellbelege, die der Mustersatz nur zum Teil bestätigt (dann nur die Wörter des bestätigten Teils). Darüber nur Stellen mit Anrede oder Titel davor („Herr“, „Frau“, „Hr.“, „Fr.“, „Dr.“, „Prof.“, „Dipl.-Ing.“, „Dipl.-Ing. (FH)“, auch „Dr. med.“). Kontaktwörter („Telefon“, „Telefax“, „Fax“, „Handy“ und weitere, auch in „Telefon-Nr“) werden nie nachgesucht. Häufige Spaltenköpfe („Pos“, „Menge“, „Summe“, „Betrag“, „Netto“, „Brutto“ und weitere) werden aus Zellbelegen nur mit Anrede nachgesucht; aus einem Satz oder der Listenform belegt, gelten sie als Nachname („Petra Preis“). Diese Fundstellen haben die Quelle `ki_namen_nachgesucht` (Bezeichnung „Namen (im Dokument nachgesucht)“), lassen sich gesammelt abwählen und erscheinen auch in `by_source` und in der alten Vorschau `findings[].pattern`. Liefert die KI-Funktion ein Ergebnis in falscher Form oder bricht sie ab, enden Vorschau und Anwenden mit HTTP 502 und einer Fehlermeldung, die beide Fälle unterscheidet.

## Bekannte Grenzen

- **Gescannte Seiten** ohne Textebene werden nur gemeldet (`pages_without_text`). Schwärzen lassen sie sich nur über eigene Bereiche.
- **Text in Bildern:** Die Nachprüfung durchsucht Bilddaten nicht.
- **Komprimierte oder große Anhänge bei `sanitize=false`:** Die Rohdatenprüfung erkennt Treffer nur in entpackten Strömen. Eingebettete Dateien, die selbst komprimiert sind (ZIP, Office, PDF im PDF), werden nicht entpackt. Für solche Fälle `sanitize` anlassen; dann werden Anhänge entfernt.
- **Laufzeit:** 500 dichte Seiten mit 45 000 Fundstellen brauchen rund 5 s für den Plan und 51 s zum Anwenden. 8 000 E-Mail-Adressen neben 40 000 weiteren Zeichenketten brauchen rund 1 s für den Plan und 14 s zum Anwenden. Es gibt keinen Hintergrund-Job.
- **Inhaltsströme:** Steht ein abgewählter längerer Text sichtbar auf der Seite (etwa „Krausestraße“), wird ein ausgewählter kürzerer Text („Krause“) in Inhaltsströmen nicht als Rest gemeldet, auch wenn er dort außerhalb des Sichtbaren stünde, etwa in einem Kommentar. Gezeichneter Text wird über den Seitentext ohnehin erkannt.
- **Kurze Begriffe:** Die Rohdatenprüfung berücksichtigt erst Texte ab vier Zeichen, sonst gäbe es zu viele Zufallstreffer. Kürzere Begriffe werden im Seitentext und in versteckten Ablagen gezählt und in Alternativtexten ersetzt, aber nicht in allen Rohdaten gesucht.
- **Ebenen:** Ausgeblendete Ebenen, `Usage`-Einstellungen und Sichtbarkeitsregeln (`/OCMD`, auch direkt in den Ressourcen) werden für Suche und Schwärzung eingeblendet und danach wiederhergestellt. Sichtbarkeit, die nur über Skripte oder Druckeinstellungen gesteuert wird, erfasst das nicht.
