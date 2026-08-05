/**
 * Gemeinsamer Zugriff auf `/api/health`.
 *
 * Parallele Aufrufe teilen sich eine Anfrage und das Ergebnis gilt eine Minute.
 * Neben der Server-Ausstattung werden auch die tatsächlich konfigurierten
 * Uploadgrenzen übernommen, damit Client- und Backendvalidierung nicht
 * auseinanderlaufen.
 */

import { apiGetJson } from '@/lib/api'
import { configureUploadLimits, type UploadLimitConfiguration } from '@/lib/fileValidation'

export interface HealthInfo {
  status: string
  accounts: boolean
  turnstile_site_key: string | null
  account_flows: boolean
  login_required_tools?: string[]
  features?: Record<string, boolean>
  upload_limits?: UploadLimitConfiguration
}

const TTL_MS = 60_000

let cached: HealthInfo | null = null
let cachedAt = 0
let inFlight: Promise<HealthInfo> | null = null

function applyHealthConfiguration(info: HealthInfo): HealthInfo {
  if (info.upload_limits) configureUploadLimits(info.upload_limits)
  return info
}

export async function getHealth(): Promise<HealthInfo> {
  if (cached && Date.now() - cachedAt < TTL_MS) return applyHealthConfiguration(cached)
  if (inFlight) return inFlight

  inFlight = apiGetJson<HealthInfo>('/api/health')
    .then((info) => {
      cached = applyHealthConfiguration(info)
      cachedAt = Date.now()
      return cached
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
