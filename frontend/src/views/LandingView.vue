<template>
  <div
    class="mx-auto w-full px-4 transition-all duration-300 sm:px-6"
    :class="isWorkspaceActive ? 'max-w-[1800px] py-3' : 'max-w-[1600px] py-8 sm:py-12'"
  >
    <!--
      Der großzügige Hero ist ausschließlich auf der Startseite sichtbar. Beim
      Öffnen eines Werkzeugs verschwindet er vollständig, damit der verfügbare
      Bildschirm dem Dokument und den Bedienelementen gehört.
    -->
    <header v-if="!isWorkspaceActive" class="mx-auto mb-10 max-w-4xl text-center sm:mb-12">
      <!-- primary-700 statt 600: 14-px-Text auf #f5f5f7 braucht 4,5:1 (BITV), 600 erreicht nur 4,31. -->
      <p class="mb-3 text-sm font-semibold uppercase tracking-[0.16em] text-primary-700 dark:text-primary-400">
        Lokal. Schnell. Vertraulich.
      </p>
      <h1 class="text-balance text-4xl font-semibold tracking-[-0.045em] text-gray-950 sm:text-6xl dark:text-white">
        PDF-Werkzeuge für konzentriertes Arbeiten
      </h1>
      <p class="mx-auto mt-5 max-w-2xl text-lg leading-8 text-gray-600 dark:text-gray-300">
        Bearbeiten, konvertieren und signieren – direkt im Browser, ohne dauerhafte Datenspeicherung.
      </p>

      <!--
        Die Suche sitzt wie Spotlight zentral im Hero. Der deutliche Rahmen im
        Ruhezustand und der zusätzliche Fokus-Ring erfüllen die Anforderungen
        an Tastaturnavigation und nicht-textuelle Kontraste.
      -->
      <label class="relative mx-auto mt-8 block max-w-2xl text-left">
        <span class="sr-only">PDF-Werkzeuge durchsuchen</span>
        <svg
          class="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-500 dark:text-gray-400"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" stroke-width="2" />
          <path d="m20 20-3.4-3.4" stroke-width="2" stroke-linecap="round" />
        </svg>
        <input
          v-model="searchQuery"
          type="search"
          autocomplete="off"
          class="w-full rounded-[1.35rem] bg-white/[0.88] py-4 pl-14 pr-12 text-base font-medium text-gray-950
                 shadow-apple ring-1 ring-gray-400/70 backdrop-blur-2xl transition
                 placeholder:text-gray-500 focus:ring-2 focus:ring-primary-500
                 dark:bg-white/10 dark:text-white dark:ring-gray-500 dark:placeholder:text-gray-400"
          placeholder="Werkzeug suchen, z. B. Formular, Teilen oder OCR"
        />
        <button
          v-if="searchQuery"
          type="button"
          class="absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-full
                 text-gray-500 transition hover:bg-black/5 hover:text-gray-900 dark:text-gray-400
                 dark:hover:bg-white/10 dark:hover:text-white"
          aria-label="Suche zurücksetzen"
          @click="searchQuery = ''"
        >×</button>
      </label>
    </header>

    <ResultsPanel v-if="!isWorkspaceActive" class="mb-8" />
    <!-- Der Schlüssel verwirft beim globalen Schließen auch lokalen Tool-State. -->
    <ToolGrid :key="workspaceRevision" :search-query="searchQuery" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ResultsPanel from '@/components/ResultsPanel.vue'
import ToolGrid from '@/components/ToolGrid.vue'
import { useWorkspace } from '@/composables/useWorkspace'

const searchQuery = ref('')
const { isWorkspaceActive, workspaceRevision } = useWorkspace()
</script>
