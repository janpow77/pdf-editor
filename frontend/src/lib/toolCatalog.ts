/**
 * Zentraler Katalog aller in der Startansicht angebotenen Werkzeuge.
 *
 * Die Metadaten waren zuvor direkt in der großen Raster-Komponente hinterlegt.
 * Durch die Trennung können Suche, Breadcrumbs, Fokus-Header und spätere
 * Favoriten dieselbe verlässliche Datenquelle verwenden. Das verhindert, dass
 * Bezeichnungen oder Kategorien an mehreren Stellen auseinanderlaufen.
 */

export interface ToolDefinition {
  id: string
  label: string
  description: string
  icon: string
  /** KI-Werkzeuge werden nur angezeigt, wenn das Backend sie meldet. */
  requiresAi?: boolean
}

export interface ToolGroupDefinition {
  key: string
  title: string
  icon: string
  tools: ToolDefinition[]
}

export const TOOL_GROUPS: ToolGroupDefinition[] = [
  {
    key: 'bearbeiten',
    title: 'Bearbeiten & Anmerken',
    icon: '✏️',
    tools: [
      { id: 'textEditor', label: 'Text bearbeiten', description: 'WYSIWYG direkt im Dokument', icon: '✏️' },
      { id: 'annotate', label: 'Anmerkungen', description: 'Markieren, stempeln und zeichnen', icon: '🖍️' },
      { id: 'searchReplace', label: 'Suchen & Ersetzen', description: 'Textstellen gezielt austauschen', icon: '🔁' },
      { id: 'signImage', label: 'Unterschrift', description: 'Bildsignatur präzise einfügen', icon: '✍️' },
      { id: 'imageReplace', label: 'Bild ersetzen', description: 'Logos und Grafiken austauschen', icon: '🖌️' },
      { id: 'formDesigner', label: 'Formular-Designer', description: 'Interaktive Felder neu anlegen', icon: '🧩' },
      { id: 'formFill', label: 'Formular ausfüllen', description: 'Vorhandene AcroForm-Felder bearbeiten', icon: '📋' },
      { id: 'tocEditor', label: 'Lesezeichen', description: 'Inhaltsstruktur und Sprungziele pflegen', icon: '🔖' },
    ],
  },
  {
    key: 'seiten',
    title: 'Seiten & Struktur',
    icon: '📑',
    tools: [
      { id: 'merge', label: 'Zusammenführen', description: 'Mehrere PDFs in Reihenfolge verbinden', icon: '📎' },
      { id: 'split', label: 'Teilen', description: 'PDF in definierte Bereiche aufteilen', icon: '✂️' },
      { id: 'rotate', label: 'Rotieren', description: 'Einzelne oder alle Seiten drehen', icon: '🔄' },
      { id: 'pageEditor', label: 'Seiten ordnen', description: 'Seiten verschieben oder entfernen', icon: '📑' },
      { id: 'insertBlank', label: 'Leere Seiten', description: 'Zusätzliche Seiten einfügen', icon: '➕' },
      { id: 'pdfCompare', label: 'PDF-Vergleich', description: 'Zwei Dokumentstände vergleichen', icon: '⚖️' },
    ],
  },
  {
    key: 'umwandeln',
    title: 'Umwandeln & Exportieren',
    icon: '🔁',
    tools: [
      { id: 'pdfToWord', label: 'PDF → Word', description: 'In eine bearbeitbare DOCX-Datei exportieren', icon: '📝' },
      { id: 'pdfToExcel', label: 'PDF → Excel', description: 'Tabellen als Arbeitsmappe extrahieren', icon: '📊' },
      { id: 'toImages', label: 'PDF → Bilder', description: 'Seiten als PNG oder JPEG ausgeben', icon: '🖼️' },
      { id: 'imagesToPdf', label: 'Bilder → PDF', description: 'Bilddateien zu einem PDF bündeln', icon: '📄' },
      { id: 'toText', label: 'PDF → Text', description: 'Reinen Dokumenttext extrahieren', icon: '📃' },
      { id: 'pdfExport', label: 'PDF exportieren', description: 'Markdown, HTML, JSON oder CSV erzeugen', icon: '📤' },
      { id: 'ocr', label: 'OCR', description: 'Scans durchsuchbar machen', icon: '🔍' },
      { id: 'pdfa', label: 'PDF/A', description: 'Dokument in ein Archivformat überführen', icon: '🗄️' },
    ],
  },
  {
    key: 'schuetzen',
    title: 'Schützen & Signieren',
    icon: '🔏',
    tools: [
      { id: 'protect', label: 'Schützen / Entsperren', description: 'Passwortschutz setzen oder entfernen', icon: '🔒' },
      { id: 'permissions', label: 'Rechteverwaltung', description: 'Drucken und Kopieren einschränken', icon: '🛡️' },
      { id: 'redact', label: 'Schwärzen', description: 'Sensible Inhalte unwiderruflich entfernen', icon: '⬛' },
      { id: 'clean', label: 'Bereinigen', description: 'Metadaten und versteckte Inhalte entfernen', icon: '🧽' },
      { id: 'flatten', label: 'Einbrennen', description: 'Anmerkungen dauerhaft fixieren', icon: '🔥' },
      { id: 'signDigital', label: 'Digital signieren', description: 'Zertifikatsbasierte PAdES-Signatur', icon: '🔏' },
      { id: 'verifySignatures', label: 'Signatur prüfen', description: 'Integrität und Unterzeichner kontrollieren', icon: '✅' },
    ],
  },
  {
    key: 'stempel',
    title: 'Stempel & Nummern',
    icon: '🏷️',
    tools: [
      { id: 'watermark', label: 'Wasserzeichen', description: 'Text oder Bild dezent überlagern', icon: '💧' },
      { id: 'pageNumbers', label: 'Seitenzahlen', description: 'Flexible Nummerierungen ergänzen', icon: '🔢' },
      { id: 'headerFooter', label: 'Kopf- / Fußzeile', description: 'Wiederkehrende Texte positionieren', icon: '📰' },
      { id: 'bates', label: 'Bates-Nummern', description: 'Dokumente revisionssicher kennzeichnen', icon: '🏷️' },
      { id: 'pruefakte', label: 'Prüfakte', description: 'Akte mit Lesezeichen und Bates erzeugen', icon: '🗂️' },
    ],
  },
  {
    key: 'pruefen',
    title: 'Prüfen & Optimieren',
    icon: '🩺',
    tools: [
      { id: 'compress', label: 'Komprimieren', description: 'Dateigröße kontrolliert reduzieren', icon: '🗜️' },
      { id: 'scanOptimize', label: 'Scan optimieren', description: 'Geraderücken, säubern und erkennen', icon: '🧹' },
      { id: 'qualityCheck', label: 'Qualitätsprüfung', description: 'Leere oder doppelte Seiten finden', icon: '🩺' },
      { id: 'metadata', label: 'Metadaten', description: 'Titel, Autor und Datumswerte bearbeiten', icon: 'ℹ️' },
      { id: 'batch', label: 'Batch', description: 'Viele Dateien in einem Durchlauf verarbeiten', icon: '📦' },
      { id: 'aiAssistant', label: 'KI-Assistent', description: 'Lokal zusammenfassen und Fragen stellen', icon: '🤖', requiresAi: true },
    ],
  },
  {
    key: 'office',
    title: 'Word & Office',
    icon: '🗃️',
    tools: [
      { id: 'wordToPdf', label: 'Word → PDF', description: 'DOCX zuverlässig konvertieren', icon: '📝' },
      { id: 'wordMerge', label: 'Word verbinden', description: 'Mehrere DOCX-Dateien zusammenführen', icon: '📋' },
      { id: 'wordDiff', label: 'Word-Vergleich', description: 'Inhaltliche Unterschiede sichtbar machen', icon: '🔍' },
      { id: 'wordMeta', label: 'Word-Metadaten', description: 'Dokumenteigenschaften bearbeiten', icon: 'ℹ️' },
      { id: 'excelMeta', label: 'Excel-Metadaten', description: 'Arbeitsmappeneigenschaften bearbeiten', icon: 'ℹ️' },
      { id: 'officeToPdf', label: 'Office → PDF', description: 'Excel, PowerPoint, ODF und RTF konvertieren', icon: '🗃️' },
    ],
  },
]

/** Liefert Werkzeug und Kategorie für Fokus-Header und Breadcrumbs. */
export function findTool(toolId: string | null | undefined):
  | { tool: ToolDefinition; group: ToolGroupDefinition }
  | null {
  if (!toolId) return null
  for (const group of TOOL_GROUPS) {
    const tool = group.tools.find((entry) => entry.id === toolId)
    if (tool) return { tool, group }
  }
  return null
}
