<template>
  <div
    class="p-4 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg
           text-sm text-emerald-900 dark:text-emerald-200 flex items-start gap-3"
  >
    <span aria-hidden="true" class="text-lg leading-none mt-0.5">🔒</span>
    <p>
      <strong>Kostenlos &amp; ohne Datenspeicherung</strong> — Ihre Dateien werden
      ausschließlich für die Dauer der Verarbeitung im Arbeitsspeicher gehalten und
      danach sofort verworfen. Keine Registrierung erforderlich.
      <RouterLink to="/datenschutz" class="underline hover:no-underline">Mehr erfahren</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
