<template>
  <div class="max-w-6xl mx-auto px-4 py-8 space-y-6">
    <header class="text-center space-y-3 py-6">
      <h1 class="text-4xl sm:text-5xl font-semibold tracking-tight text-gray-900 dark:text-white">
        PDF-Werkzeuge
      </h1>
      <p class="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
        Bearbeiten, konvertieren, signieren — direkt im Browser.
        Kostenlos und ohne Datenspeicherung.
      </p>
    </header>

    <NoticeBanner />
    <ResultsPanel />
    <ToolGrid />

    <!-- Offenlegung der Bauteile. Steht bewusst auf der Startseite und nicht
         nur im Fußbereich: Die AGPL verlangt, dass Nutzende des Dienstes vom
         Quelltext erfahren — eine Angabe, die man erst suchen muss, erfüllt
         das nur formal. -->
    <OpenSourceNotice />
  </div>
</template>

<script setup lang="ts">
import NoticeBanner from '@/components/NoticeBanner.vue'
import OpenSourceNotice from '@/components/OpenSourceNotice.vue'
import ResultsPanel from '@/components/ResultsPanel.vue'
import ToolGrid from '@/components/ToolGrid.vue'
</script>
