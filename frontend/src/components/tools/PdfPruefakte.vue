<template>
  <div class="space-y-5">
    <ToolHeader title="Prüfakte erstellen" description="Mehrere PDFs mit Dokument-Lesezeichen und optional durchgehender Bates-Nummerierung verbinden." @back="$emit('back')" />

    <UiDropZone :active="dragging" :accepted="Boolean(items.length)" :invalid="Boolean(uploadError)" @drag-active="dragging = $event" @drop="enqueueFiles">
      <input ref="input" type="file" accept=".pdf,application/pdf" multiple class="hidden" @change="onSelect" />
      <p class="font-semibold text-gray-950 dark:text-white">PDFs für die Prüfakte ablegen</p>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Die Reihenfolge bestimmt Lesezeichen und Seitenfolge.</p>
      <UiButton variant="primary" class="mt-4" :disabled="adding" @click="input?.click()">Dateien auswählen</UiButton>
    </UiDropZone>
    <UiAlert v-if="uploadError" tone="danger">{{ uploadError }}</UiAlert>

    <UiPanel v-if="items.length" class="space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2"><strong>{{ items.length }} Dokumente</strong><UiButton variant="danger" size="sm" @click="clearFiles">Alle entfernen</UiButton></div>
      <ol class="space-y-2">
        <li v-for="(item, index) in items" :key="item.id" class="flex items-center gap-2 rounded-2xl bg-gray-100/80 p-2 dark:bg-white/5">
          <span class="w-7 text-center text-xs font-semibold tabular-nums">{{ index + 1 }}</span>
          <span class="min-w-0 flex-1 truncate text-sm">{{ item.file.name }}</span>
          <span class="text-xs text-gray-600 dark:text-gray-400">{{ formatFileSize(item.file.size) }}</span>
          <UiIconButton size="sm" :disabled="index === 0" :aria-label="`${item.file.name} nach oben verschieben`" @click="move(index, -1)">↑</UiIconButton>
          <UiIconButton size="sm" :disabled="index === items.length - 1" :aria-label="`${item.file.name} nach unten verschieben`" @click="move(index, 1)">↓</UiIconButton>
          <UiIconButton size="sm" variant="danger" :aria-label="`${item.file.name} entfernen`" @click="remove(item.id)">×</UiIconButton>
        </li>
      </ol>
    </UiPanel>

    <UiPanel v-if="items.length >= 2">
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Bates-Präfix" for-id="pruefakte-prefix" hint="Leer lassen, um keine Nummerierung einzufügen."><input id="pruefakte-prefix" v-model="batesPrefix" type="text" placeholder="AKTE-" class="ui-control w-full" /></UiField>
        <UiField label="Stellen" for-id="pruefakte-digits"><input id="pruefakte-digits" v-model.number="batesDigits" type="number" min="1" max="12" class="ui-control w-full" /></UiField>
      </div>
    </UiPanel>

    <UiAlert v-if="summary" tone="success" live>{{ summary }} – Prüfakte heruntergeladen.</UiAlert>
    <UiButton v-if="items.length >= 2" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Erstelle Akte…' : `Prüfakte aus ${items.length} Dateien erstellen` }}
    </UiButton>
    <UiAlert v-else-if="items.length === 1" tone="warning">Mindestens zwei Dateien erforderlich.</UiAlert>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiField from '@/components/ui/UiField.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { apiPost, downloadBlob } from '@/lib/api'
import { formatFileSize, validatePdfFile, validateTotalFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

interface DossierItem { id: string; file: File }
const MAX_FILES = 50
const notifications = useNotifications()
const input = ref<HTMLInputElement | null>(null)
const items = ref<DossierItem[]>([])
const batesPrefix = ref('')
const batesDigits = ref(6)
const summary = ref('')
const loading = ref(false)
const adding = ref(false)
const dragging = ref(false)
const uploadError = ref('')
const error = ref<string | null>(null)
let nextId = 1
let operationGeneration = 0
let addQueue = Promise.resolve()

function onSelect(event: Event): void {
  const target = event.target as HTMLInputElement
  const selected = Array.from(target.files ?? [])
  target.value = ''
  enqueueFiles(selected)
}

function enqueueFiles(files: File[]): void {
  dragging.value = false
  if (!files.length) return
  addQueue = addQueue.then(() => addFiles(files))
}

async function addFiles(files: File[]): Promise<void> {
  adding.value = true
  uploadError.value = ''
  const accepted: File[] = []
  const rejected: string[] = []
  const freeSlots = Math.max(0, MAX_FILES - items.value.length)
  for (const [index, file] of files.entries()) {
    if (index >= freeSlots) rejected.push(`${file.name}: Maximum von ${MAX_FILES} Dokumenten erreicht`)
    else {
      const validation = await validatePdfFile(file)
      if (validation.valid) accepted.push(file)
      else rejected.push(`${file.name}: ${validation.message ?? 'ungültige PDF-Datei'}`)
    }
  }
  const total = validateTotalFileSize([...items.value.map((item) => item.file), ...accepted])
  if (!total.valid) {
    accepted.length = 0
    rejected.push(total.message ?? 'Gesamtgrößenlimit überschritten')
  }
  items.value.push(...accepted.map((file) => ({ id: `dossier-${Date.now()}-${nextId++}`, file })))
  if (rejected.length) {
    uploadError.value = rejected.join(' ')
    notifications.warning('Einige Dateien wurden abgelehnt', uploadError.value)
  }
  if (accepted.length) notifications.success('Dokumente hinzugefügt', `${accepted.length} PDF-Datei(en) wurden übernommen.`)
  adding.value = false
  resetResult()
}

function resetResult(): void {
  operationGeneration += 1
  summary.value = ''
  error.value = null
}
function remove(id: string): void { items.value = items.value.filter((item) => item.id !== id); resetResult() }
function clearFiles(): void { items.value = []; uploadError.value = ''; resetResult() }
function move(index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [item] = items.value.splice(index, 1)
  if (item) items.value.splice(target, 0, item)
  resetResult()
}

async function apply(): Promise<void> {
  if (items.value.length < 2 || loading.value) return
  const generation = ++operationGeneration
  const snapshot = [...items.value]
  loading.value = true
  summary.value = ''
  error.value = null
  try {
    const formData = new FormData()
    snapshot.forEach((item) => formData.append('files', item.file))
    formData.append('bates_prefix', batesPrefix.value.trim())
    formData.append('bates_digits', String(Math.min(12, Math.max(1, Math.trunc(batesDigits.value)))))
    const response = await apiPost('/api/pdf-more/pruefakte', formData)
    await downloadBlob(response, 'pruefakte.pdf')
    if (generation !== operationGeneration) return
    summary.value = `${response.headers.get('X-Documents') || '?'} Dokumente, ${response.headers.get('X-Pages') || '?'} Seiten`
  } catch (caught: unknown) {
    if (generation === operationGeneration) error.value = caught instanceof Error ? caught.message : 'Prüfakte konnte nicht erstellt werden.'
  } finally {
    if (generation === operationGeneration) loading.value = false
  }
}
</script>
