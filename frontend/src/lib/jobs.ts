/** Async-Job-Helfer: startet einen Verarbeitungs-Job und pollt bis zum Ergebnis. */

import { apiGetJson, apiPost } from '@/lib/api'

export async function runJob(
  startUrl: string,
  fd: FormData,
  onStatus?: (status: string) => void,
  timeoutMs = 10 * 60 * 1000,
): Promise<Response> {
  const startResp = await apiPost(startUrl, fd)
  const { job_id: jobId } = await startResp.json()

  const deadline = Date.now() + timeoutMs
  for (;;) {
    if (Date.now() > deadline) throw new Error('Zeitlimit überschritten')
    const status = await apiGetJson<{ status: string; error: string | null }>(
      `/api/pdf-extras/jobs/${jobId}`,
    )
    onStatus?.(status.status)
    if (status.status === 'error') throw new Error(status.error || 'Verarbeitung fehlgeschlagen')
    if (status.status === 'done') break
    await new Promise((r) => setTimeout(r, 1500))
  }

  const result = await fetch(`/api/pdf-extras/jobs/${jobId}/result`)
  if (!result.ok) throw new Error('Ergebnis konnte nicht abgeholt werden')
  return result
}
