<template>
  <div class="space-y-5">
    <div class="flex items-center gap-3">
      <button type="button" class="rounded-full px-3 py-2 text-sm font-semibold text-gray-600 hover:bg-black/5 hover:text-primary-700 dark:text-gray-300 dark:hover:bg-white/10 dark:hover:text-primary-300" @click="$emit('back')">← Zurück</button>
      <h2 class="text-xl font-semibold tracking-[-0.025em] text-gray-950 dark:text-white">PDFs zusammenführen</h2>
    </div>

    <div
      class="apple-upload-zone p-7 text-center"
      :class="uploadError ? 'border-rose-500 bg-rose-50/70 dark:bg-rose-500/10' : isDragging ? 'border-primary-500 bg-primary-50/80 dark:bg-primary-500/10' : ''"
      @dragover.prevent="isDragging = true"
      @dragleave="isDragging = false"
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".pdf,application/pdf" multiple class="hidden" @change="onFileSelect" />
      <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-2xl text-violet-700 dark:bg-violet-400/15 dark:text-violet-300" aria-hidden="true">📎</div>
      <p class="mt-3 font-semibold text-gray-950 dark:text-white">PDF-Dateien ablegen</p>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Die Reihenfolge kann anschließend per Drag & Drop geändert werden.</p>
      <button type="button" class="mt-4 rounded-full bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 hover:shadow-apple" @click="fileInput?.click()">Dateien auswählen</button>
    </div>

    <p v-if="uploadError" class="apple-inline-error text-sm" role="alert">{{ uploadError }}</p>

    <section v-if="items.length" class="space-y-3" aria-labelledby="merge-files-heading">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 id="merge-files-heading" class="font-semibold text-gray-950 dark:text-white">{{ items.length }} Dateien ausgewählt</h3>
          <p class="text-sm text-gray-600 dark:text-gray-300">Die erste Seite jeder PDF wird als Vorschau dargestellt.</p>
        </div>
        <button type="button" class="rounded-full px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10" @click="clearFiles">Alle entfernen</button>
      </div>

      <ol class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <li
          v-for="(item, index) in items"
          :key="item.id"
          class="group relative grid min-h-48 grid-cols-[8rem,1fr] gap-4 rounded-[1.35rem] bg-white/85 p-3 shadow-apple-sm ring-1 ring-gray-300/80 transition hover:-translate-y-0.5 hover:shadow-apple dark:bg-white/[0.07] dark:ring-gray-600"
          draggable="true"
          @dragstart="dragIdx = index"
          @dragover.prevent
          @drop.prevent="reorderFile(index)"
        >
          <div class="relative flex min-h-40 items-center justify-center overflow-hidden rounded-2xl bg-gray-100 shadow-inner dark:bg-black/30">
            <img v-if="item.thumbnail" :src="`data:image/png;base64,${item.thumbnail}`" :alt="`Vorschau der ersten Seite von ${item.file.name}`" class="h-full w-full object-contain bg-white" />
            <div v-else-if="item.loading" class="flex flex-col items-center gap-2 text-sm font-medium text-gray-600 dark:text-gray-300" role="status">
              <span class="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
              Vorschau…
            </div>
            <div v-else class="px-3 text-center text-sm text-gray-600 dark:text-gray-300">Keine Vorschau</div>
            <span class="absolute left-2 top-2 rounded-full bg-gray-950/80 px-2 py-1 text-xs font-semibold text-white">{{ index + 1 }}</span>
          </div>

          <div class="flex min-w-0 flex-col py-1">
            <span class="text-xs font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">PDF-Dokument</span>
            <p class="mt-2 break-all text-sm font-semibold leading-5 text-gray-950 dark:text-white">{{ item.file.name }}</p>
            <p class="mt-1 text-xs text-gray-600 dark:text-gray-300">{{ formatFileSize(item.file.size) }}</p>
            <p v-if="item.previewError" class="mt-2 text-xs leading-5 text-rose-700 dark:text-rose-300">{{ item.previewError }}</p>

            <div class="mt-auto flex items-center justify-between gap-2 pt-4">
              <span class="cursor-grab text-xs font-semibold text-gray-500 dark:text-gray-400" title="Zum Umsortieren ziehen">☰ Verschieben</span>
              <button type="button" class="grid h-9 w-9 place-items-center rounded-full text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10" :aria-label="`${item.file.name} entfernen`" @click="removeItem(item.id)">×</button>
            </div>
          </div>
        </li>
      </ol>
    </section>

    <div class="flex flex-wrap items-center gap-3">
      <button
        type="button"
        :disabled="items.length < 2 || loading"
        class="rounded-full bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-apple disabled:cursor-not-allowed disabled:opacity-45"
        @click="doMerge"
      >{{ loading ? 'PDFs werden zusammengeführt…' : 'PDFs zusammenführen' }}</button>
      <span v-if="items.length === 1" class="text-sm font-medium text-amber-700 dark:text-amber-300">Mindestens zwei Dateien erforderlich.</span>
    </div>

    <p v-if="error" class="apple-inline-error text-sm" role="alert">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { formatFileSize, validatePdfFile, validateTotalFileSize } from '@/lib/fileValidation'

