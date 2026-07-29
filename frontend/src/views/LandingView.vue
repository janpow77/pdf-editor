<template>
  <div class="max-w-6xl mx-auto px-4 py-8 space-y-6">
    <header class="text-center space-y-3 py-6">
      <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white">
        PDF-Werkzeuge — kostenlos &amp; ohne Datenspeicherung
      </h1>
      <p class="text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
        Zusammenführen, teilen, komprimieren, OCR, Word- und Excel-Tools — direkt im
        Browser starten, Ergebnis herunterladen, als ZIP bündeln oder per E-Mail senden.
      </p>
    </header>

    <NoticeBanner />
    <ResultsPanel />
    <ToolGrid />
  </div>
</template>

<script setup lang="ts">
import NoticeBanner from '@/components/NoticeBanner.vue'
import ResultsPanel from '@/components/ResultsPanel.vue'
import ToolGrid from '@/components/ToolGrid.vue'
</script>
