/**
 * Async-Job-Helfer: startet eine Verarbeitung, pollt ihren Status und liefert
 * anschließend das Ergebnis. Ein optionales Signal beendet Start, Polling,
 * Wartephasen und Ergebnisabruf gemeinsam.
 */

import { useNotifications } from '@/composables/useNotifications'
import { apiGetJson, apiPost } from '@/lib/api'
import { authHeader } from '@/lib/auth'

interface JobStatus { status: string; error: string | null }
const ACTIVE_STATUSES = new Set(['pending', 'queued', 'running', 'processing'])

function abortError(message = 'Die Verarbeitung wurde abgebrochen.'): Error {
  const error = new Error(message)
  error.name = 'AbortError'
  return error
}

function wait(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(signal.reason ?? abortError())
  return new Promise((resolve, reject) => {
    const timer = globalThis.setTimeout(finish, milliseconds)
    function finish(): void { signal?.removeEventListener('abort', cancel); resolve() }
    function cancel(): void { globalThis.clearTimeout(timer); signal?.removeEventListener('abort', cancel); reject(signal?.reason ?? abortError()) }
    signal?.addEventListener('abort', cancel, { once: true })
  })
}

export async function runJob(
  startUrl: string,
  formData: FormData,
  onStatus?: (status: string) => void,
  timeoutMs = 10 * 60 * 1000,
  signal?: AbortSignal,
): Promise<Response> {
  const notifications = useNotifications()
  const deadline = Date.now() + timeoutMs

  try {
    const startResp = await apiPost(startUrl, formData, {
      notifyOnError: false,
      signal,
      timeout: Math.max(1, deadline - Date.now()),
    })
    const payload = await startResp.json() as { job_id?: unknown }
    const jobId = typeof payload.job_id === 'string' ? payload.job_id.trim() : ''
    if (!jobId) throw new Error('Der Server hat keine gültige Job-ID zurückgegeben.')

    for (;;) {
      if (signal?.aborted) throw signal.reason ?? abortError()
      const remaining = deadline - Date.now()
      if (remaining <= 0) throw new Error('Die Verarbeitung hat das Zeitlimit überschritten.')

      const status = await apiGetJson<JobStatus>(
        `/api/pdf-extras/jobs/${encodeURIComponent(jobId)}`,
        { signal, timeout: remaining, notifyOnError: false },
      )
      onStatus?.(status.status)

      if (status.status === 'error') throw new Error(status.error || 'Die Verarbeitung ist fehlgeschlagen.')
      if (status.status === 'done') break
      if (!ACTIVE_STATUSES.has(status.status)) throw new Error(`Der Server meldet einen unbekannten Job-Status: ${status.status}.`)
      await wait(1500, signal)
    }

    const remaining = deadline - Date.now()
    if (remaining <= 0) throw new Error('Die Verarbeitung hat das Zeitlimit überschritten.')

    const resultController = new AbortController()
    const abortFromExternal = () => resultController.abort(signal?.reason)
    if (signal?.aborted) abortFromExternal()
    else signal?.addEventListener('abort', abortFromExternal, { once: true })
    const timer = globalThis.setTimeout(() => resultController.abort(abortError('Das Ergebnis konnte nicht rechtzeitig abgeholt werden.')), remaining)

    try {
      const result = await fetch(
        `/api/pdf-extras/jobs/${encodeURIComponent(jobId)}/result`,
        { headers: authHeader(), signal: resultController.signal },
      )
      if (!result.ok) {
        const body = await result.json().catch(() => ({ detail: '' })) as { detail?: unknown }
        const detail = typeof body.detail === 'string' && body.detail.trim() ? body.detail : `Status ${result.status}`
        throw new Error(`Das Ergebnis konnte nicht abgeholt werden: ${detail}`)
      }
      return result
    } finally {
      globalThis.clearTimeout(timer)
      signal?.removeEventListener('abort', abortFromExternal)
    }
  } catch (error: unknown) {
    // Ein bewusster Dokumentwechsel/Unmount bleibt still; echte Fehler werden
    // genau einmal zentral gemeldet.
    if (!signal?.aborted) {
      notifications.error('Verarbeitung fehlgeschlagen', notifications.errorFromUnknown(error))
    }
    throw error
  }
}