defineEmits<{ (e: 'back'): void }>()

interface MergeItem {
  id: string
  file: File
  thumbnail: string
  loading: boolean
  previewError: string
}

const { loading, error, withLoading, mergePdfs, getThumbnails } = usePdfTools()
const notifications = useNotifications()
const items = ref<MergeItem[]>([])
const isDragging = ref(false)
const dragIdx = ref(-1)
const fileInput = ref<HTMLInputElement | null>(null)
const uploadError = ref('')
let nextId = 1

function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  const selected = Array.from(input.files ?? [])
  input.value = ''
  if (selected.length) void addFiles(selected)
}

function onDrop(event: DragEvent): void {
  isDragging.value = false
  const selected = Array.from(event.dataTransfer?.files ?? [])
  if (selected.length) void addFiles(selected)
}

/**
 * Jede Datei wird einzeln validiert. Erst wenn auch die gemeinsame Größen-
 * grenze eingehalten ist, werden Listeneinträge angelegt und ihre Vorschauen
 * parallel geladen. Die ID bleibt beim Umsortieren stabil.
 */
async function addFiles(selectedFiles: File[]): Promise<void> {
  uploadError.value = ''
  const accepted: File[] = []
  const rejected: string[] = []

  for (const file of selectedFiles) {
    const result = await validatePdfFile(file)
    if (result.valid) accepted.push(file)
    else rejected.push(`${file.name}: ${result.message ?? 'ungültige PDF-Datei'}`)
  }

  if (rejected.length) {
    uploadError.value = rejected.join(' ')
    notifications.error('Einige Dateien wurden abgelehnt', uploadError.value)
  }
  if (!accepted.length) return

  const combinedFiles = [...items.value.map((item) => item.file), ...accepted]
  const totalValidation = validateTotalFileSize(combinedFiles)
  if (!totalValidation.valid) {
    uploadError.value = totalValidation.message ?? 'Die zulässige Gesamtgröße wurde überschritten.'
    notifications.error('Gesamtgröße überschritten', uploadError.value)
    return
  }

  const newItems = accepted.map<MergeItem>((file) => ({
    id: `merge-${Date.now()}-${nextId++}`,
    file,
    thumbnail: '',
    loading: true,
    previewError: '',
  }))
  items.value.push(...newItems)
  notifications.success('Dateien hinzugefügt', `${accepted.length} PDF-Datei(en) wurden übernommen.`)

  await Promise.all(newItems.map((item) => loadPreview(item)))
}

async function loadPreview(item: MergeItem): Promise<void> {
  try {
    const data = await getThumbnails(item.file, '1') as { thumbnails: Record<string, string> }
    const current = items.value.find((entry) => entry.id === item.id)
    if (!current) return
    current.thumbnail = data.thumbnails['1'] ?? ''
    current.previewError = current.thumbnail ? '' : 'Die erste Seite konnte nicht dargestellt werden.'
  } catch (previewError: unknown) {
    const current = items.value.find((entry) => entry.id === item.id)
    if (!current) return
    current.previewError = notifications.errorFromUnknown(previewError, 'Vorschau nicht verfügbar.')
  } finally {
    const current = items.value.find((entry) => entry.id === item.id)
    if (current) current.loading = false
  }
}

function removeItem(id: string): void {
  items.value = items.value.filter((item) => item.id !== id)
  uploadError.value = ''
}

function clearFiles(): void {
  items.value = []
  uploadError.value = ''
}

function reorderFile(targetIdx: number): void {
  if (dragIdx.value < 0 || dragIdx.value === targetIdx) return
  const [item] = items.value.splice(dragIdx.value, 1)
  if (item) items.value.splice(targetIdx, 0, item)
  dragIdx.value = -1
}

async function doMerge(): Promise<void> {
  if (items.value.length < 2) return
  await withLoading(() => mergePdfs(items.value.map((item) => item.file)))
}
</script>
