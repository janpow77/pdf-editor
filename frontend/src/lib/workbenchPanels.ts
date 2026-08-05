/**
 * Deklarative Seitenpanels der Werkbank: formularartige Transformationen, die
 * direkt im Vollbild-Editor auf dem aktuellen Stand laufen. Jede Angabe
 * spiegelt die Form-Parameter des jeweiligen Backend-Endpunkts — ein neues
 * Panel ist ein Eintrag hier, keine neue Komponente.
 *
 * Lange Läufe mit Job-Architektur (OCR, Scan optimieren) bleiben bewusst
 * draußen und öffnen weiterhin als Vollansicht über die Übergabe.
 */

export interface PanelField {
  name: string
  label: string
  type: 'text' | 'number' | 'password' | 'select' | 'checkbox'
  default?: string | number | boolean
  options?: { value: string; label: string }[]
  required?: boolean
  min?: number
  max?: number
  step?: number
  placeholder?: string
}

export interface PanelSpec {
  id: string
  title: string
  icon: string
  endpoint: string
  /** 'pdf': Antwort ersetzt die Komposition · 'report': Antwort ist ein Prüfbericht (JSON) */
  output: 'pdf' | 'report'
  applyLabel: string
  fields: PanelField[]
  /** Optional: wählbare Varianten mit eigenem Endpunkt (z. B. Schützen/Entsperren). */
  variants?: { value: string; label: string; endpoint: string }[]
  variantLabel?: string
}

const POSITIONS = [
  { value: 'top-left', label: 'Oben links' },
  { value: 'top-center', label: 'Oben Mitte' },
  { value: 'top-right', label: 'Oben rechts' },
  { value: 'bottom-left', label: 'Unten links' },
  { value: 'bottom-center', label: 'Unten Mitte' },
  { value: 'bottom-right', label: 'Unten rechts' },
]

