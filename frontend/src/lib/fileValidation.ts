/**
 * Gemeinsame Validierung für PDF-Uploads.
 *
 * Die Prüfung erfolgt vor dem Netzwerkaufruf. Dadurch erhalten Nutzende sofort
 * eine verständliche Rückmeldung, statt erst nach einem fehlgeschlagenen
 * Server-Upload. Neben Endung und Größe wird auch die PDF-Signatur `%PDF-`
 * geprüft; eine lediglich umbenannte Fremddatei wird damit zuverlässig erkannt.
 */
import { isAuthenticated } from '@/lib/auth'

const MEBIBYTE = 1024 * 1024
const ANONYMOUS_FILE_LIMIT = 50 * MEBIBYTE
const AUTHENTICATED_FILE_LIMIT = 100 * MEBIBYTE
const ANONYMOUS_TOTAL_LIMIT = 200 * MEBIBYTE
const AUTHENTICATED_TOTAL_LIMIT = 400 * MEBIBYTE

export interface FileValidationResult {
  valid: boolean
  message?: string
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < MEBIBYTE) return `${(bytes / 1024).toFixed(1).replace('.', ',')} KB`
  return `${(bytes / MEBIBYTE).toFixed(1).replace('.', ',')} MB`
}

export function currentFileLimit(): number {
  return isAuthenticated.value ? AUTHENTICATED_FILE_LIMIT : ANONYMOUS_FILE_LIMIT
}

export function currentTotalLimit(): number {
  return isAuthenticated.value ? AUTHENTICATED_TOTAL_LIMIT : ANONYMOUS_TOTAL_LIMIT
}

export async function validatePdfFile(file: File): Promise<FileValidationResult> {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    return { valid: false, message: 'Bitte wählen Sie eine Datei mit der Endung .pdf aus.' }
  }

  const limit = currentFileLimit()
  if (file.size > limit) {
    return {
      valid: false,
      message: `Die Datei ist ${formatFileSize(file.size)} groß. Zulässig sind maximal ${formatFileSize(limit)}.`,
    }
  }

  if (file.size < 5) {
    return { valid: false, message: 'Die Datei ist leer oder unvollständig.' }
  }

  try {
    const signature = new TextDecoder('ascii').decode(await file.slice(0, 5).arrayBuffer())
    if (signature !== '%PDF-') {
      return {
        valid: false,
        message: 'Die Datei besitzt keine gültige PDF-Signatur und ist möglicherweise beschädigt.',
      }
    }
  } catch {
    return { valid: false, message: 'Die Datei konnte im Browser nicht gelesen werden.' }
  }

  return { valid: true }
}

export function validateTotalFileSize(files: File[]): FileValidationResult {
  const total = files.reduce((sum, file) => sum + file.size, 0)
  const limit = currentTotalLimit()
  if (total > limit) {
    return {
      valid: false,
      message: `Die Gesamtgröße beträgt ${formatFileSize(total)}. Zulässig sind maximal ${formatFileSize(limit)}.`,
    }
  }
  return { valid: true }
}
