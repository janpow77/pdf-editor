<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF komprimieren</h2>
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
        <p class="text-sm text-gray-500">{{ formatSize(file.size) }}</p>
        <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="file = null; result = null">Entfernen</button>
      </div>
    </div>

    <!-- Quality selection -->
    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Komprimierungsstufe</label>
      <div class="grid grid-cols-3 gap-3">
        <button
          v-for="q in qualities"
          :key="q.value"
          class="p-3 rounded-lg border-2 text-center transition-colors"
          :class="quality === q.value
            ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
            : 'border-gray-200 dark:border-gray-600 hover:border-purple-300'"
          @click="quality = q.value"
        >
          <div class="text-lg mb-1">{{ q.icon }}</div>
          <div class="text-sm font-medium text-gray-900 dark:text-white">{{ q.label }}</div>
          <div class="text-xs text-gray-500">{{ q.desc }}</div>
        </button>
      </div>
    </div>

    <!-- Result -->
    <div v-if="result" class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-xl p-4">
      <div class="grid grid-cols-3 gap-4 text-center">
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">Original</p>
          <p class="text-lg font-bold text-gray-900 dark:text-white">{{ formatSize(result.originalSize) }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">Komprimiert</p>
          <p class="text-lg font-bold text-green-600">{{ formatSize(result.compressedSize) }}</p>
        </div>
        <div>
          <p class="text-xs text-gray-500 dark:text-gray-400">Ersparnis</p>
          <p class="text-lg font-bold text-purple-600">{{ result.ratio }}%</p>
        </div>
      </div>
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doCompress"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Komprimiere...' : 'PDF komprimieren' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, compressPdf } = usePdfTools()
const file = ref<File | null>(null)
const quality = ref('medium')
const result = ref<{ originalSize: number; compressedSize: number; savings: number; ratio: number } | null>(null)

const qualities = [
  { value: 'low', label: 'Maximal', desc: 'Kleinste Datei', icon: '🗜️' },
  { value: 'medium', label: 'Ausgewogen', desc: 'Gute Balance', icon: '⚖️' },
  { value: 'high', label: 'Minimal', desc: 'Beste Qualität', icon: '✨' },
]

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) { file.value = input.files[0]; result.value = null }
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) { file.value = f; result.value = null }
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function doCompress() {
  if (!file.value) return
  const meta = await withLoading(() => compressPdf(file.value!, quality.value))
  if (meta) result.value = meta
}
</script>
