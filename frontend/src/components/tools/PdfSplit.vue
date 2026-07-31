<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF teilen</h2>
    </div>

    <!-- Upload -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="file ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".pdf" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <p class="text-gray-500 dark:text-gray-400 mb-2">PDF hierher ziehen oder</p>
        <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Datei auswählen</button>
      </div>
      <div v-else>
        <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
        <p v-if="pageCount" class="text-sm text-gray-500">{{ pageCount }} Seiten</p>
        <button class="mt-2 text-sm text-red-500 hover:text-red-700" @click="file = null; pageCount = 0">Entfernen</button>
      </div>
    </div>

    <!-- Options -->
    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
      <div class="flex gap-4">
        <label class="flex items-center gap-2 text-sm">
          <input v-model="mode" type="radio" value="ranges" class="text-primary-600" />
          Seitenbereiche
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input v-model="mode" type="radio" value="every_n" class="text-primary-600" />
          Alle N Seiten
        </label>
      </div>

      <div v-if="mode === 'ranges'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Bereiche (getrennt durch ;)
        </label>
        <input
          v-model="ranges"
          type="text"
          class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
          placeholder="z.B. 1-3;4-6;7-10"
        />
        <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">Jeder Bereich wird eine separate Datei. Gesamt: {{ pageCount }} Seiten</p>
      </div>

      <div v-if="mode === 'every_n'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Alle N Seiten teilen</label>
        <input
          v-model.number="everyN"
          type="number"
          min="1"
          :max="pageCount"
          class="w-32 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
        />
        <p class="text-xs text-gray-600 dark:text-gray-400 mt-1">Ergibt {{ Math.ceil(pageCount / everyN) }} Teile</p>
      </div>
    </div>

    <!-- Thumbnails -->
    <PageThumbnailGrid
      v-if="Object.keys(thumbnails).length > 0"
      :thumbnails="thumbnails"
      :loading="loadingThumbs"
    />

    <!-- Action -->
    <button
      v-if="file"
      :disabled="loading || (!ranges && mode === 'ranges')"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doSplit"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Teile...' : 'PDF teilen' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'
import PageThumbnailGrid from './PageThumbnailGrid.vue'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, splitPdf, getThumbnails } = usePdfTools()
const file = ref<File | null>(null)
const pageCount = ref(0)
const mode = ref('ranges')
const ranges = ref('')
const everyN = ref(1)
const thumbnails = ref<Record<string, string>>({})
const loadingThumbs = ref(false)

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) setFile(input.files[0])
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) setFile(f)
}

async function setFile(f: File) {
  file.value = f
  loadingThumbs.value = true
  try {
    const data = await getThumbnails(f)
    thumbnails.value = data.thumbnails
    pageCount.value = data.count
  } catch { /* ignore */ }
  loadingThumbs.value = false
}

async function doSplit() {
  if (!file.value) return
  await withLoading(() => splitPdf(file.value!, mode.value, ranges.value || undefined, everyN.value))
}
</script>
