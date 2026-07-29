<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF in Bilder umwandeln</h2>
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
        <button class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Datei auswählen</button>
      </div>
      <div v-else>
        <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
        <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="file = null">Entfernen</button>
      </div>
    </div>

    <!-- Options -->
    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Seiten</label>
          <input
            v-model="pages"
            type="text"
            class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
            placeholder="alle (oder z.B. 1-5)"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Format</label>
          <select v-model="format" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm">
            <option value="png">PNG (verlustfrei)</option>
            <option value="jpg">JPG (kleiner)</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Auflösung (DPI)</label>
          <select v-model.number="dpi" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm">
            <option :value="72">72 DPI (Bildschirm)</option>
            <option :value="150">150 DPI (Standard)</option>
            <option :value="300">300 DPI (Druck)</option>
            <option :value="600">600 DPI (Hochqualität)</option>
          </select>
        </div>
      </div>
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doConvert"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Konvertiere...' : 'In Bilder umwandeln' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, pdfToImages } = usePdfTools()
const file = ref<File | null>(null)
const pages = ref('')
const format = ref('png')
const dpi = ref(150)

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) file.value = input.files[0]
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) file.value = f
}

async function doConvert() {
  if (!file.value) return
  await withLoading(() => pdfToImages(file.value!, pages.value || undefined, format.value, dpi.value))
}
</script>
