<template>
  <div
    class="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg
           text-sm text-emerald-900 dark:text-emerald-200 flex items-start gap-3"
  >
    <span aria-hidden="true" class="text-lg leading-none mt-0.5">🔒</span>
    <p>
      <strong>Kostenlos &amp; ohne Datenspeicherung</strong> — Ihre Dateien werden
      ausschließlich für die Dauer der Verarbeitung im Arbeitsspeicher gehalten und
      danach sofort verworfen.
      <template v-if="restrictedCount">
        Die meisten Werkzeuge sind ohne Registrierung nutzbar;
        {{ restrictedCount === 1 ? 'ein Werkzeug ist' : `${restrictedCount} Werkzeuge sind` }}
        mit 🔒 gekennzeichnet und stehen nur angemeldeten Nutzern offen.
      </template>
      <template v-else>Keine Registrierung erforderlich.</template>
      Mit einem optionalen Gratis-Konto gelten höhere Limits (100 MB) und gespeicherte
      Einstellungen — Ihre Dateien werden auch damit nie gespeichert.
      <RouterLink to="/datenschutz" class="underline hover:no-underline">Mehr erfahren</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { isAuthenticated } from '@/lib/auth'
import { getHealth } from '@/lib/health'

// Nur für anonyme Besucher relevant: wie viele Werkzeuge hat der Betreiber
// auf angemeldete Nutzer beschränkt?
const restrictedCount = ref(0)

onMounted(async () => {
  if (isAuthenticated.value) return
  try {
    const health = await getHealth()
    restrictedCount.value = (health.login_required_tools ?? []).length
  } catch {
    restrictedCount.value = 0
  }
})
</script>
