/**
 * Arbeitsstand der Editoren: Bearbeitung unterbrechen und später fortsetzen.
 *
 * Browser-Sicherungen liegen in IndexedDB; portable Sitzungen enthalten PDF
 * und JSON-Zustand als ZIP. Alle Daten bleiben lokal. Datenbankverbindungen,
 * Object-URLs und fehlerhafte beziehungsweise übergroße Importe werden zentral
 * behandelt, damit die drei Editoren keine eigenen Sonderpfade benötigen.
 */

import JSZip from 'jszip'
import { currentFileLimit, currentTotalLimit, validatePdfFile } from '@/lib/fileValidation'

export const SESSION_VERSION = 1
const DB_NAME = 'pdfapp_worksessions'
const STORE = 'sessions'
/** Größere Dokumente werden nicht im Browser zwischengelagert (Quota). */
export const MAX_LOCAL_BYTES = 40 * 1024 * 1024
const MAX_STATE_BYTES = 5 * 1024 * 1024

export interface WorkSession<S = unknown> {
  tool: string
  name: string
  blob: Blob
  state: S
  savedAt: string
}

function openDb(): Promise<IDBDatabase> {
  if (typeof indexedDB === 'undefined') {
    return Promise.reject(new Error('IndexedDB ist nicht verfügbar.'))
  }
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE)
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('Browser-Datenbank konnte nicht geöffnet werden.'))
    request.onblocked = () => reject(new Error('Browser-Datenbank ist durch einen anderen Tab blockiert.'))
  })
}

/**
 * Ein Vorgang gilt erst nach erfolgreichem Abschluss der gesamten Transaktion
 * als gespeichert. Die Datenbankverbindung wird in jedem Ausgangspfad beendet.
 */
async function tx<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDb()
  return new Promise<T>((resolve, reject) => {
    let result!: T
    let settled = false
    const finish = (callback: () => void) => {
      if (settled) return
      settled = true
      db.close()
      callback()
    }

    try {
      const transaction = db.transaction(STORE, mode)
      const request = run(transaction.objectStore(STORE))
      request.onsuccess = () => { result = request.result }
      request.onerror = () => {
        finish(() => reject(request.error ?? new Error('Browser-Datenbankvorgang fehlgeschlagen.')))
      }
      transaction.oncomplete = () => finish(() => resolve(result))
      transaction.onerror = () => {
        finish(() => reject(transaction.error ?? new Error('Browser-Datenbanktransaktion fehlgeschlagen.')))
      }
      transaction.onabort = () => {
        finish(() => reject(transaction.error ?? new Error('Browser-Datenbanktransaktion wurde abgebrochen.')))
      }
    } catch (error: unknown) {
      finish(() => reject(error))
    }
  })
}

/** Vue-Proxys entfernen und zyklische/nicht serialisierbare Zustände ablehnen. */
function plain<S>(state: S): S {
  return JSON.parse(JSON.stringify(state ?? null)) as S
}

export type SaveResult = 'ok' | 'zu-gross' | 'fehlgeschlagen'

export async function saveLocalSession<S>(
  tool: string,
  name: string,
  blob: Blob,
  state: S,
): Promise<SaveResult> {
  if (blob.size > Math.min(MAX_LOCAL_BYTES, currentFileLimit())) return 'zu-gross'
  try {
    const record: WorkSession<S> = {
      tool,
      name,
      blob,
      state: plain(state),
      savedAt: new Date().toISOString(),
    }
    await tx('readwrite', (store) => store.put(record, tool))
    return 'ok'
  } catch {
    return 'fehlgeschlagen'
  }
}

export async function loadLocalSession<S>(tool: string): Promise<WorkSession<S> | null> {
  try {
    const record = await tx<WorkSession<S> | undefined>('readonly', (store) => store.get(tool))
    if (!record || !(record.blob instanceof Blob) || record.blob.size > currentFileLimit()) return null
    return record
  } catch {
    return null
  }
}

export async function clearLocalSession(tool: string): Promise<void> {
  try {
    await tx('readwrite', (store) => store.delete(tool))
  } catch {
    // Ein gesperrter Browser-Speicher darf den Editor nicht blockieren.
  }
}

function safeBaseName(name: string): string {
  return name.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').trim() || 'dokument.pdf'
}

function sessionFileName(name: string): string {
  return safeBaseName(name).replace(/\.pdf$/i, '') + '_arbeitsstand.zip'
}

