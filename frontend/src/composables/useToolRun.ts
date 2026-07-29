/** Gemeinsames Ablaufmuster der einfachen Werkzeug-Kacheln. */

import { ref } from 'vue'
import { apiPost, downloadBlob } from '@/lib/api'

export function useToolRun() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const done = ref(false)

  async function run(url: string, fd: FormData, filename: string): Promise<Response | null> {
    loading.value = true
    error.value = null
    done.value = false
    try {
      const resp = await apiPost(url, fd)
      await downloadBlob(resp, filename)
      done.value = true
      return resp
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
      return null
    } finally {
      loading.value = false
    }
  }

  return { loading, error, done, run }
}
