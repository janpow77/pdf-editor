/**
 * Fetch-Helfer der öffentlichen PDF-Editor-App — bewusst OHNE Authentifizierung.
 *
 * Portierung von useAuthFetch.ts aus audit_designer: identische
 * FormData-Upload-, Timeout- und Blob-Download-Logik, aber ohne Bearer-Token
 * (die App ist anonym nutzbar). Zusätzlich landet jede heruntergeladene Datei
 * in der Sitzungs-Ergebnisliste (lib/results.ts) für ZIP-Download/Mailversand —
 * ausschließlich im Browser-Speicher, nie auf dem Server.
 */

import { authHeader, isAuthenticated, logout } from '@/lib/auth'
import { addResult } from '@/lib/results'

const DEFAULT_TIMEOUT = 5 * 60 * 1000 // 5 Minuten

async function throwFromResponse(response: Response): Promise<never> {
  // Abgelaufene/ungültige Anmeldung: Token verwerfen, Fehler durchreichen
  if (response.status === 401 && isAuthenticated.value) logout()
  const err = await response.json().catch(() => ({ detail: response.statusText }))
  throw new Error(err.detail || `Fehler ${response.status}`)
}

/** POST einer FormData mit Per-Request-Timeout. Wirft bei !ok. */
export async function apiPost(
  url: string,
  formData: FormData,
  options?: { timeout?: number },
): Promise<Response> {
  const controller = new AbortController()
  const timeout = options?.timeout ?? DEFAULT_TIMEOUT
  const timer = setTimeout(() => controller.abort(), timeout)
  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: authHeader(),
      signal: controller.signal,
    })
    if (!response.ok) await throwFromResponse(response)
    return response
  } finally {
    clearTimeout(timer)
  }
}

/** GET, gibt JSON zurück. Wirft bei !ok. */
export async function apiGetJson<T = unknown>(url: string): Promise<T> {
  const response = await fetch(url, { headers: authHeader() })
  if (!response.ok) await throwFromResponse(response)
  return response.json() as Promise<T>
}

/** JSON-Request (PATCH/PUT/DELETE) mit optionaler Anmeldung. Wirft bei !ok. */
export async function apiJson<T = unknown>(
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  url: string,
  body?: unknown,
): Promise<T | null> {
  const response = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeader() },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) await throwFromResponse(response)
  if (response.status === 204) return null
  return response.json() as Promise<T>
}

/** Löst einen Browser-Download aus und merkt das Ergebnis für ZIP/Mail vor. */
export function downloadBlob(response: Response, fallbackName: string): Promise<void> {
  return response.blob().then((blob) => {
    const disposition = response.headers.get('Content-Disposition')
    let filename = fallbackName
    if (disposition) {
      const match = disposition.match(/filename="?([^";\n]+)"?/)
      if (match) filename = match[1]
    }
    addResult(filename, blob)
    const objectUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objectUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(objectUrl)
  })
}
