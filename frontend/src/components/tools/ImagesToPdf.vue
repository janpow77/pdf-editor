<template>
  <div class="space-y-5">
    <ToolHeader
      title="Bilder zu PDF"
      description="Bilddateien in stabiler Reihenfolge zu einem PDF-Dokument bündeln."
      @back="$emit('back')"
    />

    <UiDropZone
      :active="isDragging"
      :invalid="Boolean(uploadError)"
      @drag-active="isDragging = $event"
      @drop="onDroppedFiles"
    >
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/gif,image/bmp,image/tiff,image/webp" multiple class="hidden" @change="onFileSelect" />
      <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-emerald-100 text-2xl text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300" aria-hidden="true">🖼️</div>
      <p class="mt-3 font-semibold text-gray-950 dark:text-white">Bilder ablegen</p>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">PNG, JPEG, GIF, BMP, TIFF oder WebP – Reihenfolge anschließend frei ändern.</p>
      <UiButton variant="primary" class="mt-4" @click="fileInput?.click()">Bilder auswählen</UiButton>
    </UiDropZone>

    <UiAlert v-if="uploadError" tone="danger">{{ uploadError }}</UiAlert>

    <section v-if="items.length" class="space-y-3" aria-labelledby="image-list-heading">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 id="image-list-heading" class="font-semibold text-gray-950 dark:text-white">{{ items.length }} Bilder</h3>
          <p class="text-sm text-gray-600 dark:text-gray-300">Ziehen oder mit den Pfeiltasten verschieben.</p>
        </div>
        <UiButton variant="danger" size="sm" @click="clearItems">Alle entfernen</UiButton>
      </div>

      <!--
        Das frühere Acht-Spalten-Raster machte Vorschauen auf Desktop sehr klein.
        Vier Spalten verdoppeln die sichtbare Fläche ungefähr und erfüllen damit
        die globale Vorgabe von mindestens 50 Prozent größeren Vorschauen.
      -->
      <ol class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        <UiPanel
          v-for="(item, index) in items"
          :key="item.id"
          as="li"
          padding="sm"
          class="group overflow-hidden transition hover:-translate-y-0.5 hover:shadow-apple"
          draggable="true"
          @dragstart="dragIndex = index"
          @dragover.prevent
          @drop.prevent="reorder(index)"
        >
          <div class="relative aspect-[4/3] overflow-hidden rounded-xl bg-gray-100 dark:bg-black/30">
            <img :src="item.previewUrl" :alt="`Vorschau von ${item.file.name}`" class="h-full w-full object-contain" />
            <span class="absolute left-2 top-2 rounded-full bg-gray-950/80 px-2 py-1 text-xs font-semibold text-white">{{ index + 1 }}</span>
          </div>

          <div class="space-y-3 pt-3">
            <div>
              <p class="break-all text-sm font-semibold leading-5 text-gray-950 dark:text-white">{{ item.file.name }}</p>
              <p class="mt-1 text-xs text-gray-600 dark:text-gray-300">{{ formatFileSize(item.file.size) }}</p>
            </div>
            <div class="flex items-center justify-between gap-2">
              <div class="flex gap-1">
                <UiIconButton size="sm" :disabled="index === 0" :aria-label="`${item.file.name} nach vorne verschieben`" @click="moveItem(index, -1)">←</UiIconButton>
                <UiIconButton size="sm" :disabled="index === items.length - 1" :aria-label="`${item.file.name} nach hinten verschieben`" @click="moveItem(index, 1)">→</UiIconButton>
              </div>
              <UiIconButton variant="danger" size="sm" :aria-label="`${item.file.name} entfernen`" @click="removeItem(item.id)">×</UiIconButton>
            </div>
          </div>
        </UiPanel>
      </ol>
    </section>

    <UiPanel v-if="items.length" as="section" aria-labelledby="image-pdf-options">
      <h3 id="image-pdf-options" class="mb-4 font-semibold text-gray-950 dark:text-white">Seiteneinstellungen</h3>
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Seitengröße" for-id="image-page-size">
          <select id="image-page-size" v-model="pageSize" class="ui-control w-full">
            <option value="a4">A4</option>
            <option value="a3">A3</option>
            <option value="letter">Letter</option>
            <option value="legal">Legal</option>
          </select>
        </UiField>
        <UiField label="Ausrichtung" for-id="image-orientation">
          <select id="image-orientation" v-model="orientation" class="ui-control w-full">
            <option value="portrait">Hochformat</option>
            <option value="landscape">Querformat</option>
          </select>
        </UiField>
      </div>
    </UiPanel>

    <UiButton v-if="items.length" variant="primary" size="lg" :loading="loading" @click="doConvert">
      {{ loading ? 'PDF wird erstellt…' : 'PDF erstellen' }}
    </UiButton>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiField from '@/components/ui/UiField.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { currentFileLimit, currentTotalLimit, formatFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

