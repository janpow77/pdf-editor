<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Word-Dateien zusammenführen</h2>
    </div>

    <!-- Drop zone -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="isDragging ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".docx,.doc" multiple class="hidden" @change="onFileSelect" />
      <p class="text-gray-500 dark:text-gray-400 mb-2">Word-Dateien (.docx) hierher ziehen oder</p>
      <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Dateien auswählen</button>
    </div>

    <!-- File list -->
    <div v-if="files.length > 0" class="space-y-2">
      <p class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ files.length }} Dateien</p>
      <div
        v-for="(file, idx) in files"
        :key="idx"
        class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
        draggable="true"
        @dragstart="dragIdx = idx"
        @dragover.prevent
        @drop.prevent="reorder(idx)"
      >
        <svg class="w-4 h-4 text-gray-400 cursor-grab" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16" />
        </svg>
        <span class="text-sm text-gray-600 dark:text-gray-300 font-mono">{{ idx + 1 }}.</span>
        <svg class="w-5 h-5 text-blue-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <span class="flex-1 text-sm text-gray-900 dark:text-white truncate">{{ file.name }}</span>
        <span class="text-xs text-gray-400">{{ formatSize(file.size) }}</span>
        <button class="text-gray-400 hover:text-red-500" @click="files.splice(idx, 1)">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </div>

    <!-- Options -->
    <div v-if="files.length >= 2" class="flex items-center gap-2">
      <label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
        <input v-model="addPageBreak" type="checkbox" class="text-primary-600 rounded" />
        Seitenumbruch zwischen Dokumenten
      </label>
    </div>

    <div class="flex items-center gap-3">
      <button
        :disabled="files.length < 2 || loading"
        class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        @click="doMerge"
      >
        <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ loading ? 'Zusammenführen...' : 'Word-Dateien zusammenführen' }}
      </button>
      <span v-if="files.length === 1" class="text-sm text-amber-600">Mindestens 2 Dateien erforderlich</span>
    </div>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, wordMerge } = usePdfTools()
const files = ref<File[]>([])
const isDragging = ref(false)
const dragIdx = ref(-1)
const addPageBreak = ref(true)

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    files.value.push(...Array.from(input.files).filter(f => f.name.toLowerCase().endsWith('.docx') || f.name.toLowerCase().endsWith('.doc')))
  }
  input.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) {
    files.value.push(...Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.docx') || f.name.toLowerCase().endsWith('.doc')))
  }
}

function reorder(targetIdx: number) {
  if (dragIdx.value === targetIdx) return
  const item = files.value.splice(dragIdx.value, 1)[0]
  files.value.splice(targetIdx, 0, item)
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function doMerge() {
  await withLoading(() => wordMerge(files.value, addPageBreak.value))
}
</script>
