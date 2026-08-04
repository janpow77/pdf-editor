<template>
  <div class="space-y-5">
    <ToolHeader title="Bild ersetzen" description="Ein eingebettetes Bild austauschen, ohne dessen Position und Größe im PDF zu verändern." @back="$emit('back')" />
    <UiAlert tone="info">Geeignet für Logos und Grafiken. Das neue Bild sollte dasselbe Seitenverhältnis besitzen.</UiAlert>

    <FileDrop v-model="file" />

    <div v-if="loadingList" class="flex items-center justify-center gap-3 py-6" role="status">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="text-sm text-gray-600 dark:text-gray-300">Eingebettete Bilder werden gesucht…</span>
    </div>

    <UiPanel v-if="images.length" class="space-y-4">
      <h3 class="font-semibold">{{ images.length }} Bild(er) gefunden – eines auswählen</h3>
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        <button
          v-for="imageEntry in images"
          :key="imageEntry.xref"
          type="button"
          class="rounded-2xl p-2 text-left shadow-apple-sm ring-2 transition hover:-translate-y-0.5 hover:shadow-apple"
          :class="selected === imageEntry.xref ? 'bg-primary-50 ring-primary-500 dark:bg-primary-500/15' : 'bg-white ring-gray-300 dark:bg-white/5 dark:ring-gray-600'"
          :aria-pressed="selected === imageEntry.xref"
          @click="selectImage(imageEntry.xref)"
        >
          <img v-if="imageEntry.preview" :src="`data:image/png;base64,${imageEntry.preview}`" :alt="`Bild auf Seite ${imageEntry.page}`" class="h-36 w-full rounded-xl bg-gray-100 object-contain dark:bg-black/30" />
          <div v-else class="flex h-36 items-center justify-center rounded-xl bg-gray-100 text-sm text-gray-600 dark:bg-black/30 dark:text-gray-300">Keine Vorschau</div>
          <p class="mt-2 text-sm font-semibold">Seite {{ imageEntry.page }}</p>
          <p class="text-xs text-gray-600 dark:text-gray-400">{{ imageEntry.width }} × {{ imageEntry.height }} px</p>
        </button>
      </div>
    </UiPanel>

    <UiAlert v-if="file && !loadingList && listLoaded && !images.length" tone="warning">Dieses PDF enthält keine austauschbaren Bilder.</UiAlert>

    <FileDrop v-if="selected !== null" v-model="newImage" accept=".png,.jpg,.jpeg,image/png,image/jpeg" label="Neues Bild (PNG/JPEG)" />

    <UiAlert v-if="done" tone="success" live>Bild ersetzt und PDF heruntergeladen.</UiAlert>
    <UiButton v-if="selected !== null && newImage" variant="primary" size="lg" :loading="loading" @click="apply">{{ loading ? 'Ersetze…' : 'Bild ersetzen' }}</UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiPost } from '@/lib/api'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (event: 'back'): void }>()

interface PdfImage { xref: number; page: number; width: number; height: number; preview: string }

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const images = ref<PdfImage[]>([])
const selected = ref<number | null>(null)
const newImage = ref<File | null>(null)
const loadingList = ref(false)
const listLoaded = ref(false)
let generation = 0
let controller: AbortController | null = null

function normalizeImages(value: unknown): PdfImage[] {
  const source = value && typeof value === 'object' && 'images' in value ? (value as { images?: unknown }).images : []
  if (!Array.isArray(source)) return []
  return source.slice(0, 1000).flatMap((entry) => {
    if (!entry || typeof entry !== 'object') return []
    const raw = entry as Record<string, unknown>
    const xref = Number(raw.xref); const page = Number(raw.page); const width = Number(raw.width); const height = Number(raw.height)
    if (![xref, page, width, height].every(Number.isFinite) || xref < 0 || page < 1) return []
    return [{ xref: Math.trunc(xref), page: Math.trunc(page), width: Math.max(0, Math.trunc(width)), height: Math.max(0, Math.trunc(height)), preview: typeof raw.preview === 'string' ? raw.preview : '' }]
  })
}

watch(file, async (currentFile) => {
  const currentGeneration = ++generation
  controller?.abort(); controller = null
  images.value = []; selected.value = null; newImage.value = null; listLoaded.value = false; loadingList.value = false
  done.value = false; error.value = null
  if (!currentFile) return

  const requestController = new AbortController(); controller = requestController; loadingList.value = true
  try {
    const formData = new FormData(); formData.append('file', currentFile)
    const response = await apiPost('/api/pdf-more/images/list', formData, { signal: requestController.signal, notifyOnError: false })
    const normalized = normalizeImages(await response.json())
    if (currentGeneration !== generation || file.value !== currentFile) return
    images.value = normalized
  } catch (caught: unknown) {
    if (!requestController.signal.aborted && currentGeneration === generation) error.value = caught instanceof Error ? caught.message : 'Bilder konnten nicht gelesen werden.'
  } finally {
    if (currentGeneration === generation) { loadingList.value = false; listLoaded.value = true }
    if (controller === requestController) controller = null
  }
})
watch([selected, newImage], () => { done.value = false; error.value = null })

function selectImage(xref: number): void { selected.value = xref; newImage.value = null }

async function apply(): Promise<void> {
  const currentFile = file.value; const currentImage = newImage.value; const xref = selected.value
  if (!currentFile || !currentImage || xref === null) return
  const currentGeneration = generation
  const formData = new FormData(); formData.append('file', currentFile); formData.append('xref', String(xref)); formData.append('image', currentImage)
  await run('/api/pdf-more/images/replace', formData, currentFile.name.replace(/\.pdf$/i, '_bild.pdf'))
  if (currentGeneration !== generation) done.value = false
}

onBeforeUnmount(() => { generation += 1; controller?.abort() })
</script>
