/**
 * Zentrale Netzwerk- und Download-Helfer der PDF-Anwendung.
 *
 * Uploads, JSON-Aktionen und Downloads verwenden dieselben Zeitlimits,
 * verständlichen Fehlertexte und optionalen Abbruchsignale. Fachkomponenten
 * behalten zusätzlich ihre Inline-Zustände, ohne Netzwerklogik zu duplizieren.
 */
import { useNotifications } from '@/composables/useNotifications'
import { authHeader, isAuthenticated, logout } from '@/lib/auth'
import { addResult } from '@/lib/results'

const DEFAULT_TIMEOUT = 5 * 60 * 1000

export interface ApiRequestOptions {
  timeout?: number
  /** Vorschau- oder Hintergrundaufrufe können die globale Meldung abschalten. */
  notifyOnError?: boolean
  /** Ein Werkzeug kann einen überholten Datei-/Preview-Aufruf aktiv abbrechen. */
  signal?: AbortSignal
}

/** Übersetzt unterschiedliche FastAPI-Fehlerformen in einen lesbaren Text. */
function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((entry) => {
        if (typeof entry === 'string') return entry
        if (entry && typeof entry === 'object' && 'msg' in entry) return String(entry.msg)
        return ''
      })
      .filter(Boolean)
    if (messages.length) return messages.join(' ')
  }
  return fallback
}

async function throwFromResponse(response: Response): Promise<never> {
  if (response.status === 401 && isAuthenticated.value) logout()

  const payload = await response.json().catch(() => ({ detail: response.statusText })) as {
    detail?: unknown
  }
  throw new Error(detailMessage(payload.detail, `Serverfehler ${response.status}`))
}

/**
 * Erstellt ein eigenes Abbruchsignal und verbindet es mit einem optionalen
 * Werkzeugsignal. Listener und Timer werden in jedem Ausgangspfad entfernt.
 */
async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  options: ApiRequestOptions = {},
): Promise<Response> {
  const controller = new AbortController()
  const externalSignal = options.signal
  const abortFromExternal = () => controller.abort(externalSignal?.reason)

  if (externalSignal?.aborted) abortFromExternal()
  else externalSignal?.addEventListener('abort', abortFromExternal, { once: true })

  const timer = globalThis.setTimeout(
    () => controller.abort(new DOMException('Zeitlimit überschritten', 'AbortError')),
    options.timeout ?? DEFAULT_TIMEOUT,
  )

  try {
    return await fetch(url, { ...init, signal: controller.signal })
  } finally {
    globalThis.clearTimeout(timer)
    externalSignal?.removeEventListener('abort', abortFromExternal)
  }
}

function notifyFailure(title: string, error: unknown, options?: ApiRequestOptions): void {
  if (options?.notifyOnError === false) return
  const notifications = useNotifications()
  notifications.error(title, notifications.errorFromUnknown(error))
}

/** POST einer FormData mit Abbruchsignal und zentraler Fehlerbehandlung. */
export async function apiPost(
  url: string,
  formData: FormData,
  options?: ApiRequestOptions,
): Promise<Response> {
  try {
    const response = await fetchWithTimeout(url, {
      method: 'POST',
      body: formData,
      headers: authHeader(),
    }, options)
    if (!response.ok) await throwFromResponse(response)
    return response
  } catch (error: unknown) {
    notifyFailure('Verarbeitung fehlgeschlagen', error, options)
    throw error
  }
}

/**
 * GET für Health-, Status- und Ergebnisabfragen. Hintergrundabfragen bleiben
 * standardmäßig still, können aber bei einer sichtbaren Nutzeraktion Toasts
 * aktivieren.
 */
export async function apiGetJson<T = unknown>(
  url: string,
  options: ApiRequestOptions = { notifyOnError: false },
): Promise<T> {
  try {
    const response = await fetchWithTimeout(url, { headers: authHeader() }, options)
    if (!response.ok) await throwFromResponse(response)
    return response.json() as Promise<T>
  } catch (error: unknown) {
    notifyFailure('Abfrage fehlgeschlagen', error, options)
    throw error
  }
}

/** JSON-Request mit derselben Timeout- und Fehlerdarstellung wie Uploads. */
export async function apiJson<T = unknown>(
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  url: string,
  body?: unknown,
  options?: ApiRequestOptions,
): Promise<T | null> {
  try {
    const response = await fetchWithTimeout(url, {
      method,
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: body === undefined ? undefined : JSON.stringify(body),
    }, options)
    if (!response.ok) await throwFromResponse(response)
    if (response.status === 204) return null
    return response.json() as Promise<T>
  } catch (error: unknown) {
    notifyFailure('Aktion fehlgeschlagen', error, options)
    throw error
  }
}

/** Entfernt Pfad- und Steuerzeichen aus serverseitig gelieferten Dateinamen. */
function safeFilename(value: string, fallback: string): string {
  const cleaned = value
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_')
    .trim()
  return cleaned || fallback
}

function filenameFromDisposition(disposition: string | null): string | null {
  if (!disposition) return null
  const encoded = disposition.match(/filename\*=UTF-8''([^;\n]+)/i)?.[1]
  if (encoded) {
    try {
      return decodeURIComponent(encoded)
    } catch {
      // Fällt auf die klassische filename-Angabe zurück.
    }
  }
  return disposition.match(/filename="?([^";\n]+)"?/i)?.[1] ?? null
}

/**
 * Löst den Download aus und übernimmt das Ergebnis in die lokale Ergebnisliste.
 * Object-URL und temporärer Link werden auch bei einem Browserfehler freigegeben.
 */
export async function downloadBlob(response: Response, fallbackName: string): Promise<void> {
  const blob = await response.blob()
  const filename = safeFilename(
    filenameFromDisposition(response.headers.get('Content-Disposition')) ?? fallbackName,
    fallbackName,
  )

  addResult(filename, blob)
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  try {
    anchor.href = objectUrl
    anchor.download = filename
    document.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    URL.revokeObjectURL(objectUrl)
  }

  useNotifications().success('Datei erstellt', `${filename} wurde zum Download bereitgestellt.`)
}
