/**
 * Fehlertoleranter Adapter für kleine Browser-Präferenzen und Auth-Tokens.
 *
 * `localStorage` kann in Privatmodi, eingebetteten Browsern oder automatisierten
 * Tests vollständig gesperrt sein und dann bereits beim Lesen eine DOMException
 * werfen. Der Adapter kapselt deshalb jeden Zugriff und verwendet für die
 * aktuelle Sitzung einen In-Memory-Fallback. Fachmodule müssen keine eigenen
 * try/catch-Varianten mehr pflegen und bleiben auch ohne Persistenz bedienbar.
 */
const memoryFallback = new Map<string, string>()

function browserStorage(): Storage | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function readStoredValue(key: string): string | null {
  const storage = browserStorage()
  if (storage) {
    try {
      const value = storage.getItem(key)
      if (value !== null) memoryFallback.set(key, value)
      return value
    } catch {
      // Der In-Memory-Wert hält die aktuelle Sitzung funktionsfähig.
    }
  }
  return memoryFallback.get(key) ?? null
}

export function writeStoredValue(key: string, value: string): void {
  memoryFallback.set(key, value)
  const storage = browserStorage()
  if (!storage) return
  try {
    storage.setItem(key, value)
  } catch {
    // Persistenz ist Komfort; der Sitzungszustand bleibt im Fallback erhalten.
  }
}

export function removeStoredValue(key: string): void {
  memoryFallback.delete(key)
  const storage = browserStorage()
  if (!storage) return
  try {
    storage.removeItem(key)
  } catch {
    // Ein gesperrter Speicher darf Logout oder Reset nicht verhindern.
  }
}
