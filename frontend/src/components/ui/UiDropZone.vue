<template>
  <div
    :class="zoneClass"
    @dragenter.prevent="setDragActive(true)"
    @dragover.prevent="setDragActive(true)"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
/**
 * Einheitliche Upload- und Drop-Fläche für einfache und mehrfache Uploads.
 *
 * Die Komponente kapselt Material, Radius und Zustandsfarben. Dateiauswahl und
 * fachliche Validierung bleiben bewusst im aufrufenden Werkzeug. Beim Wechsel
 * zwischen Kindelementen wird der Drag-Zustand nicht zurückgesetzt; nur das
 * tatsächliche Verlassen der gesamten Fläche beendet die Hervorhebung.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  active?: boolean
  accepted?: boolean
  invalid?: boolean
}>(), {
  active: false,
  accepted: false,
  invalid: false,
})

const emit = defineEmits<{
  (event: 'drop', files: File[]): void
  (event: 'drag-active', active: boolean): void
}>()

const zoneClass = computed(() => [
  'rounded-[1.5rem] border-2 border-dashed p-7 text-center shadow-inner backdrop-blur-xl transition',
  'border-gray-500/75 bg-white/65 hover:border-primary-500 hover:bg-primary-50/70',
  'dark:border-gray-400/75 dark:bg-white/[0.05] dark:hover:border-primary-400 dark:hover:bg-primary-500/10',
  props.active ? 'border-primary-500 bg-primary-50/80 dark:border-primary-400 dark:bg-primary-500/10' : '',
  props.accepted ? 'border-emerald-500 bg-emerald-50/75 dark:border-emerald-400 dark:bg-emerald-500/10' : '',
  props.invalid ? 'border-rose-500 bg-rose-50/75 dark:border-rose-400 dark:bg-rose-500/10' : '',
])

function setDragActive(active: boolean): void {
  emit('drag-active', active)
}

function onDragLeave(event: DragEvent): void {
  const current = event.currentTarget as HTMLElement | null
  const related = event.relatedTarget
  if (current && related instanceof Node && current.contains(related)) return
  setDragActive(false)
}

function onDrop(event: DragEvent): void {
  setDragActive(false)
  emit('drop', Array.from(event.dataTransfer?.files ?? []))
}
</script>
