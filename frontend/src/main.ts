import { createApp } from 'vue'

import App from '@/App.vue'
import { initializeTheme } from '@/composables/useTheme'
import { router } from '@/router'
import '@/style.css'
import '@/apple-utilities.css'

// Das Theme wird vor dem Mount gesetzt. So entsteht beim Laden kein kurzer
// heller Blitz, wenn die gespeicherte oder systemweite Auswahl dunkel ist.
initializeTheme()

createApp(App).use(router).mount('#app')
