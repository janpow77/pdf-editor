<template>
  <div class="space-y-5">
    <ToolHeader
      title="Seiten ordnen und löschen"
      description="Seiten per Drag & Drop neu anordnen oder gezielt deaktivieren."
      @back="$emit('back')"
    />

    <UiDropZone :accepted="Boolean(file)" :invalid="Boolean(uploadError)" @drop="onDroppedFiles">
      <input ref="fileInput" type="file" accept=".pdf,application/pdf" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-2xl text-violet-700 dark:bg-violet-400/15 dark:text-violet-300" aria-hidden="true">📑</div>
        <p class="mt-3 font-semibold text-gray-950 dark:text-white">PDF-Seiten bearbeiten</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Datei hierher ziehen oder lokal auswählen.</p>
        <UiButton variant="primary" class="mt-4" @click="fileInput?.click()">Datei auswählen</UiButton>
      </div>
      <div v-else>
        <p class="break-all font-semibold text-gray-950 dark:text-white">{{ file.name }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ pageOrder.length || '…' }} Seiten</p>
        <UiButton variant="danger" size="sm" class="mt-3" @click="reset">Entfernen</UiButton>
      </div>
    </UiDropZone>

    <UiAlert v-if="uploadError" tone="danger">{{ uploadError }}</UiAlert>

    <div v-if="file && pageOrder.length" class="flex flex-wrap items-center gap-3">
      <p class="text-sm text-gray-600 dark:text-gray-300">
        Seiten ziehen, um die Reihenfolge zu ändern. Mit Klick, Eingabe- oder Leertaste löschen beziehungsweise wiederherstellen.
      </p>
      <span class="rounded-full bg-primary-50 px-3 py-1.5 text-sm font-semibold text-primary-700 dark:bg-primary-500/15 dark:text-primary-300">
        {{ activePages.length }} / {{ pageOrder.length }} Seiten aktiv
      </span>
      <UiButton v-if="deletedPages.size" variant="ghost" size="sm" @click="restoreAll">Alle wiederherstellen</UiButton>
    </div>

    <!--
      Vier statt sechs Desktop-Spalten vergrößern jede Seitenvorschau um
      mindestens 50 Prozent. Die 320-Pixel-Renderings aus `usePdfTools` liefern
      dafür ausreichend Details, ohne kleine Displays horizontal zu überladen.
    -->
    <div v-if="Object.keys(thumbnails).length" class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
      <UiPanel
        v-for="(pageNum, index) in pageOrder"
        :key="pageNum"
        as="button"
        type="button"
        padding="sm"
        class="group relative overflow-hidden text-left transition-all"
        :class="deletedPages.has(pageNum)
          ? 'opacity-45 ring-rose-400'
          : 'hover:-translate-y-0.5 hover:shadow-apple'"
        draggable="true"
        :aria-pressed="deletedPages.has(pageNum)"
        :aria-label="`Seite ${pageNum} ${deletedPages.has(pageNum) ? 'wiederherstellen' : 'löschen'}`"
        @dragstart="dragIndex = index"
        @dragover.prevent
        @drop.prevent="reorder(index)"
        @click="toggleDelete(pageNum)"
      >
        <span class="absolute left-2 top-2 z-10 rounded-full bg-gray-950/80 px-2 py-1 text-xs font-semibold text-white">Seite {{ pageNum }}</span>
        <div v-if="deletedPages.has(pageNum)" class="absolute inset-0 z-10 flex items-center justify-center bg-rose-500/20" aria-hidden="true">
          <span class="grid h-12 w-12 place-items-center rounded-full bg-white/90 text-2xl text-rose-600 shadow-apple dark:bg-gray-900/90">×</span>
        </div>
        <img
          v-if="thumbnails[String(pageNum)]"
          :src="`data:image/png;base64,${thumbnails[String(pageNum)]}`"
          :alt="`Vorschau der PDF-Seite ${pageNum}`"
          class="h-auto w-full bg-white"
        />
      </UiPanel>
    </div>

    <div v-if="loadingThumbs" class="flex items-center justify-center py-10" role="status">
      <span class="h-7 w-7 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="ml-3 text-sm font-medium text-gray-600 dark:text-gray-300">Vorschau wird geladen…</span>
    </div>

    <UiButton
      v-if="file && pageOrder.length"
      variant="primary"
      size="lg"
      :loading="loading"
      :disabled="activePages.length === 0"
      @click="doApply"
    >{{ loading ? 'Änderungen werden angewendet…' : `Änderungen anwenden (${activePages.length} Seiten)` }}</UiButton>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { validatePdfFile } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, getThumbnails, pageOperations } = usePdfTools()
const notifications = useNotifications()
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const thumbnails = ref<Record<string, string>>({})
const loadingThumbs = ref(false)
const pageOrder = ref<number[]>([])
const deletedPages = reactive(new Set<number>())
const dragIndex = ref(-1)
const uploadError = ref('')
let latestPreviewRequest = 0

const activePages = computed(() => pageOrder.value.filter((page) => !deletedPages.has(page)))

function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  const selected = input.files?.[0]
  input.value = ''
  if (selected) void setFile(selected)
}

function onDroppedFiles(files: File[]): void {
  const selected = files[0]
  if (selected) void setFile(selected)
}

/**
 * Derselbe Request-Zähler wie im Teilen-Modul verhindert, dass eine verspätete
 * Vorschau des vorherigen Dokuments den aktuellen Seitenzustand überschreibt.
 */
async function setFile(selected: File): Promise<void> {
  const validation = await validatePdfFile(selected)
  if (!validation.valid) {
    uploadError.value = validation.message ?? 'Die PDF-Datei ist ungültig.'
    notifications.error('Datei nicht angenommen', uploadError.value)
    return
  }

  const requestId = ++latestPreviewRequest
  file.value = selected
  thumbnails.value = {}
  pageOrder.value = []
  deletedPages.clear()
  loadingThumbs.value = true
  uploadError.value = ''
  error.value = null

  try {
    const data = await getThumbnails(selected) as { thumbnails: Record<string, string> }
    if (requestId !== latestPreviewRequest || file.value !== selected) return
    thumbnails.value = data.thumbnails
    pageOrder.value = Object.keys(data.thumbnails).map(Number).sort((a, b) => a - b)
    notifications.success('Vorschau geladen', `${selected.name} ist zur Seitenbearbeitung bereit.`)
  } catch (previewError: unknown) {
    if (requestId !== latestPreviewRequest) return
    uploadError.value = notifications.errorFromUnknown(previewError, 'Die Seitenvorschau konnte nicht erzeugt werden.')
  } finally {
    if (requestId === latestPreviewRequest) loadingThumbs.value = false
  }
}

function reset(): void {
  latestPreviewRequest += 1
  file.value = null
  thumbnails.value = {}
  pageOrder.value = []
  deletedPages.clear()
  loadingThumbs.value = false
  uploadError.value = ''
  error.value = null
}

function toggleDelete(page: number): void {
  if (deletedPages.has(page)) deletedPages.delete(page)
  else deletedPages.add(page)
}

function restoreAll(): void {
  deletedPages.clear()
}

function reorder(targetIndex: number): void {
  if (dragIndex.value < 0 || dragIndex.value === targetIndex) return
  const [page] = pageOrder.value.splice(dragIndex.value, 1)
  if (page !== undefined) pageOrder.value.splice(targetIndex, 0, page)
  dragIndex.value = -1
}

async function doApply(): Promise<void> {
  if (!file.value) return
  await withLoading(() => pageOperations(file.value!, activePages.value))
}
</script>
