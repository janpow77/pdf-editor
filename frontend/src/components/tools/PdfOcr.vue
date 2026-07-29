<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <button
        class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1"
        @click="$emit('back')"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Zurueck
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">OCR - Texterkennung</h2>
    </div>

    <!-- Description -->
    <div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Macht gescannte PDFs durchsuchbar. Der Text wird als unsichtbare Ebene ueber die Seiten gelegt,
      sodass Sie den Text kopieren und durchsuchen koennen.
    </div>

    <!-- Upload -->
    <div
      class="border-2 border-dashed rounded-xl p-8 text-center transition-colors"
      :class="[
        file
          ? 'border-green-500 bg-green-50 dark:bg-green-900/20'
          : dragOver
            ? 'border-primary-400 bg-primary-50 dark:bg-primary-900/10'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500',
      ]"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".pdf" class="hidden" @change="onFileSelect" />
      <div v-if="file" class="space-y-2">
        <div class="text-4xl">&#128196;</div>
        <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
        <p class="text-sm text-gray-500 dark:text-gray-400">{{ formatSize(file.size) }}</p>
        <button
          class="text-sm text-red-500 hover:text-red-700 hover:underline"
          @click="removeFile"
        >
          Entfernen
        </button>
      </div>
      <div v-else class="cursor-pointer space-y-2" @click="($refs.fileInput as HTMLInputElement).click()">
        <div class="text-4xl">&#128229;</div>
        <p class="text-gray-600 dark:text-gray-400">Gescannte PDF hierher ziehen</p>
        <p class="text-sm text-gray-400">oder klicken zum Auswaehlen</p>
      </div>
    </div>

    <!-- Language selection -->
    <div v-if="file && !result" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Sprache der Texterkennung</label>
      <div class="flex flex-wrap gap-4">
        <label
          v-for="lang in languages"
          :key="lang.value"
          class="flex items-center gap-2 cursor-pointer"
        >
          <input
            v-model="language"
            type="radio"
            :value="lang.value"
            class="w-4 h-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600"
          />
          <span class="text-sm text-gray-700 dark:text-gray-300">{{ lang.label }}</span>
        </label>
      </div>
    </div>

    <!-- Start button -->
    <button
      v-if="file && !loading && !result"
      class="w-full py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium transition-colors"
      @click="runOcr"
    >
      OCR starten
    </button>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-8 space-y-3">
      <svg class="animate-spin w-10 h-10 mx-auto text-primary-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <p class="text-gray-600 dark:text-gray-400 font-medium">OCR wird durchgefuehrt...</p>
      <p class="text-xs text-gray-400 dark:text-gray-500">
        Dies kann bei grossen Dokumenten einige Minuten dauern.
      </p>
    </div>

    <!-- Result -->
    <div v-if="result" class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-xl p-6 space-y-4">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 bg-green-100 dark:bg-green-800 rounded-full flex items-center justify-center text-xl">
          &#9989;
        </div>
        <div>
          <p class="font-bold text-green-800 dark:text-green-300">OCR erfolgreich!</p>
          <p class="text-sm text-green-600 dark:text-green-400">
            {{ result.pagesProcessed }} Seiten verarbeitet,
            {{ result.charsRecognized.toLocaleString('de-DE') }} Zeichen erkannt
          </p>
        </div>
      </div>

      <!-- Stats grid -->
      <div class="grid grid-cols-2 gap-4 pt-2">
        <div class="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
          <p class="text-xs text-gray-500 dark:text-gray-400">Seiten</p>
          <p class="text-lg font-bold text-gray-900 dark:text-white">{{ result.pagesProcessed }}</p>
        </div>
        <div class="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
          <p class="text-xs text-gray-500 dark:text-gray-400">Zeichen</p>
          <p class="text-lg font-bold text-gray-900 dark:text-white">
            {{ result.charsRecognized.toLocaleString('de-DE') }}
          </p>
        </div>
      </div>

      <button
        v-if="result.blobUrl"
        class="w-full py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium transition-colors"
        @click="downloadResult"
      >
        Durchsuchbare PDF herunterladen
      </button>

      <button
        class="w-full py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        @click="reset"
      >
        Neues Dokument
      </button>
    </div>

    <!-- Error -->
    <div v-if="error" class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg">
      <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      <button
        class="mt-2 text-xs text-red-500 hover:underline"
        @click="error = null"
      >
        Schliessen
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { runJob } from '@/lib/jobs'
import { prefDefault } from '@/lib/auth'

defineEmits<{ (e: 'back'): void }>()

// --- Constants ---

const API_BASE = '/api/pdf-editor'
const OCR_TIMEOUT = 10 * 60 * 1000 // 10 minutes for OCR

const languages = [
  { value: 'deu', label: 'Deutsch' },
  { value: 'eng', label: 'Englisch' },
  { value: 'deu+eng', label: 'Deutsch + Englisch' },
]

// --- State ---

const file = ref<File | null>(null)
const language = ref(prefDefault('ocr_language', 'deu'))
const loading = ref(false)
const error = ref<string | null>(null)
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const result = ref<{
  pagesProcessed: number
  charsRecognized: number
  blobUrl: string | null
  filename: string
} | null>(null)

// --- File handling ---

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    file.value = input.files[0]
    result.value = null
    error.value = null
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) {
    file.value = f
    result.value = null
    error.value = null
  }
}

function removeFile() {
  file.value = null
  result.value = null
  error.value = null
  if (fileInput.value) fileInput.value.value = ''
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// --- OCR ---

async function runOcr() {
  if (!file.value) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('language', language.value)

    // Async-Job: übersteht auch sehr große Dateien ohne Browser-Timeout
    const response = await runJob('/api/pdf-extras/jobs/ocr', fd)

    // Extract metadata from headers
    const pagesProcessed = Number(response.headers.get('X-Pages-Processed') || 0)
    const charsRecognized = Number(response.headers.get('X-Characters-Recognized') || 0)

    // Extract filename from Content-Disposition
    const disposition = response.headers.get('Content-Disposition')
    let filename = (file.value.name || 'document').replace(/\.pdf$/i, '') + '_ocr.pdf'
    if (disposition) {
      const match = disposition.match(/filename="?([^";\n]+)"?/)
      if (match) filename = match[1]
    }

    // Create blob URL for download
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)

    result.value = {
      pagesProcessed,
      charsRecognized,
      blobUrl,
      filename,
    }
  } catch (e: any) {
    if (e.name === 'AbortError') {
      error.value = 'Zeitlimit ueberschritten. Bitte versuchen Sie es mit einem kleineren Dokument.'
    } else {
      error.value = e.message || 'Unbekannter Fehler bei der OCR-Verarbeitung'
    }
  } finally {
    loading.value = false
  }
}

// --- Download & Reset ---

function downloadResult() {
  if (!result.value?.blobUrl) return
  const a = document.createElement('a')
  a.href = result.value.blobUrl
  a.download = result.value.filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function reset() {
  if (result.value?.blobUrl) {
    URL.revokeObjectURL(result.value.blobUrl)
  }
  file.value = null
  result.value = null
  error.value = null
  language.value = 'deu'
  if (fileInput.value) fileInput.value.value = ''
}

// Cleanup blob URL on unmount
onUnmounted(() => {
  if (result.value?.blobUrl) {
    URL.revokeObjectURL(result.value.blobUrl)
  }
})
</script>
