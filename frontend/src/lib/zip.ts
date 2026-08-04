/** Client-seitiger ZIP-Download aller Sitzungsergebnisse. */

import JSZip from 'jszip'
import type { SessionResult } from '@/lib/results'

function safeName(value: string): string {
  return value.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').trim() || 'ergebnis.bin'
}

export async function downloadResultsAsZip(items: SessionResult[]): Promise<void> {
  if (!items.length) throw new Error('Es sind keine Ergebnisse zum Packen vorhanden.')
  const zip = new JSZip()
  const seen = new Map<string, number>()

  for (const item of items) {
    const baseName = safeName(item.name)
    const count = (seen.get(baseName) ?? 0) + 1
    seen.set(baseName, count)
    const name = count === 1
      ? baseName
      : baseName.replace(/(\.[^.]+)?$/, (extension) => ` (${count})${extension}`)
    zip.file(name, item.blob)
  }

  const blob = await zip.generateAsync({ type: 'blob' })
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  try {
    anchor.href = objectUrl
    anchor.download = 'pdf-editor-ergebnisse.zip'
    document.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    URL.revokeObjectURL(objectUrl)
  }
}
