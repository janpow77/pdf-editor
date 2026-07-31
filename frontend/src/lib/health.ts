/**
 * Gemeinsamer Zugriff auf `/api/health`.
 *
 * Die Startseite fragte den Endpunkt bisher doppelt ab (Kachelraster und
 * Hinweisleiste), und bei jedem Wechsel zurück zur Übersicht erneut. Die
 * Antwort beschreibt nur die Server-Ausstattung und die Werkzeug-Freigabe —
 * die ändert sich nicht im Sekundentakt. Deshalb: parallele Aufrufe teilen
 * sich eine Anfrage, und das Ergebnis gilt für eine Minute.
 *
 * Kein Zwischenspeichern über den Tab hinaus: nach einer Änderung durch die
 * Administration soll ein Neuladen der Seite sofort den neuen Stand zeigen.
 */

import { apiGetJson } from '@/lib/api'

export interface HealthInfo {
  status: string
  accounts: boolean
  turnstile_site_key: string | null
  account_flows: boolean
  login_required_tools?: string[]
  features?: Record<string, boolean>
}

const TTL_MS = 60_000

let cached: HealthInfo | null = null
let cachedAt = 0
let inFlight: Promise<HealthInfo> | null = null

export async function getHealth(): Promise<HealthInfo> {
  if (cached && Date.now() - cachedAt < TTL_MS) return cached
  if (inFlight) return inFlight

  inFlight = apiGetJson<HealthInfo>('/api/health')
    .then((info) => {
      cached = info
      cachedAt = Date.now()
      return info
    })
    .finally(() => {
      inFlight = null
    })
  return inFlight
}

/** Nach Admin-Änderungen: nächster Aufruf holt frisch. */
export function invalidateHealth(): void {
  cached = null
  cachedAt = 0
}
