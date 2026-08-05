/**
 * Ergebnisse der aktuellen Sitzung – ausschließlich im Browser-RAM.
 *
 * Blobs können sehr groß sein. Deshalb gelten dieselbe Gesamtgrenze wie für
 * Uploads und zusätzlich höchstens 20 Einträge. Älteste Ergebnisse werden
 * kontrolliert aus der Liste entfernt; der unmittelbare Dateidownload bleibt
 * davon unberührt.
 */

import { computed, ref } from 'vue'
import { currentTotalLimit } from '@/lib/fileValidation'

export interface SessionResult {
  id: number
  name: string
  blob: Blob
  createdAt: Date
}

export interface AddResultOutcome {
  stored: boolean
  removed: SessionResult[]
}

const MAX_RESULTS = 20
let nextId = 1
export const results = ref<SessionResult[]>([])

function currentSize(): number {
  return results.value.reduce((sum, result) => sum + result.blob.size, 0)
}

export function addResult(name: string, blob: Blob): AddResultOutcome {
  const removed: SessionResult[] = []
  const byteLimit = currentTotalLimit()
  if (blob.size > byteLimit) return { stored: false, removed }

  while (
    results.value.length >= MAX_RESULTS
    || (results.value.length > 0 && currentSize() + blob.size > byteLimit)
  ) {
    const oldest = results.value.shift()
    if (oldest) removed.push(oldest)
  }

  results.value.push({ id: nextId++, name, blob, createdAt: new Date() })
  return { stored: true, removed }
}

export function removeResult(id: number): void {
  results.value = results.value.filter((result) => result.id !== id)
}

export function clearResults(): void {
  results.value = []
}

export const totalSize = computed(() =>
  results.value.reduce((sum, result) => sum + result.blob.size, 0),
)

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1).replace('.', ',')} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`
}
