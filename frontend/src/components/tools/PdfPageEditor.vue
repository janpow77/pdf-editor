<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Seiten ordnen / löschen</h2>
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
        <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="reset">Entfernen</button>
      </div>
    </div>

    <!-- Instructions -->
    <div v-if="file && pageOrder.length > 0" class="flex items-center gap-3 flex-wrap">
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Seiten per Drag & Drop umsortieren. Klicken um zu löschen/wiederherstellen.
      </p>
      <span class="text-sm font-medium text-purple-600">
        {{ pageOrder.filter(p => !deletedPages.has(p)).length }} / {{ pageOrder.length }} Seiten
      </span>
      <button v-if="deletedPages.size > 0" class="text-sm text-blue-500 hover:text-blue-700" @click="deletedPages.clear()">Alle wiederherstellen</button>
    </div>

    <!-- Page grid -->
    <div v-if="Object.keys(thumbnails).length > 0" class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
      <div
        v-for="(pageNum, idx) in pageOrder"
        :key="pageNum + '-' + idx"
        class="relative group cursor-pointer border-2 rounded-lg overflow-hidden transition-all"
        :class="deletedPages.has(pageNum) ? 'border-red-300 opacity-40' : 'border-gray-200 dark:border-gray-600 hover:border-purple-300'"
        draggable="true"
        @dragstart="dragIdx = idx"
        @dragover.prevent
        @drop.prevent="reorder(idx)"
        @click="toggleDelete(pageNum)"
      >
        <div class="absolute top-1 left-1 z-10 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
          {{ pageNum }}
        </div>
        <div v-if="deletedPages.has(pageNum)" class="absolute inset-0 z-10 flex items-center justify-center bg-red-500/20">
          <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
        </div>
        <img
          v-if="thumbnails[String(pageNum)]"
          :src="'data:image/png;base64,' + thumbnails[String(pageNum)]"
          :alt="'Seite ' + pageNum"
          class="w-full h-auto"
        />
      </div>
    </div>

    <div v-if="loadingThumbs" class="flex items-center justify-center py-8">
      <svg class="animate-spin w-6 h-6 text-purple-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span class="ml-2 text-sm text-gray-500">Vorschau laden...</span>
    </div>

    <button
      v-if="file && pageOrder.length > 0"
      :disabled="loading || activePages.length === 0"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doApply"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Anwenden...' : `Änderungen anwenden (${activePages.length} Seiten)` }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, getThumbnails, pageOperations } = usePdfTools()
const file = ref<File | null>(null)
const thumbnails = ref<Record<string, string>>({})
const loadingThumbs = ref(false)
const pageOrder = ref<number[]>([])
const deletedPages = reactive(new Set<number>())
const dragIdx = ref(-1)

const activePages = computed(() => pageOrder.value.filter(p => !deletedPages.has(p)))

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
  deletedPages.clear()
  loadingThumbs.value = true
  try {
    const data = await getThumbnails(f)
    thumbnails.value = data.thumbnails
    pageOrder.value = Object.keys(data.thumbnails).map(Number).sort((a, b) => a - b)
  } catch { /* ignore */ }
  loadingThumbs.value = false
}

function reset() {
  file.value = null
  thumbnails.value = {}
  pageOrder.value = []
  deletedPages.clear()
}

function toggleDelete(page: number) {
  if (deletedPages.has(page)) {
    deletedPages.delete(page)
  } else {
    deletedPages.add(page)
  }
}

function reorder(targetIdx: number) {
  if (dragIdx.value === targetIdx) return
  const item = pageOrder.value.splice(dragIdx.value, 1)[0]
  pageOrder.value.splice(targetIdx, 0, item)
}

async function doApply() {
  if (!file.value) return
  await withLoading(() => pageOperations(file.value!, activePages.value))
}
</script>
