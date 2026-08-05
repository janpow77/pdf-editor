<template>
  <div class="space-y-3">
    <div v-if="loading" class="flex items-center justify-center py-10" role="status">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="ml-2 text-sm font-medium text-gray-600 dark:text-gray-300">Vorschau wird geladen…</span>
    </div>

    <div v-else-if="sortedPages.length" class="grid gap-4" :class="gridCols">
      <article
        v-for="(pageNum, index) in sortedPages"
        :key="pageNum"
        class="group relative overflow-hidden rounded-2xl bg-white shadow-apple-sm ring-2 transition-all dark:bg-gray-900"
        :class="isSelected(pageNum)
          ? 'ring-primary-500 shadow-apple'
          : 'ring-gray-300 hover:-translate-y-0.5 hover:ring-gray-500 dark:ring-gray-600 dark:hover:ring-gray-400'"
        :draggable="draggable"
        @dragstart="onDragStart($event, pageNum)"
        @dragover.prevent="onDragOver($event)"
        @drop="onDrop($event, pageNum)"
      >
        <!--
          Die Seitenauswahl ist ein echter Button. Rotations- und
          Reorder-Schaltflächen liegen als Geschwister daneben; damit werden
          keine interaktiven Elemente ineinander verschachtelt.
        -->
        <button
          v-if="selectable"
          type="button"
          class="block w-full text-left"
          :aria-pressed="isSelected(pageNum)"
          :aria-label="`Seite ${pageNum} ${isSelected(pageNum) ? 'abwählen' : 'auswählen'}`"
          @click="toggleSelect(pageNum)"
        >
          <PagePreview :page-num="pageNum" />
        </button>
        <PagePreview v-else :page-num="pageNum" />

        <div v-if="selectable" class="pointer-events-none absolute right-2 top-2 z-10" aria-hidden="true">
          <span
            class="grid h-6 w-6 place-items-center rounded-full shadow-sm ring-2"
            :class="isSelected(pageNum)
              ? 'bg-primary-600 text-white ring-primary-600'
              : 'bg-white/90 text-transparent ring-gray-400 dark:bg-gray-800/90 dark:ring-gray-500'"
          >✓</span>
        </div>

        <div
          v-if="showRotation || draggable"
          class="absolute bottom-2 right-2 z-10 flex gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
        >
          <UiIconButton
            v-if="draggable"
            size="sm"
            :disabled="index === 0"
            :aria-label="`Seite ${pageNum} nach vorne verschieben`"
            @click="movePage(index, -1)"
          >←</UiIconButton>
          <UiIconButton
            v-if="draggable"
            size="sm"
            :disabled="index === sortedPages.length - 1"
            :aria-label="`Seite ${pageNum} nach hinten verschieben`"
            @click="movePage(index, 1)"
          >→</UiIconButton>
          <UiIconButton
            v-if="showRotation"
            size="sm"
            :aria-label="`Seite ${pageNum} um 90 Grad nach links drehen`"
            @click="$emit('rotate', pageNum, 270)"
          >↶</UiIconButton>
          <UiIconButton
            v-if="showRotation"
            size="sm"
            :aria-label="`Seite ${pageNum} um 90 Grad nach rechts drehen`"
            @click="$emit('rotate', pageNum, 90)"
          >↷</UiIconButton>
        </div>
      </article>
    </div>

    <p v-else class="py-5 text-center text-sm text-gray-600 dark:text-gray-300">Keine Vorschau verfügbar.</p>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, type PropType } from 'vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'

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
  (event: 'select', pages: number[]): void
  (event: 'rotate', page: number, angle: number): void
  (event: 'reorder', from: number, to: number): void
}>()

const sortedPages = computed(() => Object.keys(props.thumbnails).map(Number).filter(Number.isFinite).sort((a, b) => a - b))

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
  const current = [...props.selectedPages]
  const index = current.indexOf(page)
  if (index >= 0) current.splice(index, 1)
  else current.push(page)
  emit('select', current.sort((a, b) => a - b))
}

function rotationClass(page: number): string {
  const rotation = props.rotations[page] || 0
  if (rotation === 90) return 'rotate-90'
  if (rotation === 180) return 'rotate-180'
  if (rotation === 270) return '-rotate-90'
  return ''
}

/** Kleine interne Darstellungskomponente vermeidet doppeltes Bild-Markup. */
const PagePreview = defineComponent({
  name: 'PagePreview',
  props: {
    pageNum: { type: Number as PropType<number>, required: true },
  },
  setup(componentProps) {
    return () => h('div', { class: 'relative overflow-hidden' }, [
      h('span', {
        class: 'absolute left-2 top-2 z-10 rounded-full bg-gray-950/80 px-2 py-1 text-xs font-semibold text-white backdrop-blur-md',
      }, `Seite ${componentProps.pageNum}`),
      h('img', {
        src: `data:image/png;base64,${props.thumbnails[String(componentProps.pageNum)]}`,
        alt: `Vorschau der PDF-Seite ${componentProps.pageNum}`,
        class: ['h-auto w-full bg-white transition-transform', rotationClass(componentProps.pageNum)],
      }),
    ])
  },
})

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
  if (dragSource && dragSource !== targetPage) emit('reorder', dragSource, targetPage)
  dragSource = 0
}

function movePage(index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= sortedPages.value.length) return
  emit('reorder', sortedPages.value[index], sortedPages.value[target])
}
</script>