export async function downloadSessionFile<S>(
  tool: string,
  name: string,
  blob: Blob,
  state: S,
): Promise<string> {
  const plainState = plain(state)
  const zip = new JSZip()
  zip.file('dokument.pdf', blob)
  zip.file(
    'arbeitsstand.json',
    JSON.stringify({
      version: SESSION_VERSION,
      app: 'pdf-editor',
      tool,
      document: safeBaseName(name),
      savedAt: new Date().toISOString(),
      state: plainState,
    }, null, 2),
  )
  const out = await zip.generateAsync({ type: 'blob' })
  const filename = sessionFileName(name)
  const url = URL.createObjectURL(out)
  const anchor = document.createElement('a')
  try {
    anchor.href = url
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    URL.revokeObjectURL(url)
  }
  return filename
}

export interface LoadedSession<S> {
  name: string
  blob: Blob
  state: S | null
  foreignTool: string | null
}

async function validatedPdfBlob(blob: Blob, name: string): Promise<Blob> {
  if (blob.size > currentFileLimit()) throw new Error('Das PDF der Sitzung überschreitet das aktuelle Dateilimit.')
  const file = new File([blob], safeBaseName(name).replace(/\.zip$/i, '.pdf'), { type: 'application/pdf' })
  const validation = await validatePdfFile(file)
  if (!validation.valid) throw new Error(validation.message ?? 'Das Sitzungs-PDF ist ungültig.')
  return new Blob([blob], { type: 'application/pdf' })
}

/** Sitzungsdatei oder einfaches, validiertes PDF einlesen. */
export async function readSessionFile<S>(file: File, tool: string): Promise<LoadedSession<S>> {
  if (file.size > currentTotalLimit()) {
    throw new Error('Die Sitzungsdatei überschreitet das aktuelle Gesamtgrößenlimit.')
  }

  if (file.name.toLowerCase().endsWith('.pdf')) {
    const validation = await validatePdfFile(file)
    if (!validation.valid) throw new Error(validation.message ?? 'Die PDF-Datei ist ungültig.')
    return { name: safeBaseName(file.name), blob: file, state: null, foreignTool: null }
  }
  if (!file.name.toLowerCase().endsWith('.zip')) {
    throw new Error('Bitte wählen Sie eine PDF- oder Arbeitsstandsdatei im ZIP-Format.')
  }

  const zip = await JSZip.loadAsync(file)
  const pdfEntry = zip.file('dokument.pdf')
  if (!pdfEntry) throw new Error('Die Datei enthält kein dokument.pdf.')
  const pdfBlob = await validatedPdfBlob(await pdfEntry.async('blob'), file.name)

  const metaEntry = zip.file('arbeitsstand.json')
  if (!metaEntry) {
    return {
      name: safeBaseName(file.name.replace(/_arbeitsstand\.zip$/i, '.pdf')),
      blob: pdfBlob,
      state: null,
      foreignTool: null,
    }
  }

  const metaText = await metaEntry.async('string')
  if (new TextEncoder().encode(metaText).byteLength > MAX_STATE_BYTES) {
    throw new Error('Der gespeicherte Werkzeugzustand ist ungewöhnlich groß.')
  }
  const parsed = JSON.parse(metaText) as unknown
  if (!parsed || typeof parsed !== 'object') throw new Error('Die Sitzungsmetadaten sind ungültig.')
  const meta = parsed as { version?: number; tool?: string; document?: string; state?: S }
  if (meta.version !== SESSION_VERSION) {
    throw new Error('Die Sitzungsdatei stammt aus einer anderen Programmversion.')
  }

  return {
    name: safeBaseName(meta.document || file.name.replace(/_arbeitsstand\.zip$/i, '.pdf')),
    blob: pdfBlob,
    state: meta.state ?? null,
    foreignTool: meta.tool && meta.tool !== tool ? meta.tool : null,
  }
}

/** „vor 5 Minuten“ / „am 30.07.2026, 14:12 Uhr“. */
export function formatSavedAt(iso: string): string {
  const then = new Date(iso).getTime()
  if (!Number.isFinite(then)) return 'zu einem unbekannten Zeitpunkt'
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000))
  if (minutes < 1) return 'gerade eben'
  if (minutes < 60) return `vor ${minutes} Minute${minutes === 1 ? '' : 'n'}`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `vor ${hours} Stunde${hours === 1 ? '' : 'n'}`
  return `am ${new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })} Uhr`
}
