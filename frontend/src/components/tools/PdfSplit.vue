<template>
  <div class="space-y-5">
    <div class="flex items-center gap-3">
      <button type="button" class="rounded-full px-3 py-2 text-sm font-semibold text-gray-600 hover:bg-black/5 hover:text-primary-700 dark:text-gray-300 dark:hover:bg-white/10 dark:hover:text-primary-300" @click="$emit('back')">← Zurück</button>
      <h2 class="text-xl font-semibold tracking-[-0.025em] text-gray-950 dark:text-white">PDF teilen</h2>
    </div>

    <div
      class="apple-upload-zone p-7 text-center"
      :class="uploadError ? 'border-rose-500 bg-rose-50/70 dark:bg-rose-500/10' : file ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-500/10' : ''"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".pdf,application/pdf" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-2xl text-violet-700 dark:bg-violet-400/15 dark:text-violet-300" aria-hidden="true">✂</div>
        <p class="mt-3 font-semibold text-gray-950 dark:text-white">PDF zum Teilen auswählen</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Datei hierher ziehen oder lokal öffnen.</p>
        <button type="button" class="mt-4 rounded-full bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary-700 hover:shadow-apple" @click="fileInput?.click()">Datei auswählen</button>
      </div>
      <div v-else>
        <p class="break-all font-semibold text-gray-950 dark:text-white">{{ file.name }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ pageCount || '…' }} Seiten</p>
        <button type="button" class="mt-2 rounded-full px-4 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10" @click="resetFile">Entfernen</button>
      </div>
    </div>

    <p v-if="uploadError" class="apple-inline-error text-sm" role="alert">{{ uploadError }}</p>

    <section v-if="file" class="apple-surface space-y-4 p-5">
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

      <div v-if="mode === 'ranges'">
        <label for="split-ranges" class="mb-1 block text-sm font-semibold text-gray-700 dark:text-gray-200">Bereiche, getrennt durch Semikolon</label>
        <input id="split-ranges" v-model="ranges" type="text" class="w-full rounded-2xl bg-white px-4 py-3 text-gray-950 shadow-sm ring-1 ring-gray-400 focus:ring-2 focus:ring-primary-500 dark:bg-white/10 dark:text-white dark:ring-gray-600" placeholder="z. B. 1-3; 4-6; 7-10" />
        <p class="mt-1 text-xs text-gray-600 dark:text-gray-400">Jeder Bereich wird als separate Datei erzeugt.</p>
      </div>

      <div v-else>
        <label for="split-every-n" class="mb-1 block text-sm font-semibold text-gray-700 dark:text-gray-200">Nach wie vielen Seiten teilen?</label>
        <input id="split-every-n" v-model.number="everyN" type="number" min="1" :max="pageCount" class="w-36 rounded-2xl bg-white px-4 py-3 text-gray-950 shadow-sm ring-1 ring-gray-400 focus:ring-2 focus:ring-primary-500 dark:bg-white/10 dark:text-white dark:ring-gray-600" />
        <p class="mt-1 text-xs text-gray-600 dark:text-gray-400">Ergibt voraussichtlich {{ Math.ceil(pageCount / Math.max(1, everyN)) }} Dateien.</p>
      </div>
    </section>

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

    <button
      v-if="file"
      type="button"
      :disabled="loading || (mode === 'ranges' && !ranges.trim())"
      class="rounded-full bg-primary-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-apple disabled:cursor-not-allowed disabled:opacity-45"
      @click="doSplit"
    >{{ loading ? 'PDF wird geteilt…' : 'PDF teilen' }}</button>

    <p v-if="error" class="apple-inline-error text-sm" role="alert">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { validatePdfFile } from '@/lib/fileValidation'
import PageThumbnailGrid from './PageThumbnailGrid.vue'

defineEmits<{ (e: 'back'): void }>()

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

function onDrop(event: DragEvent): void {
  const selected = event.dataTransfer?.files?.[0]
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
