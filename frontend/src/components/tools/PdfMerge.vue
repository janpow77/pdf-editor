<template>
  <div class="space-y-5">
    <ToolHeader
      title="PDFs zusammenführen"
      description="Mehrere Dokumente mit stabiler Vorschauzuordnung in eine Reihenfolge bringen."
      @back="$emit('back')"
    />

    <UiDropZone
      :active="isDragging"
      :invalid="Boolean(uploadError)"
      @drag-active="isDragging = $event"
      @drop="onDroppedFiles"
    >
      <input ref="fileInput" type="file" accept=".pdf,application/pdf" multiple class="hidden" @change="onFileSelect" />
      <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-2xl text-violet-700 dark:bg-violet-400/15 dark:text-violet-300" aria-hidden="true">📎</div>
      <p class="mt-3 font-semibold text-gray-950 dark:text-white">PDF-Dateien ablegen</p>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Die Reihenfolge kann per Drag & Drop oder mit den Pfeiltasten geändert werden.</p>
      <UiButton variant="primary" class="mt-4" @click="fileInput?.click()">Dateien auswählen</UiButton>
    </UiDropZone>

    <UiAlert v-if="uploadError" tone="danger">{{ uploadError }}</UiAlert>

    <section v-if="items.length" class="space-y-3" aria-labelledby="merge-files-heading">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 id="merge-files-heading" class="font-semibold text-gray-950 dark:text-white">{{ items.length }} Dateien ausgewählt</h3>
          <p class="text-sm text-gray-600 dark:text-gray-300">Die erste Seite jeder PDF wird als Vorschau dargestellt.</p>
        </div>
        <UiButton variant="danger" size="sm" @click="clearFiles">Alle entfernen</UiButton>
      </div>

      <ol class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <UiPanel
          v-for="(item, index) in items"
          :key="item.id"
          as="li"
          padding="sm"
          class="group relative grid min-h-48 grid-cols-[8rem,1fr] gap-4 transition hover:-translate-y-0.5 hover:shadow-apple"
          draggable="true"
          @dragstart="dragIdx = index"
          @dragover.prevent
          @drop.prevent="reorderFile(index)"
        >
          <div class="relative flex min-h-40 items-center justify-center overflow-hidden rounded-2xl bg-gray-100 shadow-inner dark:bg-black/30">
            <img v-if="item.thumbnail" :src="`data:image/png;base64,${item.thumbnail}`" :alt="`Vorschau der ersten Seite von ${item.file.name}`" class="h-full w-full bg-white object-contain" />
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
            <UiAlert v-if="item.previewError" tone="danger" class="mt-2 !px-3 !py-2 text-xs">{{ item.previewError }}</UiAlert>

            <div class="mt-auto flex flex-wrap items-center justify-between gap-2 pt-4">
              <span class="cursor-grab text-xs font-semibold text-gray-500 dark:text-gray-400" title="Zum Umsortieren ziehen">☰ Verschieben</span>
              <div class="flex items-center gap-1">
                <UiIconButton
                  size="sm"
                  :disabled="index === 0"
                  :aria-label="`${item.file.name} nach oben verschieben`"
                  @click="moveItem(index, -1)"
                >↑</UiIconButton>
                <UiIconButton
                  size="sm"
                  :disabled="index === items.length - 1"
                  :aria-label="`${item.file.name} nach unten verschieben`"
                  @click="moveItem(index, 1)"
                >↓</UiIconButton>
                <UiIconButton variant="danger" size="sm" :aria-label="`${item.file.name} entfernen`" @click="removeItem(item.id)">×</UiIconButton>
              </div>
            </div>
          </div>
        </UiPanel>
      </ol>
    </section>

    <div class="flex flex-wrap items-center gap-3">
      <UiButton
        variant="primary"
        size="lg"
        :loading="loading"
        :disabled="items.length < 2"
        @click="doMerge"
      >{{ loading ? 'PDFs werden zusammengeführt…' : 'PDFs zusammenführen' }}</UiButton>
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
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { formatFileSize, validatePdfFile, validateTotalFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

interface MergeItem {
  id: string
  file: File
  thumbnail: string
  loading: boolean
  previewError: string
}

const MAX_FILES = 50
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

function onDroppedFiles(files: File[]): void {
  if (files.length) void addFiles(files)
}

/**
 * Jede Datei wird einzeln validiert. Erst wenn auch Anzahl und gemeinsame
 * Größengrenze eingehalten sind, werden Listeneinträge angelegt und ihre
 * Vorschauen parallel geladen. Die ID bleibt beim Umsortieren stabil.
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

  if (items.value.length + accepted.length > MAX_FILES) {
    uploadError.value = `Es können maximal ${MAX_FILES} PDF-Dateien gleichzeitig zusammengeführt werden.`
    notifications.error('Zu viele Dateien', uploadError.value)
    return
  }

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

/** Tastaturbedienbare Alternative zum Drag-&-Drop. */
function moveItem(index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [item] = items.value.splice(index, 1)
  if (item) items.value.splice(target, 0, item)
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