export const WORKBENCH_PANELS: Record<string, PanelSpec> = {
  watermark: {
    id: 'watermark', title: 'Wasserzeichen', icon: '💧',
    endpoint: '/api/pdf-tools/watermark', output: 'pdf', applyLabel: 'Wasserzeichen anwenden',
    fields: [
      { name: 'text', label: 'Text', type: 'text', required: true, placeholder: 'ENTWURF' },
      { name: 'opacity', label: 'Deckkraft (0–1)', type: 'number', default: 0.3, min: 0.05, max: 1, step: 0.05 },
      { name: 'rotation', label: 'Drehung in Grad', type: 'number', default: -45, min: -180, max: 180, step: 5 },
    ],
  },
  pageNumbers: {
    id: 'pageNumbers', title: 'Seitenzahlen', icon: '🔢',
    endpoint: '/api/pdf-editor/page-numbers', output: 'pdf', applyLabel: 'Seitenzahlen einfügen',
    fields: [
      { name: 'position', label: 'Position', type: 'select', default: 'bottom-center', options: POSITIONS },
      { name: 'font_size', label: 'Schriftgröße', type: 'number', default: 10, min: 6, max: 24 },
      { name: 'start_page', label: 'Ab Seite', type: 'number', default: 1, min: 1 },
      { name: 'start_number', label: 'Startnummer', type: 'number', default: 1, min: 0 },
    ],
  },
  headerFooter: {
    id: 'headerFooter', title: 'Kopf-/Fußzeile', icon: '📰',
    endpoint: '/api/pdf-editor/header-footer', output: 'pdf', applyLabel: 'Kopf-/Fußzeile setzen',
    fields: [
      { name: 'header_left', label: 'Kopf links', type: 'text', default: '' },
      { name: 'header_center', label: 'Kopf Mitte', type: 'text', default: '' },
      { name: 'header_right', label: 'Kopf rechts', type: 'text', default: '' },
      { name: 'footer_left', label: 'Fuß links', type: 'text', default: '' },
      { name: 'footer_center', label: 'Fuß Mitte', type: 'text', default: '' },
      { name: 'footer_right', label: 'Fuß rechts', type: 'text', default: '' },
      { name: 'font_size', label: 'Schriftgröße', type: 'number', default: 9, min: 6, max: 18 },
    ],
  },
  bates: {
    id: 'bates', title: 'Bates-Nummern', icon: '🏷️',
    endpoint: '/api/pdf-extras/bates', output: 'pdf', applyLabel: 'Bates-Nummern stempeln',
    fields: [
      { name: 'prefix', label: 'Präfix', type: 'text', default: '', placeholder: 'AKTE-' },
      { name: 'start', label: 'Startnummer', type: 'number', default: 1, min: 0 },
      { name: 'digits', label: 'Stellen', type: 'number', default: 6, min: 1, max: 12 },
      { name: 'position', label: 'Position', type: 'select', default: 'bottom-right', options: POSITIONS },
    ],
  },
  compress: {
    id: 'compress', title: 'Komprimieren', icon: '🗜️',
    endpoint: '/api/pdf-tools/compress', output: 'pdf', applyLabel: 'Komprimieren',
    fields: [
      { name: 'quality', label: 'Qualität', type: 'select', default: 'medium', options: [
        { value: 'low', label: 'Stark (kleinste Datei)' },
        { value: 'medium', label: 'Ausgewogen' },
        { value: 'high', label: 'Schonend (beste Qualität)' },
      ] },
    ],
  },
  clean: {
    id: 'clean', title: 'Bereinigen', icon: '🧽',
    endpoint: '/api/pdf-more/clean', output: 'pdf', applyLabel: 'Metadaten & Verstecktes entfernen',
    fields: [],
  },
  pdfa: {
    id: 'pdfa', title: 'PDF/A', icon: '🗄️',
    endpoint: '/api/pdf-extras/to-pdfa', output: 'pdf', applyLabel: 'Nach PDF/A wandeln',
    fields: [
      { name: 'level', label: 'PDF/A-Level', type: 'select', default: '2b', options: [
        { value: '1b', label: 'PDF/A-1b' }, { value: '2b', label: 'PDF/A-2b' }, { value: '3b', label: 'PDF/A-3b' },
      ] },
    ],
  },
  // Eine Kachel, zwei Richtungen: Die Startseite kennt nur „Schützen /
  // Entsperren" (id protect) — ein eigenes unlock-Panel wäre aus dem Menü
  // nie erreichbar gewesen.
  protect: {
    id: 'protect', title: 'Schützen / Entsperren', icon: '🔒',
    endpoint: '/api/pdf-tools/protect', output: 'pdf', applyLabel: 'Anwenden',
    variantLabel: 'Aktion',
    variants: [
      { value: 'protect', label: 'Passwortschutz setzen', endpoint: '/api/pdf-tools/protect' },
      { value: 'unlock', label: 'Schutz entfernen', endpoint: '/api/pdf-tools/unlock' },
    ],
    fields: [
      { name: 'password', label: 'Passwort', type: 'password', required: true },
    ],
  },
  permissions: {
    id: 'permissions', title: 'Rechteverwaltung', icon: '🛡️',
    endpoint: '/api/pdf-more/permissions', output: 'pdf', applyLabel: 'Rechte setzen',
    fields: [
      { name: 'owner_password', label: 'Besitzer-Passwort', type: 'password', required: true },
      { name: 'allow_print', label: 'Drucken erlauben', type: 'checkbox', default: true },
      { name: 'allow_copy', label: 'Kopieren erlauben', type: 'checkbox', default: false },
      { name: 'allow_modify', label: 'Ändern erlauben', type: 'checkbox', default: false },
      { name: 'allow_annotate', label: 'Kommentieren erlauben', type: 'checkbox', default: true },
    ],
  },
  flatten: {
    id: 'flatten', title: 'Einbrennen', icon: '🔥',
    endpoint: '/api/pdf-editor/flatten', output: 'pdf', applyLabel: 'Anmerkungen einbrennen',
    fields: [],
  },
  searchReplace: {
    id: 'searchReplace', title: 'Suchen & Ersetzen', icon: '🔁',
    endpoint: '/api/pdf-editor/text/replace', output: 'pdf', applyLabel: 'Ersetzen',
    fields: [
      { name: 'search', label: 'Suchen nach', type: 'text', required: true },
      { name: 'replace', label: 'Ersetzen durch', type: 'text', default: '' },
      { name: 'match_case', label: 'Groß-/Kleinschreibung beachten', type: 'checkbox', default: true },
    ],
  },
  qualityCheck: {
    id: 'qualityCheck', title: 'Qualitätsprüfung', icon: '🩺',
    endpoint: '/api/pdf-more/quality-check', output: 'report', applyLabel: 'Prüfen',
    fields: [],
  },
}
