/*
 * Das Erscheinungsbild wird vor dem Laden des Vue-Bundles gesetzt. So
 * entsteht bei gespeichertem Dunkelmodus kein heller Zwischenzustand.
 * Gesperrter Browser-Speicher fällt sicher auf die Systempräferenz zurück.
 *
 * Eigene Datei statt Inline-Skript: die Content-Security-Policy erlaubt
 * bewusst nur script-src 'self' — Inline-Code würde geblockt.
 */
;(() => {
  let preference = 'system'
  try {
    const stored = window.localStorage.getItem('pdfapp_theme_preference')
    if (stored === 'light' || stored === 'dark' || stored === 'system') preference = stored
  } catch {
    // Die Systempräferenz bleibt auch ohne persistenten Speicher verfügbar.
  }
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = preference === 'dark' || (preference === 'system' && systemDark)
  document.documentElement.classList.toggle('dark', dark)
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light'
})()
