/**
 * Zentrale Netzwerk- und Download-Helfer der PDF-Anwendung.
 *
 * Alle schreibenden Workflows laufen durch dieses Modul. Dadurch werden
 * Serverfehler, Zeitüberschreitungen und erfolgreiche Downloads einheitlich
 * als Apple-artige Toasts angezeigt, ohne dass jedes Werkzeug eigene Meldungs-
 * logik duplizieren muss. Die Fachkomponenten behalten zusätzlich ihre
 * dezenten Inline-Hinweise, damit Fehler direkt am Arbeitskontext sichtbar sind.
 */
import { useNotifications } from '@/composables/useNotifications'
import { authHeader, isAuthenticated, logout } from '@/lib/auth'
import { addResult } from '@/lib/results'

const DEFAULT_TIMEOUT = 5 * 60 * 1000

export interface ApiRequestOptions {
  timeout?: number
  /** Vorschau- oder Hintergrundaufrufe können die globale Meldung abschalten. */
  notifyOnError?: boolean
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
 * POST einer FormData mit Abbruchsignal und verständlicher Fehlerbehandlung.
 * `useNotifications()` wird erst im Fehlerpfad aufgerufen. Dadurch besitzt das
 * Modul beim Import keine UI-Seiteneffekte und bleibt in Tests robuster.
 */
export async function apiPost(
  url: string,
  formData: FormData,
  options?: ApiRequestOptions,
): Promise<Response> {
  const controller = new AbortController()
  const timer = globalThis.setTimeout(
    () => controller.abort(),
    options?.timeout ?? DEFAULT_TIMEOUT,
  )

  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: authHeader(),
      signal: controller.signal,
    })
    if (!response.ok) await throwFromResponse(response)
    return response
  } catch (error: unknown) {
    if (options?.notifyOnError !== false) {
      const notifications = useNotifications()
      notifications.error(
        'Verarbeitung fehlgeschlagen',
        notifications.errorFromUnknown(error),
      )
    }
    throw error
  } finally {
    globalThis.clearTimeout(timer)
  }
}

/** GET ohne automatische Toasts, weil Health- und Statusabfragen im Hintergrund laufen. */
export async function apiGetJson<T = unknown>(url: string): Promise<T> {
  const response = await fetch(url, { headers: authHeader() })
  if (!response.ok) await throwFromResponse(response)
  return response.json() as Promise<T>
}

/** JSON-Request mit derselben zentralen Fehlerdarstellung wie Datei-Uploads. */
export async function apiJson<T = unknown>(
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  url: string,
  body?: unknown,
): Promise<T | null> {
  try {
    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', ...authHeader() },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
    if (!response.ok) await throwFromResponse(response)
    if (response.status === 204) return null
    return response.json() as Promise<T>
  } catch (error: unknown) {
    const notifications = useNotifications()
    notifications.error('Aktion fehlgeschlagen', notifications.errorFromUnknown(error))
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

/**
 * Löst den Download aus und übernimmt das Ergebnis in die lokale Ergebnisliste.
 * Die Erfolgsmeldung wird erst nach dem Erzeugen des Browser-Downloads gezeigt.
 */
export async function downloadBlob(response: Response, fallbackName: string): Promise<void> {
  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition')
  let filename = fallbackName
  if (disposition) {
    const match = disposition.match(/filename="?([^";\n]+)"?/)
    if (match) filename = match[1]
  }
  filename = safeFilename(filename, fallbackName)

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
