<template>
  <footer class="mt-10 border-t border-black/5 bg-white/40 py-6 backdrop-blur-xl dark:border-white/10 dark:bg-black/10">
    <div class="mx-auto max-w-[1600px] space-y-4 px-4 sm:px-6">
      <div class="flex flex-col gap-3 text-sm text-gray-600 sm:flex-row sm:items-center sm:justify-between dark:text-gray-300">
        <p class="font-medium">Kostenlos – Verarbeitung nur im Arbeitsspeicher.</p>
        <nav class="flex flex-wrap gap-x-4 gap-y-2" aria-label="Rechtliche Informationen">
          <RouterLink to="/impressum" class="rounded-md hover:text-gray-950 dark:hover:text-white">Impressum</RouterLink>
          <RouterLink to="/datenschutz" class="rounded-md hover:text-gray-950 dark:hover:text-white">Datenschutz</RouterLink>
          <RouterLink to="/barrierefreiheit" class="rounded-md hover:text-gray-950 dark:hover:text-white">Barrierefreiheit</RouterLink>
          <RouterLink to="/lizenzen" class="rounded-md hover:text-gray-950 dark:hover:text-white">Open Source</RouterLink>
        </nav>
      </div>

      <!--
        Die früher großflächigen Hinweise sind als kompakte Akkordeons weiterhin
        unmittelbar erreichbar, belegen in den Werkzeugen aber keinen wertvollen
        Arbeitsraum mehr. Native details-Elemente bleiben ohne JavaScript
        tastaturbedienbar und werden von Screenreadern korrekt angekündigt.
      -->
      <div class="grid gap-2 text-sm sm:grid-cols-2">
        <details class="rounded-2xl bg-white/60 px-4 py-2.5 shadow-sm ring-1 ring-black/5 dark:bg-white/5 dark:ring-white/10">
          <summary class="cursor-pointer font-semibold text-gray-800 dark:text-gray-100">Datenschutz & Verarbeitung</summary>
          <p class="mt-2 leading-6 text-gray-600 dark:text-gray-300">
            Dateien werden nur für die gewählte Verarbeitung übertragen und nicht dauerhaft gespeichert.
            Einzelheiten stehen in der <RouterLink to="/datenschutz" class="font-semibold text-primary-600 dark:text-primary-400">Datenschutzerklärung</RouterLink>.
          </p>
        </details>
        <details class="rounded-2xl bg-white/60 px-4 py-2.5 shadow-sm ring-1 ring-black/5 dark:bg-white/5 dark:ring-white/10">
          <summary class="cursor-pointer font-semibold text-gray-800 dark:text-gray-100">Offener Quelltext</summary>
          <p class="mt-2 leading-6 text-gray-600 dark:text-gray-300">
            Die Anwendung verwendet freie Komponenten. Lizenzen und der erreichbare Quelltext sind unter
            <RouterLink to="/lizenzen" class="font-semibold text-primary-600 dark:text-primary-400">Open Source</RouterLink> dokumentiert.
          </p>
        </details>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
