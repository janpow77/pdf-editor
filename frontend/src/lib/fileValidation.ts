/**
 * Gemeinsame Validierung für Datei- und PDF-Uploads.
 *
 * Die Prüfung erfolgt vor dem Netzwerkaufruf. Die zunächst verwendeten Defaults
 * entsprechen der Standardkonfiguration des Backends; `/api/health` ersetzt sie
 * anschließend durch die im jeweiligen Deployment tatsächlich aktiven Werte.
 */
import { isAuthenticated } from '@/lib/auth'

const MEBIBYTE = 1024 * 1024

export interface UploadLimitTier {
  max_file: number
  max_total: number
}

export interface UploadLimitConfiguration {
  anonymous: UploadLimitTier
  authenticated: UploadLimitTier
}

const DEFAULT_LIMITS: UploadLimitConfiguration = {
  anonymous: { max_file: 50 * MEBIBYTE, max_total: 200 * MEBIBYTE },
  authenticated: { max_file: 100 * MEBIBYTE, max_total: 400 * MEBIBYTE },
}

let configuredLimits: UploadLimitConfiguration = structuredClone(DEFAULT_LIMITS)

export interface FileValidationResult {
  valid: boolean
  message?: string
}

function positiveLimit(value: unknown, fallback: number): number {
  const numeric = Number(value)
  return Number.isFinite(numeric) && numeric > 0 ? Math.floor(numeric) : fallback
}

/** Übernimmt ausschließlich plausible, positive Grenzwerte vom Health-Endpunkt. */
export function configureUploadLimits(value: UploadLimitConfiguration): void {
  configuredLimits = {
    anonymous: {
      max_file: positiveLimit(value.anonymous?.max_file, DEFAULT_LIMITS.anonymous.max_file),
      max_total: positiveLimit(value.anonymous?.max_total, DEFAULT_LIMITS.anonymous.max_total),
    },
    authenticated: {
      max_file: positiveLimit(value.authenticated?.max_file, DEFAULT_LIMITS.authenticated.max_file),
      max_total: positiveLimit(value.authenticated?.max_total, DEFAULT_LIMITS.authenticated.max_total),
    },
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < MEBIBYTE) return `${(bytes / 1024).toFixed(1).replace('.', ',')} KB`
  return `${(bytes / MEBIBYTE).toFixed(1).replace('.', ',')} MB`
}

function activeTier(): UploadLimitTier {
  return isAuthenticated.value ? configuredLimits.authenticated : configuredLimits.anonymous
}

export function currentFileLimit(): number {
  return activeTier().max_file
}

export function currentTotalLimit(): number {
  return activeTier().max_total
}

function hasPdfSignature(bytes: Uint8Array): boolean {
  const signature = [0x25, 0x50, 0x44, 0x46, 0x2d] // %PDF-
  outer: for (let offset = 0; offset <= bytes.length - signature.length; offset += 1) {
    for (let index = 0; index < signature.length; index += 1) {
      if (bytes[offset + index] !== signature[index]) continue outer
    }
    return true
  }
  return false
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
    /*
     * Übliche PDFs beginnen direkt mit `%PDF-`. Einige zulässige Dateien
     * enthalten wenige Präfix-Bytes. Die bytegenaue Suche in den ersten 1.024
     * Bytes ist deshalb robuster als ein Textdecoder und akzeptiert keine bloß
     * umbenannten Fremdformate.
     */
    const bytes = new Uint8Array(await file.slice(0, 1024).arrayBuffer())
    if (!hasPdfSignature(bytes)) {
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
