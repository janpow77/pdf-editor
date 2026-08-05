import { createApp } from 'vue'

import App from '@/App.vue'
import { initializeTheme } from '@/composables/useTheme'
import { router } from '@/router'
import '@/style.css'

// Das Theme wird vor dem Mount gesetzt. So entsteht beim Laden kein kurzer
// heller Blitz, wenn die gespeicherte oder systemweite Auswahl dunkel ist.
initializeTheme()

// Nach einem Deploy tragen die nachladbaren Bausteine neue Dateinamen — ein
// offener Alt-Tab läuft dann bei der ersten Werkzeug-Öffnung in einen
// Ladefehler und bliebe stumm leer. Einmalig automatisch neu laden holt die
// frische Version; schlägt auch das fehl, bleibt eine sichtbare Meldung.
window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  const RELOAD_KEY = 'pdfapp_chunk_reload'
  let alreadyReloaded = false
  try {
    alreadyReloaded = sessionStorage.getItem(RELOAD_KEY) === '1'
    sessionStorage.setItem(RELOAD_KEY, '1')
  } catch { /* Ohne Speicher lieber einmal mehr neu laden als leer bleiben. */ }
  if (!alreadyReloaded) {
    window.location.reload()
    return
  }
  void import('@/composables/useNotifications').then(({ useNotifications }) => {
    useNotifications().error(
      'Neue Version verfügbar',
      'Die Seite konnte einen Baustein nicht laden. Bitte mit Strg+Shift+R neu laden.',
    )
  })
})

createApp(App).use(router).mount('#app')

// Erfolgreicher Start: Reload-Wächter zurücksetzen, damit der nächste Deploy
// wieder automatisch neu laden darf.
try { sessionStorage.removeItem('pdfapp_chunk_reload') } catch { /* unkritisch */ }
