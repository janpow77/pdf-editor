/**
 * Client-seitiger ZIP-Download aller Sitzungs-Ergebnisse via JSZip.
 * Läuft komplett im Browser — der Server sieht die Dateien dafür nicht erneut.
 */

import JSZip from 'jszip'

import type { SessionResult } from '@/lib/results'

export async function downloadResultsAsZip(items: SessionResult[]): Promise<void> {
  const zip = new JSZip()
  const seen = new Map<string, number>()
  for (const item of items) {
    // Namenskollisionen entschärfen: datei.pdf, datei (2).pdf, ...
    const count = (seen.get(item.name) ?? 0) + 1
    seen.set(item.name, count)
    const name =
      count === 1
        ? item.name
        : item.name.replace(/(\.[^.]+)?$/, (ext) => ` (${count})${ext}`)
    zip.file(name, item.blob)
  }
  const blob = await zip.generateAsync({ type: 'blob' })
  const objectUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objectUrl
  a.download = 'pdf-editor-ergebnisse.zip'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(objectUrl)
}
