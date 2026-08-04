<template>
  <div class="space-y-3">
    <div v-if="loading" class="flex items-center justify-center py-10" role="status">
      <svg class="h-6 w-6 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span class="ml-2 text-sm font-medium text-gray-600 dark:text-gray-300">Vorschau wird geladen…</span>
    </div>

    <!--
      Standardmäßig werden nur vier statt sechs Spalten dargestellt. Zusammen
      mit den 320-Pixel-Renderings wächst die sichtbare Vorschau deutlich über
      die geforderten 50 Prozent; auf kleinen Geräten reduziert sich das Raster
      automatisch auf zwei Spalten.
    -->
    <div v-else-if="Object.keys(thumbnails).length > 0" class="grid gap-4" :class="gridCols">
      <div
        v-for="pageNum in sortedPages"
        :key="pageNum"
        class="group relative overflow-hidden rounded-2xl bg-white shadow-apple-sm ring-2 transition-all
               dark:bg-gray-900"
        :class="[
          isSelected(pageNum)
            ? 'ring-primary-500 shadow-apple'
            : 'ring-gray-300 hover:-translate-y-0.5 hover:ring-gray-500 dark:ring-gray-600 dark:hover:ring-gray-400',
          rotationClass(pageNum),
          selectable ? 'cursor-pointer' : '',
        ]"
        :draggable="draggable"
        :role="selectable ? 'button' : undefined"
        :tabindex="selectable ? 0 : undefined"
        :aria-pressed="selectable ? isSelected(pageNum) : undefined"
        :aria-label="selectable ? `Seite ${pageNum} ${isSelected(pageNum) ? 'abwählen' : 'auswählen'}` : undefined"
        @click="toggleSelect(pageNum)"
        @keydown.enter.prevent="toggleSelect(pageNum)"
        @keydown.space.prevent="toggleSelect(pageNum)"
        @dragstart="onDragStart($event, pageNum)"
        @dragover.prevent="onDragOver($event)"
        @drop="onDrop($event, pageNum)"
      >
        <div class="absolute left-2 top-2 z-10 rounded-full bg-gray-950/80 px-2 py-1 text-xs font-semibold text-white backdrop-blur-md">
          Seite {{ pageNum }}
        </div>

        <div v-if="selectable" class="absolute right-2 top-2 z-10" aria-hidden="true">
          <div
            class="grid h-6 w-6 place-items-center rounded-full shadow-sm ring-2"
            :class="isSelected(pageNum)
              ? 'bg-primary-600 text-white ring-primary-600'
              : 'bg-white/90 text-transparent ring-gray-400 dark:bg-gray-800/90 dark:ring-gray-500'"
          >✓</div>
        </div>

        <div v-if="showRotation" class="absolute bottom-2 right-2 z-10 flex gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-gray-950/80 text-white backdrop-blur-md hover:bg-gray-950" aria-label="Seite 90 Grad nach links drehen" @click.stop="$emit('rotate', pageNum, 270)">↶</button>
          <button type="button" class="grid h-9 w-9 place-items-center rounded-full bg-gray-950/80 text-white backdrop-blur-md hover:bg-gray-950" aria-label="Seite 90 Grad nach rechts drehen" @click.stop="$emit('rotate', pageNum, 90)">↷</button>
        </div>

        <img
          :src="'data:image/png;base64,' + thumbnails[String(pageNum)]"
          :alt="`Vorschau der PDF-Seite ${pageNum}`"
          class="h-auto w-full bg-white"
        />
      </div>
    </div>

    <p v-else class="py-5 text-center text-sm text-gray-600 dark:text-gray-300">Keine Vorschau verfügbar.</p>
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
  columns: 4,
})

const emit = defineEmits<{
  (e: 'select', pages: number[]): void
  (e: 'rotate', page: number, angle: number): void
  (e: 'reorder', from: number, to: number): void
}>()

const sortedPages = computed(() => Object.keys(props.thumbnails).map(Number).sort((a, b) => a - b))

const gridCols = computed(() => {
  const columns = props.columns
  if (columns <= 2) return 'grid-cols-1 sm:grid-cols-2'
  if (columns <= 3) return 'grid-cols-2 lg:grid-cols-3'
  if (columns <= 4) return 'grid-cols-2 sm:grid-cols-3 xl:grid-cols-4'
  return 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5'
})

function isSelected(page: number): boolean {
  return props.selectedPages.includes(page)
}

function toggleSelect(page: number): void {
  if (!props.selectable) return
  const current = [...props.selectedPages]
  const index = current.indexOf(page)
  if (index >= 0) current.splice(index, 1)
  else current.push(page)
  emit('select', current.sort((a, b) => a - b))
}

function rotationClass(page: number): string {
  const rotation = props.rotations[page] || 0
  if (rotation === 90) return 'thumbnail-rotate-90'
  if (rotation === 180) return 'thumbnail-rotate-180'
  if (rotation === 270) return 'thumbnail-rotate-270'
  return ''
}

let dragSource = 0
function onDragStart(event: DragEvent, page: number): void {
  if (!props.draggable) return
  dragSource = page
  event.dataTransfer?.setData('text/plain', String(page))
}

function onDragOver(event: DragEvent): void {
  if (props.draggable) event.preventDefault()
}

function onDrop(event: DragEvent, targetPage: number): void {
  if (!props.draggable) return
  event.preventDefault()
  if (dragSource !== targetPage) emit('reorder', dragSource, targetPage)
}
</script>

<style scoped>
/* Die Rotation bleibt auf das Bild beschränkt, damit Bedienflächen gerade bleiben. */
.thumbnail-rotate-90 img { transform: rotate(90deg); }
.thumbnail-rotate-180 img { transform: rotate(180deg); }
.thumbnail-rotate-270 img { transform: rotate(270deg); }
</style>
