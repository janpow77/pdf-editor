/**
 * Arbeitsstand der Editoren: Bearbeitung unterbrechen und später fortsetzen.
 *
 * Zwei Wege, bewusst getrennt:
 *
 * 1. **Im Browser** (IndexedDB): Der Arbeitsstand wird beim Bearbeiten
 *    automatisch auf dem eigenen Gerät abgelegt. Beim nächsten Öffnen bietet
 *    das Werkzeug an, dort weiterzumachen. Verlässt das Gerät nie — der Server
 *    sieht davon nichts. Für den Wechsel auf ein anderes Gerät taugt es nicht.
 *
 * 2. **Als Sitzungsdatei** (.zip): enthält die aktuelle Arbeitskopie als PDF
 *    plus die noch nicht angewandten Änderungen als JSON. Diese Datei kann man
 *    ablegen, mitnehmen und später wieder hochladen.
 *
 * Warum überhaupt eine ZIP-Datei und nicht nur das PDF? Ein reines PDF trägt
 * nur den bereits angewandten Stand — vorgemerkte Änderungen wären weg. Genau
 * die will man beim Unterbrechen aber behalten.
 */

import JSZip from 'jszip'

export const SESSION_VERSION = 1
const DB_NAME = 'pdfapp_worksessions'
const STORE = 'sessions'
/** Größere Dokumente werden nicht im Browser zwischengelagert (Quota). */
export const MAX_LOCAL_BYTES = 40 * 1024 * 1024

export interface WorkSession<S = unknown> {
  /** Werkzeug-Kennung, z.B. "textEditor" */
  tool: string
  /** Dateiname der Arbeitskopie */
  name: string
  /** aktuelle Arbeitskopie */
  blob: Blob
  /** werkzeugspezifischer Zustand (vorgemerkte Änderungen, Seite …) */
  state: S
  /** ISO-Zeitstempel der Sicherung */
  savedAt: string
}

// ── IndexedDB (klein gehalten, ohne Abhängigkeit) ─────────────

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function tx<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return openDb().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const request = run(db.transaction(STORE, mode).objectStore(STORE))
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error)
      }),
  )
}

/**
 * Reaktive Hüllen entfernen: Vue-Proxys sind nicht strukturiert klonbar,
 * IndexedDB würde sie mit DataCloneError ablehnen. Der Zustand ist ohnehin
 * JSON-fähig (er landet auch so in der Sitzungsdatei).
 */
function plain<S>(state: S): S {
  return JSON.parse(JSON.stringify(state ?? null)) as S
}

export type SaveResult = 'ok' | 'zu-gross' | 'fehlgeschlagen'

/** Arbeitsstand auf diesem Gerät sichern (überschreibt den vorherigen). */
export async function saveLocalSession<S>(
  tool: string,
  name: string,
  blob: Blob,
  state: S,
): Promise<SaveResult> {
  if (blob.size > MAX_LOCAL_BYTES) return 'zu-gross'
  const record: WorkSession<S> = {
    tool,
    name,
    blob,
    state: plain(state),
    savedAt: new Date().toISOString(),
  }
  try {
    await tx('readwrite', (store) => store.put(record, tool))
    return 'ok'
  } catch {
    return 'fehlgeschlagen' // privater Modus, volle Quota — Bearbeitung läuft weiter
  }
}

export async function loadLocalSession<S>(tool: string): Promise<WorkSession<S> | null> {
  try {
    const record = await tx<WorkSession<S> | undefined>('readonly', (store) => store.get(tool))
    return record && record.blob instanceof Blob ? record : null
  } catch {
    return null
  }
}

export async function clearLocalSession(tool: string): Promise<void> {
  try {
    await tx('readwrite', (store) => store.delete(tool))
  } catch {
    /* nichts zu tun */
  }
}

// ── Sitzungsdatei (.zip) ──────────────────────────────────────

function sessionFileName(name: string): string {
  return name.replace(/\.pdf$/i, '') + '_arbeitsstand.zip'
}

/** Arbeitskopie + offene Änderungen als ZIP herunterladen. */
export async function downloadSessionFile<S>(
  tool: string,
  name: string,
  blob: Blob,
  state: S,
): Promise<string> {
  const zip = new JSZip()
  zip.file('dokument.pdf', blob)
  zip.file(
    'arbeitsstand.json',
    JSON.stringify(
      {
        version: SESSION_VERSION,
        app: 'pdf-editor',
        tool,
        document: name,
        savedAt: new Date().toISOString(),
        state: plain(state),
      },
      null,
      2,
    ),
  )
  const out = await zip.generateAsync({ type: 'blob' })
  const url = URL.createObjectURL(out)
  const a = document.createElement('a')
  a.href = url
  a.download = sessionFileName(name)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  return a.download
}

export interface LoadedSession<S> {
  name: string
  blob: Blob
  state: S | null
  /** true, wenn die Datei aus einem anderen Werkzeug stammt */
  foreignTool: string | null
}

/**
 * Sitzungsdatei oder einfaches PDF einlesen.
 * Ein PDF ergibt einen Arbeitsstand ohne offene Änderungen.
 */
export async function readSessionFile<S>(file: File, tool: string): Promise<LoadedSession<S>> {
  if (file.name.toLowerCase().endsWith('.pdf')) {
    return { name: file.name, blob: file, state: null, foreignTool: null }
  }
  const zip = await JSZip.loadAsync(file)
  const pdfEntry = zip.file('dokument.pdf')
  if (!pdfEntry) throw new Error('Die Datei enthält kein dokument.pdf')
  const blob = await pdfEntry.async('blob')
  const metaEntry = zip.file('arbeitsstand.json')
  if (!metaEntry) {
    return { name: file.name.replace(/_arbeitsstand\.zip$/i, '.pdf'), blob, state: null, foreignTool: null }
  }
  const meta = JSON.parse(await metaEntry.async('string')) as {
    version?: number
    tool?: string
    document?: string
    state?: S
  }
  if (meta.version !== SESSION_VERSION) {
    throw new Error('Die Sitzungsdatei stammt aus einer anderen Programmversion')
  }
  return {
    name: meta.document || file.name.replace(/_arbeitsstand\.zip$/i, '.pdf'),
    blob: new Blob([blob], { type: 'application/pdf' }),
    state: meta.state ?? null,
    foreignTool: meta.tool && meta.tool !== tool ? meta.tool : null,
  }
}

/** „vor 5 Minuten" / „am 30.07.2026, 14:12 Uhr" */
export function formatSavedAt(iso: string): string {
  const then = new Date(iso).getTime()
  const minutes = Math.round((Date.now() - then) / 60000)
  if (minutes < 1) return 'gerade eben'
  if (minutes < 60) return `vor ${minutes} Minute${minutes === 1 ? '' : 'n'}`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `vor ${hours} Stunde${hours === 1 ? '' : 'n'}`
  return `am ${new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })} Uhr`
}
