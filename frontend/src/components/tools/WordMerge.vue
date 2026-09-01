<template>
  <div class="space-y-5">
    <ToolHeader title="Word-Dateien zusammenführen" description="Mehrere DOC- oder DOCX-Dateien in einer stabilen Reihenfolge verbinden." @back="$emit('back')" />

    <UiDropZone :active="isDragging" @drag-active="isDragging = $event" @drop="onDroppedFiles">
      <input ref="fileInput" type="file" accept=".docx,.doc" multiple class="hidden" @change="onFileSelect" />
      <p class="font-semibold text-gray-950 dark:text-white">Word-Dateien hierher ziehen</p>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Die Reihenfolge kann anschließend per Drag & Drop oder über Pfeiltasten geändert werden.</p>
      <UiButton variant="primary" class="mt-4" @click="fileInput?.click()">Dateien auswählen</UiButton>
    </UiDropZone>

    <section v-if="items.length" class="space-y-3" aria-labelledby="word-merge-list">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 id="word-merge-list" class="font-semibold text-gray-950 dark:text-white">{{ items.length }} Dateien</h3>
        <UiButton variant="danger" size="sm" @click="clearItems">Alle entfernen</UiButton>
      </div>
      <ol class="space-y-2">
        <UiPanel
          v-for="(item, index) in items"
          :key="item.id"
          as="li"
          padding="sm"
          class="flex items-center gap-3"
          draggable="true"
          @dragstart="dragIndex = index"
          @dragover.prevent
          @drop.prevent="reorder(index)"
        >
          <span class="cursor-grab text-gray-500" aria-hidden="true">☰</span>
          <span class="text-sm font-mono text-gray-600 dark:text-gray-300">{{ index + 1 }}.</span>
          <span class="min-w-0 flex-1 truncate text-sm font-semibold">{{ item.file.name }}</span>
          <span class="text-xs opacity-65">{{ formatFileSize(item.file.size) }}</span>
          <UiIconButton size="sm" :disabled="index === 0" :aria-label="`${item.file.name} nach oben verschieben`" @click="moveItem(index, -1)">↑</UiIconButton>
          <UiIconButton size="sm" :disabled="index === items.length - 1" :aria-label="`${item.file.name} nach unten verschieben`" @click="moveItem(index, 1)">↓</UiIconButton>
          <UiIconButton variant="danger" size="sm" :aria-label="`${item.file.name} entfernen`" @click="removeItem(item.id)">×</UiIconButton>
        </UiPanel>
      </ol>
    </section>

    <label v-if="items.length >= 2" class="ui-choice">
      <input v-model="addPageBreak" type="checkbox" class="rounded" /> Seitenumbruch zwischen Dokumenten
    </label>

    <div class="flex flex-wrap items-center gap-3">
      <UiButton variant="primary" size="lg" :loading="loading" :disabled="items.length < 2" @click="doMerge">
        {{ loading ? 'Zusammenführen…' : 'Word-Dateien zusammenführen' }}
      </UiButton>
      <UiAlert v-if="items.length === 1" tone="warning">Mindestens zwei Dateien erforderlich.</UiAlert>
    </div>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { usePdfTools } from '@/composables/usePdfTools'
import { formatFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

interface WordMergeItem {
  id: string
  file: File
}

const { loading, error, withLoading, wordMerge } = usePdfTools()
const items = ref<WordMergeItem[]>([])
const isDragging = ref(false)
const dragIndex = ref(-1)
const addPageBreak = ref(true)
const fileInput = ref<HTMLInputElement | null>(null)
let nextId = 1

function isWordFile(file: File): boolean {
  const name = file.name.toLowerCase()
  return name.endsWith('.docx') || name.endsWith('.doc')
}

function addFiles(files: File[]): void {
  for (const file of files.filter(isWordFile)) {
    items.value.push({ id: `word-${Date.now()}-${nextId++}`, file })
  }
}

function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  addFiles(Array.from(input.files ?? []))
  input.value = ''
}

function onDroppedFiles(files: File[]): void {
  addFiles(files)
}

function removeItem(id: string): void {
  items.value = items.value.filter((item) => item.id !== id)
}

function clearItems(): void {
  items.value = []
}

function moveItem(index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [item] = items.value.splice(index, 1)
  if (item) items.value.splice(target, 0, item)
}

function reorder(targetIndex: number): void {
  if (dragIndex.value < 0 || dragIndex.value === targetIndex) return
  const [item] = items.value.splice(dragIndex.value, 1)
  if (item) items.value.splice(targetIndex, 0, item)
  dragIndex.value = -1
}

async function doMerge(): Promise<void> {
  await withLoading(() => wordMerge(items.value.map((item) => item.file), addPageBreak.value))
}
</script>
