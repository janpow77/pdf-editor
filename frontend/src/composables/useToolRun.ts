/**
 * Gemeinsames Ablaufmuster der einfachen Werkzeug-Komponenten.
 *
 * Ein Generationszähler und AbortController verhindern, dass eine Verarbeitung
 * nach Datei- oder Optionswechsel noch einen Download, Erfolgshinweis oder
 * Fehlerzustand für den inzwischen veralteten Arbeitsstand erzeugt.
 */

import { onBeforeUnmount, ref } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import { apiPost, downloadBlob } from '@/lib/api'

export function useToolRun() {
  const loading = ref(false)
  const error = ref<string | null>(null)
  const done = ref(false)
  const notifications = useNotifications()
  let generation = 0
  let controller: AbortController | null = null

  /** Eingabe hat sich geändert: laufenden Request abbrechen und Status leeren. */
  function reset(): void {
    generation += 1
    controller?.abort()
    controller = null
    loading.value = false
    error.value = null
    done.value = false
  }

  async function run(url: string, formData: FormData, filename: string): Promise<Response | null> {
    reset()
    const currentGeneration = generation
    const requestController = new AbortController()
    controller = requestController
    loading.value = true

    try {
      const response = await apiPost(url, formData, {
        signal: requestController.signal,
        notifyOnError: false,
      })
      if (currentGeneration !== generation || requestController.signal.aborted) return null
      await downloadBlob(response, filename)
      if (currentGeneration !== generation) return null
      done.value = true
      return response
    } catch (caught: unknown) {
      if (requestController.signal.aborted || currentGeneration !== generation) return null
      error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler'
      notifications.error('Verarbeitung fehlgeschlagen', error.value)
      return null
    } finally {
      if (controller === requestController) controller = null
      if (currentGeneration === generation) loading.value = false
    }
  }

  onBeforeUnmount(reset)
  return { loading, error, done, run, reset }
}
