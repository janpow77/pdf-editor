<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Word zu PDF</h2>
    </div>

    <!-- Upload -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="file ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".docx,.doc" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <p class="text-gray-500 dark:text-gray-400 mb-2">Word-Datei (.docx) hierher ziehen oder</p>
        <button class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Datei auswählen</button>
      </div>
      <div v-else>
        <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
        <p class="text-sm text-gray-500">{{ formatSize(file.size) }}</p>
        <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="file = null">Entfernen</button>
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
      {{ loading ? 'Konvertiere...' : 'In PDF umwandeln' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, wordToPdf } = usePdfTools()
const file = ref<File | null>(null)

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) file.value = input.files[0]
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.docx') || f?.name.toLowerCase().endsWith('.doc')) file.value = f
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function doConvert() {
  if (!file.value) return
  await withLoading(() => wordToPdf(file.value!))
}
</script>
