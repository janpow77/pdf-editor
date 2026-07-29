<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Seiten rotieren</h2>
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

    <!-- Quick actions -->
    <div v-if="file && Object.keys(thumbnails).length > 0" class="flex flex-wrap gap-2">
      <button class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300" @click="rotateAll(90)">Alle 90° rechts</button>
      <button class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300" @click="rotateAll(180)">Alle 180°</button>
      <button class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300" @click="rotateAll(270)">Alle 90° links</button>
      <button class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 text-red-500" @click="rotations = {}">Zurücksetzen</button>
    </div>

    <!-- Info text -->
    <p v-if="file && Object.keys(thumbnails).length > 0" class="text-xs text-gray-400">
      Klicken Sie auf die Rotations-Buttons an den einzelnen Seiten oder nutzen Sie die Schnellaktionen oben.
      {{ Object.keys(rotations).length }} Seite(n) werden rotiert.
    </p>

    <!-- Thumbnails with rotation -->
    <PageThumbnailGrid
      v-if="Object.keys(thumbnails).length > 0"
      :thumbnails="thumbnails"
      :loading="loadingThumbs"
      :show-rotation="true"
      :rotations="rotations"
      @rotate="onRotatePage"
    />

    <!-- Action -->
    <button
      v-if="file && Object.keys(rotations).length > 0"
      :disabled="loading"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doRotate"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Rotiere...' : `${Object.keys(rotations).length} Seite(n) rotieren` }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'
import PageThumbnailGrid from './PageThumbnailGrid.vue'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, rotatePdf, getThumbnails } = usePdfTools()
const file = ref<File | null>(null)
const thumbnails = ref<Record<string, string>>({})
const loadingThumbs = ref(false)
const rotations = ref<Record<number, number>>({})

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
  rotations.value = {}
  loadingThumbs.value = true
  try {
    const data = await getThumbnails(f)
    thumbnails.value = data.thumbnails
  } catch { /* ignore */ }
  loadingThumbs.value = false
}

function reset() {
  file.value = null
  thumbnails.value = {}
  rotations.value = {}
}

function onRotatePage(page: number, angle: number) {
  const current = rotations.value[page] || 0
  const newAngle = (current + angle) % 360
  if (newAngle === 0) {
    delete rotations.value[page]
  } else {
    rotations.value[page] = newAngle
  }
  // Force reactivity
  rotations.value = { ...rotations.value }
}

function rotateAll(angle: number) {
  const pages = Object.keys(thumbnails.value).map(Number)
  const newRot: Record<number, number> = {}
  pages.forEach(p => { newRot[p] = angle })
  rotations.value = newRot
}

async function doRotate() {
  if (!file.value) return
  await withLoading(() => rotatePdf(file.value!, rotations.value))
}
</script>
