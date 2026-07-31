<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Bilder zu PDF</h2>
    </div>

    <!-- Drop zone -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="isDragging ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept="image/*" multiple class="hidden" @change="onFileSelect" />
      <p class="text-gray-500 dark:text-gray-400 mb-2">Bilder hierher ziehen oder</p>
      <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Bilder auswählen</button>
      <p class="text-xs text-gray-600 dark:text-gray-400 mt-2">PNG, JPG, GIF, BMP, TIFF, WebP</p>
    </div>

    <!-- Preview grid -->
    <div v-if="files.length > 0" class="space-y-3">
      <p class="text-sm font-medium text-gray-700 dark:text-gray-300">{{ files.length }} Bilder</p>
      <div class="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
        <div
          v-for="(file, idx) in files"
          :key="idx"
          class="relative group aspect-square border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden"
          draggable="true"
          @dragstart="dragIdx = idx"
          @dragover.prevent
          @drop.prevent="reorder(idx)"
        >
          <img :src="previews[idx]" :alt="file.name" class="w-full h-full object-cover" />
          <div class="absolute top-0 left-0 bg-black/60 text-white text-xs px-1">{{ idx + 1 }}</div>
          <button
            class="absolute top-0 right-0 bg-red-500 text-white w-5 h-5 text-xs opacity-0 group-hover:opacity-100 transition-opacity"
            @click="removeFile(idx)"
          >
            ×
          </button>
        </div>
      </div>
    </div>

    <!-- Options -->
    <div v-if="files.length > 0" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Seitengröße</label>
          <select v-model="pageSize" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm">
            <option value="a4">A4</option>
            <option value="a3">A3</option>
            <option value="letter">Letter</option>
            <option value="legal">Legal</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ausrichtung</label>
          <select v-model="orientation" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm">
            <option value="portrait">Hochformat</option>
            <option value="landscape">Querformat</option>
          </select>
        </div>
      </div>
    </div>

    <button
      v-if="files.length > 0"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doConvert"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Erstelle PDF...' : 'PDF erstellen' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, imagesToPdf } = usePdfTools()
const files = ref<File[]>([])
const previews = ref<string[]>([])
const isDragging = ref(false)
const dragIdx = ref(-1)
const pageSize = ref('a4')
const orientation = ref('portrait')

const imageExts = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp']

function isImage(f: File) {
  return imageExts.some(ext => f.name.toLowerCase().endsWith(ext))
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) addFiles(Array.from(input.files))
  input.value = ''
}

function onDrop(e: DragEvent) {
  isDragging.value = false
  if (e.dataTransfer?.files) addFiles(Array.from(e.dataTransfer.files))
}

function addFiles(newFiles: File[]) {
  const valid = newFiles.filter(isImage)
  files.value.push(...valid)
  valid.forEach(f => {
    const url = URL.createObjectURL(f)
    previews.value.push(url)
  })
}

function removeFile(idx: number) {
  URL.revokeObjectURL(previews.value[idx])
  files.value.splice(idx, 1)
  previews.value.splice(idx, 1)
}

function reorder(targetIdx: number) {
  if (dragIdx.value === targetIdx) return
  const f = files.value.splice(dragIdx.value, 1)[0]
  const p = previews.value.splice(dragIdx.value, 1)[0]
  files.value.splice(targetIdx, 0, f)
  previews.value.splice(targetIdx, 0, p)
}

async function doConvert() {
  await withLoading(() => imagesToPdf(files.value, pageSize.value, orientation.value))
}
</script>
