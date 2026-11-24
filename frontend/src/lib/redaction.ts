/**
 * Datenformat der Schwärzung mit Pflicht-Vorschau (Backend: Bibliothek
 * auditcore_pdf.redaction). Der Plan enthält Klartext der Fundstellen und
 * bleibt deshalb nur im Arbeitsspeicher — kein Web Storage, kein Protokoll.
 */

export interface RedactionCriteria {
  patterns: string[]
  terms: string[]
  case_sensitive: boolean
  whole_word: boolean
}

export interface RedactionCandidate {
  id: string
  kind: 'text' | 'hidden'
  source: string
  label: string
  text: string
  page: number | null
  /** Anzeigekoordinaten 0…1 je Zeile, bezogen auf die gedrehte Seite. */
  rects: [number, number, number, number][]
  location: string
  outside_view: boolean
  selected: boolean
}

export interface RedactionPageInfo {
  page: number
  width: number
  height: number
  rotation: number
  has_text: boolean
}

export interface RedactionPlan {
  version: number
  sha256: string
  criteria: RedactionCriteria
  page_count: number
  pages: RedactionPageInfo[]
  pages_without_text: number[]
  total: number
  by_source: Record<string, number>
  candidates: RedactionCandidate[]
  cleanup: { metadata_fields: string[]; xmp: boolean; attachments: number; javascript: boolean }
}

export interface RedactionArea {
  id: string
  page: number
  rect: [number, number, number, number]
}

export interface RedactionSelection {
  sha256: string
  criteria: RedactionCriteria
  selected: string[]
  areas: { page: number; rect: [number, number, number, number] }[]
  sanitize: boolean
}

/** Gleiche Fundtexte derselben Quelle werden gemeinsam an- und abgewählt. */
export interface CandidateGroup {
  key: string
  source: string
  label: string
  text: string
  items: RedactionCandidate[]
  pages: number[]
  hidden: boolean
}

export function normalizeText(text: string): string {
  return text.normalize('NFKC').replace(/\s+/g, ' ').trim().toLocaleLowerCase('de')
}

export function groupCandidates(candidates: RedactionCandidate[]): CandidateGroup[] {
  const groups = new Map<string, CandidateGroup>()
  for (const candidate of candidates) {
    const key = `${candidate.source}\u001f${normalizeText(candidate.text)}`
    let group = groups.get(key)
    if (!group) {
      group = { key, source: candidate.source, label: candidate.label, text: candidate.text, items: [], pages: [], hidden: false }
      groups.set(key, group)
    }
    group.items.push(candidate)
    if (candidate.kind === 'hidden') group.hidden = true
    if (candidate.page && !group.pages.includes(candidate.page)) group.pages.push(candidate.page)
  }
  return [...groups.values()].sort((a, b) => b.items.length - a.items.length || a.text.localeCompare(b.text, 'de'))
}

export function formatPages(pages: number[]): string {
  const sorted = [...pages].sort((a, b) => a - b)
  const parts: string[] = []
  let start = sorted[0]
  let previous = sorted[0]
  for (const page of sorted.slice(1).concat([Number.NaN])) {
    if (page === previous + 1) {
      previous = page
      continue
    }
    if (start !== undefined) parts.push(start === previous ? `${start}` : `${start}–${previous}`)
    start = page
    previous = page
  }
  return parts.join(', ')
}

export function selectionPayload(
  plan: RedactionPlan,
  selected: Set<string>,
  areas: RedactionArea[],
  sanitize: boolean,
): RedactionSelection {
  return {
    sha256: plan.sha256,
    criteria: plan.criteria,
    selected: plan.candidates.filter((c) => selected.has(c.id)).map((c) => c.id),
    areas: areas.map(({ page, rect }) => ({ page, rect })),
    sanitize,
  }
}
