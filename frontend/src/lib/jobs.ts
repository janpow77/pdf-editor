/**
 * Async-Job-Helfer: startet eine Verarbeitung, pollt ihren Status und liefert
 * anschließend das Ergebnis. Alle Fehlerpfade laufen durch genau eine globale
 * Benachrichtigung; der Start-POST unterdrückt deshalb seinen eigenen Toast.
 */

import { useNotifications } from '@/composables/useNotifications'
import { apiGetJson, apiPost } from '@/lib/api'
import { authHeader } from '@/lib/auth'

export async function runJob(
  startUrl: string,
  fd: FormData,
  onStatus?: (status: string) => void,
  timeoutMs = 10 * 60 * 1000,
): Promise<Response> {
  const notifications = useNotifications()
  const deadline = Date.now() + timeoutMs

  try {
    const startResponse = await apiPost(startUrl, fd, {
      notifyOnError: false,
      timeout: Math.max(1, deadline - Date.now()),
    })
    const { job_id: jobId } = await startResponse.json() as { job_id?: string }
    if (!jobId) throw new Error('Der Server hat keine gültige Job-ID zurückgegeben.')

    for (;;) {
      if (Date.now() > deadline) {
        throw new Error('Die Verarbeitung hat das Zeitlimit überschritten.')
      }

      const status = await apiGetJson<{ status: string; error: string | null }>(
        `/api/pdf-extras/jobs/${encodeURIComponent(jobId)}`,
      )
      onStatus?.(status.status)

      if (status.status === 'error') {
        throw new Error(status.error || 'Die Verarbeitung ist fehlgeschlagen.')
      }
      if (status.status === 'done') break

      await new Promise<void>((resolve) => globalThis.setTimeout(resolve, 1500))
    }

    const remaining = deadline - Date.now()
    if (remaining <= 0) throw new Error('Die Verarbeitung hat das Zeitlimit überschritten.')

    const controller = new AbortController()
    const timer = globalThis.setTimeout(() => controller.abort(), remaining)
    try {
      const result = await fetch(
        `/api/pdf-extras/jobs/${encodeURIComponent(jobId)}/result`,
        { headers: authHeader(), signal: controller.signal },
      )
      if (!result.ok) {
        throw new Error(`Das Ergebnis konnte nicht abgeholt werden (${result.status}).`)
      }
      return result
    } finally {
      globalThis.clearTimeout(timer)
    }
  } catch (error: unknown) {
    notifications.error(
      'Verarbeitung fehlgeschlagen',
      notifications.errorFromUnknown(error),
    )
    throw error
  }
}
