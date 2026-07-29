<template>
  <footer class="mt-12 border-t border-gray-200 dark:border-gray-700 py-6">
    <div class="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-gray-500 dark:text-gray-400">
      <p>Kostenlos &amp; ohne Datenspeicherung — Verarbeitung nur im Arbeitsspeicher.</p>
      <nav class="flex gap-4">
        <RouterLink to="/impressum" class="hover:text-gray-900 dark:hover:text-white">Impressum</RouterLink>
        <RouterLink to="/datenschutz" class="hover:text-gray-900 dark:hover:text-white">Datenschutz</RouterLink>
      </nav>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
