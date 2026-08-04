/**
 * Zentrale Theme-Steuerung für die gesamte Anwendung.
 *
 * Die Klasse `dark` wird bewusst am Wurzelelement gesetzt. Dadurch kann eine
 * manuelle Entscheidung die Betriebssystem-Präferenz zuverlässig übersteuern.
 * Ohne gespeicherte Auswahl folgt die Anwendung weiterhin automatisch
 * `prefers-color-scheme` und reagiert auch auf spätere Systemänderungen.
 */
import { computed, readonly, ref } from 'vue'

export type ThemePreference = 'system' | 'light' | 'dark'

const STORAGE_KEY = 'pdfapp_theme_preference'
const preference = ref<ThemePreference>('system')
const systemIsDark = ref(false)
let initialized = false
let mediaQuery: MediaQueryList | null = null

const isDark = computed(() =>
  preference.value === 'system' ? systemIsDark.value : preference.value === 'dark',
)

function applyTheme(): void {
  document.documentElement.classList.toggle('dark', isDark.value)
  document.documentElement.style.colorScheme = isDark.value ? 'dark' : 'light'
}

function onSystemThemeChanged(event: MediaQueryListEvent): void {
  systemIsDark.value = event.matches
  if (preference.value === 'system') applyTheme()
}

/** Browser können localStorage in besonders strikten Datenschutzmodi sperren. */
function readStoredPreference(): ThemePreference | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    return stored === 'light' || stored === 'dark' || stored === 'system' ? stored : null
  } catch {
    return null
  }
}

function storePreference(next: ThemePreference): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // Die aktuelle Auswahl bleibt für die Sitzung wirksam, auch ohne Persistenz.
  }
}

export function initializeTheme(): void {
  if (initialized || typeof window === 'undefined') return
  initialized = true

  const stored = readStoredPreference()
  if (stored) preference.value = stored

  mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  systemIsDark.value = mediaQuery.matches
  mediaQuery.addEventListener('change', onSystemThemeChanged)
  applyTheme()
}

export function useTheme() {
  function setPreference(next: ThemePreference): void {
    preference.value = next
    storePreference(next)
    applyTheme()
  }

  /**
   * Der kompakte Header-Schalter wechselt direkt zwischen Hell und Dunkel.
   * Die explizite Wahl wird gespeichert; die Systemeinstellung bleibt über
   * `setPreference('system')` weiterhin als Architektur-Option verfügbar.
   */
  function toggleTheme(): void {
    setPreference(isDark.value ? 'light' : 'dark')
  }

  return {
    preference: readonly(preference),
    isDark,
    setPreference,
    toggleTheme,
  }
}
