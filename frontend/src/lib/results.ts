/**
 * Sitzungs-Ergebnisse — ausschließlich im Browser-Speicher (RAM).
 *
 * Jedes Werkzeug-Ergebnis wird hier vorgemerkt, damit Nutzer:innen alle
 * Dateien gesammelt als ZIP herunterladen oder per Mail versenden können.
 * Nichts davon verlässt den Browser, außer beim explizit angestoßenen
 * Mailversand; ein Reload leert die Liste.
 */

import { computed, ref } from 'vue'

export interface SessionResult {
  id: number
  name: string
  blob: Blob
  createdAt: Date
}

let nextId = 1
export const results = ref<SessionResult[]>([])

export function addResult(name: string, blob: Blob): void {
  results.value.push({ id: nextId++, name, blob, createdAt: new Date() })
}

export function removeResult(id: number): void {
  results.value = results.value.filter((r) => r.id !== id)
}

export function clearResults(): void {
  results.value = []
}

export const totalSize = computed(() =>
  results.value.reduce((sum, r) => sum + r.blob.size, 0),
)

export function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1).replace('.', ',')} MB`
}
