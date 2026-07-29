<template>
  <div class="space-y-3">
    <div v-if="loading" class="flex items-center justify-center py-8">
      <svg class="animate-spin w-6 h-6 text-purple-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span class="ml-2 text-sm text-gray-500 dark:text-gray-400">Vorschau wird geladen...</span>
    </div>

    <div
      v-else-if="Object.keys(thumbnails).length > 0"
      class="grid gap-3"
      :class="gridCols"
    >
      <div
        v-for="pageNum in sortedPages"
        :key="pageNum"
        class="relative group cursor-pointer border-2 rounded-lg overflow-hidden transition-all"
        :class="[
          isSelected(pageNum)
            ? 'border-purple-500 ring-2 ring-purple-300 dark:ring-purple-600'
            : 'border-gray-200 dark:border-gray-600 hover:border-purple-300',
          rotationClass(pageNum)
        ]"
        :draggable="draggable"
        @click="toggleSelect(pageNum)"
        @dragstart="onDragStart($event, pageNum)"
        @dragover.prevent="onDragOver($event, pageNum)"
        @drop="onDrop($event, pageNum)"
      >
        <!-- Page number badge -->
        <div class="absolute top-1 left-1 z-10 bg-black/60 text-white text-xs px-1.5 py-0.5 rounded">
          {{ pageNum }}
        </div>

        <!-- Selection checkbox -->
        <div v-if="selectable" class="absolute top-1 right-1 z-10">
          <div
            class="w-5 h-5 rounded border-2 flex items-center justify-center transition-colors"
            :class="isSelected(pageNum)
              ? 'bg-purple-500 border-purple-500 text-white'
              : 'bg-white/80 border-gray-300 dark:bg-gray-700/80 dark:border-gray-500'"
          >
            <svg v-if="isSelected(pageNum)" class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          </div>
        </div>

        <!-- Rotation buttons -->
        <div v-if="showRotation" class="absolute bottom-1 right-1 z-10 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            class="w-6 h-6 bg-black/60 text-white rounded flex items-center justify-center hover:bg-black/80"
            title="90° links drehen"
            @click.stop="$emit('rotate', pageNum, 270)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h1l1-2h6l1 2h1M12 3v3m0 0l-3-2m3 2l3-2M9 21h6a2 2 0 002-2v-5H7v5a2 2 0 002 2z" />
            </svg>
          </button>
          <button
            class="w-6 h-6 bg-black/60 text-white rounded flex items-center justify-center hover:bg-black/80"
            title="90° rechts drehen"
            @click.stop="$emit('rotate', pageNum, 90)"
          >
            <svg class="w-4 h-4 transform scale-x-[-1]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h1l1-2h6l1 2h1M12 3v3m0 0l-3-2m3 2l3-2M9 21h6a2 2 0 002-2v-5H7v5a2 2 0 002 2z" />
            </svg>
          </button>
        </div>

        <!-- Thumbnail image -->
        <img
          :src="'data:image/png;base64,' + thumbnails[String(pageNum)]"
          :alt="'Seite ' + pageNum"
          class="w-full h-auto"
        />
      </div>
    </div>

    <p v-else class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
      Keine Vorschau verfügbar
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  thumbnails: Record<string, string>
  loading?: boolean
  selectedPages?: number[]
  selectable?: boolean
  draggable?: boolean
  showRotation?: boolean
  rotations?: Record<number, number>
  columns?: number
}>(), {
  loading: false,
  selectedPages: () => [],
  selectable: false,
  draggable: false,
  showRotation: false,
  rotations: () => ({}),
  columns: 6,
})

const emit = defineEmits<{
  (e: 'select', pages: number[]): void
  (e: 'rotate', page: number, angle: number): void
  (e: 'reorder', from: number, to: number): void
}>()

const sortedPages = computed(() =>
  Object.keys(props.thumbnails).map(Number).sort((a, b) => a - b)
)

const gridCols = computed(() => {
  const c = props.columns
  if (c <= 3) return 'grid-cols-2 sm:grid-cols-3'
  if (c <= 4) return 'grid-cols-3 sm:grid-cols-4'
  if (c <= 6) return 'grid-cols-3 sm:grid-cols-4 md:grid-cols-6'
  return 'grid-cols-4 sm:grid-cols-6 md:grid-cols-8'
})

function isSelected(page: number) {
  return props.selectedPages.includes(page)
}

function toggleSelect(page: number) {
  if (!props.selectable) return
  const current = [...props.selectedPages]
  const idx = current.indexOf(page)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(page)
  }
  emit('select', current.sort((a, b) => a - b))
}

function rotationClass(page: number) {
  const r = props.rotations[page] || 0
  if (r === 90) return 'thumbnail-rotate-90'
  if (r === 180) return 'thumbnail-rotate-180'
  if (r === 270) return 'thumbnail-rotate-270'
  return ''
}

let dragSource = 0

function onDragStart(e: DragEvent, page: number) {
  if (!props.draggable) return
  dragSource = page
  e.dataTransfer?.setData('text/plain', String(page))
}

function onDragOver(e: DragEvent, _page: number) {
  if (!props.draggable) return
  e.preventDefault()
}

function onDrop(e: DragEvent, targetPage: number) {
  if (!props.draggable) return
  e.preventDefault()
  if (dragSource !== targetPage) {
    emit('reorder', dragSource, targetPage)
  }
}
</script>

<style scoped>
.thumbnail-rotate-90 img { transform: rotate(90deg); }
.thumbnail-rotate-180 img { transform: rotate(180deg); }
.thumbnail-rotate-270 img { transform: rotate(270deg); }
</style>