interface ImageItem {
  id: string
  file: File
  previewUrl: string
}

const MAX_IMAGES = 100
const { loading, error, withLoading, imagesToPdf } = usePdfTools()
const notifications = useNotifications()
const items = ref<ImageItem[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const dragIndex = ref(-1)
const pageSize = ref('a4')
const orientation = ref('portrait')
const uploadError = ref('')
let nextId = 1

const imageExtensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp']

function isSupportedImage(file: File): boolean {
  const extensionAllowed = imageExtensions.some((extension) => file.name.toLowerCase().endsWith(extension))
  const mimeAllowed = !file.type || file.type.startsWith('image/')
  return extensionAllowed && mimeAllowed
}

function onFileSelect(event: Event): void {
  const input = event.target as HTMLInputElement
  const selected = Array.from(input.files ?? [])
  input.value = ''
  if (selected.length) addItems(selected)
}

function onDroppedFiles(files: File[]): void {
  if (files.length) addItems(files)
}

/** Prüft Dateityp, Anzahl sowie Einzel- und Gesamtgröße vor den Object-URLs. */
function addItems(selected: File[]): void {
  uploadError.value = ''
  const accepted: File[] = []
  const rejected: string[] = []
  const fileLimit = currentFileLimit()
  const freeSlots = Math.max(0, MAX_IMAGES - items.value.length)

  for (const [index, file] of selected.entries()) {
    if (index >= freeSlots) rejected.push(`${file.name}: Maximum von ${MAX_IMAGES} Bildern erreicht`)
    else if (!isSupportedImage(file)) rejected.push(`${file.name}: nicht unterstütztes Bildformat`)
    else if (file.size > fileLimit) rejected.push(`${file.name}: größer als ${formatFileSize(fileLimit)}`)
    else accepted.push(file)
  }

  const combinedSize = [...items.value.map((item) => item.file), ...accepted]
    .reduce((sum, file) => sum + file.size, 0)
  if (combinedSize > currentTotalLimit()) {
    uploadError.value = `Die Gesamtgröße beträgt ${formatFileSize(combinedSize)}. Zulässig sind maximal ${formatFileSize(currentTotalLimit())}.`
    notifications.error('Gesamtgröße überschritten', uploadError.value)
    return
  }

  for (const file of accepted) {
    items.value.push({
      id: `image-${Date.now()}-${nextId++}`,
      file,
      previewUrl: URL.createObjectURL(file),
    })
  }

  if (rejected.length) {
    uploadError.value = rejected.join(' ')
    notifications.warning('Einige Bilder wurden abgelehnt', uploadError.value)
  }
  if (accepted.length) notifications.success('Bilder hinzugefügt', `${accepted.length} Bilddatei(en) wurden übernommen.`)
}

function removeItem(id: string): void {
  const index = items.value.findIndex((item) => item.id === id)
  if (index < 0) return
  URL.revokeObjectURL(items.value[index].previewUrl)
  items.value.splice(index, 1)
}

function clearItems(): void {
  items.value.forEach((item) => URL.revokeObjectURL(item.previewUrl))
  items.value = []
  uploadError.value = ''
}

function reorder(targetIndex: number): void {
  if (dragIndex.value < 0 || dragIndex.value === targetIndex) return
  const [item] = items.value.splice(dragIndex.value, 1)
  if (item) items.value.splice(targetIndex, 0, item)
  dragIndex.value = -1
}

function moveItem(index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [item] = items.value.splice(index, 1)
  if (item) items.value.splice(target, 0, item)
}

async function doConvert(): Promise<void> {
  await withLoading(() => imagesToPdf(items.value.map((item) => item.file), pageSize.value, orientation.value))
}

onBeforeUnmount(() => {
  items.value.forEach((item) => URL.revokeObjectURL(item.previewUrl))
})
</script>
