<template>
  <div class="space-y-5">
    <ToolHeader title="PDF teilen" description="Ein Dokument nach Bereichen oder in festen Abständen aufteilen." @back="$emit('back')" />

    <UiDropZone :accepted="Boolean(file)" :invalid="Boolean(uploadError)" @drop="onDroppedFiles">
      <input ref="fileInput" type="file" accept=".pdf,application/pdf" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-2xl text-violet-700 dark:bg-violet-400/15 dark:text-violet-300" aria-hidden="true">✂</div>
        <p class="mt-3 font-semibold text-gray-950 dark:text-white">PDF zum Teilen auswählen</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Datei hierher ziehen oder lokal öffnen.</p>
        <UiButton variant="primary" class="mt-4" @click="fileInput?.click()">Datei auswählen</UiButton>
      </div>
      <div v-else>
        <p class="break-all font-semibold text-gray-950 dark:text-white">{{ file.name }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ pageCount || '…' }} Seiten</p>
        <UiButton variant="danger" size="sm" class="mt-3" @click="resetFile">Entfernen</UiButton>
      </div>
    </UiDropZone>

    <UiAlert v-if="uploadError" tone="danger">{{ uploadError }}</UiAlert>

    <UiPanel v-if="file" as="section" class="space-y-4">
      <fieldset>
        <legend class="mb-3 text-sm font-semibold text-gray-800 dark:text-gray-100">Teilungsmethode</legend>
        <div class="flex flex-wrap gap-3">
          <label class="flex cursor-pointer items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-sm font-medium dark:bg-white/10">
            <input v-model="mode" type="radio" value="ranges" class="text-primary-600" /> Seitenbereiche
          </label>
          <label class="flex cursor-pointer items-center gap-2 rounded-full bg-gray-100 px-4 py-2 text-sm font-medium dark:bg-white/10">
            <input v-model="mode" type="radio" value="every_n" class="text-primary-600" /> Alle N Seiten
          </label>
        </div>
      </fieldset>

      <UiField
        v-if="mode === 'ranges'"
        label="Bereiche, getrennt durch Semikolon"
        for-id="split-ranges"
        hint="Jeder Bereich wird als separate Datei erzeugt."
      >
        <input id="split-ranges" v-model="ranges" type="text" class="ui-control w-full" placeholder="z. B. 1-3; 4-6; 7-10" />
      </UiField>

      <UiField
        v-else
        label="Nach wie vielen Seiten teilen?"
        for-id="split-every-n"
        :hint="`Ergibt voraussichtlich ${Math.ceil(pageCount / Math.max(1, everyN))} Dateien.`"
      >
        <input id="split-every-n" v-model.number="everyN" type="number" min="1" :max="pageCount" class="ui-control w-36" />
      </UiField>
    </UiPanel>

    <!--
      Der Schlüssel erzwingt beim Dokumentwechsel eine neue Instanz des Rasters.
      Zusätzlich wird der alte Thumbnail-State vor dem neuen Netzwerkaufruf
      geleert. Ein monotoner Request-Zähler verhindert, dass eine langsamere
      Antwort der vorherigen Datei den aktuellen Zustand überschreibt.
    -->
    <PageThumbnailGrid
      v-if="loadingThumbs || Object.keys(thumbnails).length > 0"
      :key="previewGeneration"
      :thumbnails="thumbnails"
      :loading="loadingThumbs"
    />

    <UiButton
      v-if="file"
      variant="primary"
      size="lg"
      :loading="loading"
      :disabled="mode === 'ranges' && !ranges.trim()"
      @click="doSplit"
    >{{ loading ? 'PDF wird geteilt…' : 'PDF teilen' }}</UiButton>

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
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { validatePdfFile } from '@/lib/fileValidation'
import PageThumbnailGrid from './PageThumbnailGrid.vue'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, splitPdf, getThumbnails } = usePdfTools()
const notifications = useNotifications()
const file = ref<File | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const pageCount = ref(0)
const mode = ref<'ranges' | 'every_n'>('ranges')
const ranges = ref('')
const everyN = ref(1)
const thumbnails = ref<Record<string, string>>({})
const loadingThumbs = ref(false)
const uploadError = ref('')
const previewGeneration = ref(0)
let latestPreviewRequest = 0

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

async function setFile(selected: File): Promise<void> {
  const validation = await validatePdfFile(selected)
  if (!validation.valid) {
    uploadError.value = validation.message ?? 'Die PDF-Datei ist ungültig.'
    notifications.error('Datei nicht angenommen', uploadError.value)
    return
  }

  // Alter Dokumentzustand wird synchron verworfen, bevor die neue Vorschau lädt.
  const requestId = ++latestPreviewRequest
  file.value = selected
  thumbnails.value = {}
  pageCount.value = 0
  ranges.value = ''
  everyN.value = 1
  uploadError.value = ''
  error.value = null
  loadingThumbs.value = true
  previewGeneration.value += 1

  try {
    const data = await getThumbnails(selected) as { thumbnails: Record<string, string>; count: number }
    if (requestId !== latestPreviewRequest || file.value !== selected) return
    thumbnails.value = data.thumbnails
    pageCount.value = data.count
    notifications.success('Vorschau geladen', `${selected.name} enthält ${data.count} Seiten.`)
  } catch (previewError: unknown) {
    if (requestId !== latestPreviewRequest) return
    thumbnails.value = {}
    pageCount.value = 0
    uploadError.value = notifications.errorFromUnknown(previewError, 'Die PDF-Vorschau konnte nicht erzeugt werden.')
  } finally {
    if (requestId === latestPreviewRequest) loadingThumbs.value = false
  }
}

function resetFile(): void {
  latestPreviewRequest += 1
  file.value = null
  thumbnails.value = {}
  pageCount.value = 0
  ranges.value = ''
  everyN.value = 1
  loadingThumbs.value = false
  uploadError.value = ''
  error.value = null
  previewGeneration.value += 1
}

async function doSplit(): Promise<void> {
  if (!file.value) return
  await withLoading(() => splitPdf(file.value!, mode.value, ranges.value.trim() || undefined, everyN.value))
}
</script>
