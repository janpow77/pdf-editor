<template>
  <div class="space-y-5">
    <ToolHeader title="Bild ersetzen" description="Ein vorhandenes PDF-Bild austauschen, ohne Position oder Größe zu verändern." @back="$emit('back')" />

    <UiAlert tone="info">Geeignet zum Aktualisieren von Logos und Grafiken. Für zusätzliche Bilder stehen Unterschrift und Wasserzeichen bereit.</UiAlert>

    <FileDrop v-model="file" />

    <div v-if="loadingList" class="flex items-center gap-2 py-4 text-sm text-gray-600 dark:text-gray-300" role="status">
      <span class="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      Bilder werden gesucht…
    </div>

    <UiPanel v-if="images.length" class="space-y-3">
      <h3 class="font-semibold text-gray-950 dark:text-white">{{ images.length }} Bilder gefunden</h3>
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        <UiPanel
          v-for="imageEntry in images"
          :key="imageEntry.xref"
          as="button"
          type="button"
          padding="sm"
          class="text-left transition hover:-translate-y-0.5 hover:shadow-apple"
          :class="selected === imageEntry.xref ? 'ring-2 ring-primary-500' : ''"
          :aria-pressed="selected === imageEntry.xref"
          @click="selected = imageEntry.xref"
        >
          <img
            v-if="imageEntry.preview"
            :src="`data:image/png;base64,${imageEntry.preview}`"
            class="h-36 w-full rounded-xl bg-gray-100 object-contain dark:bg-black/30"
            :alt="`Bild auf Seite ${imageEntry.page}`"
          />
          <div v-else class="flex h-36 w-full items-center justify-center rounded-xl bg-gray-100 text-xs text-gray-600 dark:bg-black/30 dark:text-gray-300">Keine Vorschau</div>
          <p class="mt-2 text-xs font-semibold">Seite {{ imageEntry.page }}</p>
          <p class="text-xs opacity-70">{{ imageEntry.width }} × {{ imageEntry.height }} px</p>
        </UiPanel>
      </div>
    </UiPanel>

    <UiAlert v-if="file && !loadingList && !images.length && listLoaded" tone="warning">Dieses PDF enthält keine austauschbaren Bilder.</UiAlert>

    <UiPanel v-if="selected">
      <UiField label="Neues Bild (PNG/JPG)" for-id="replacement-image" hint="Für ein sauberes Ergebnis sollte das Seitenverhältnis dem Original entsprechen.">
        <input id="replacement-image" type="file" accept=".png,.jpg,.jpeg" class="block w-full text-sm text-gray-600 dark:text-gray-300" @change="onImage" />
      </UiField>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Bild ersetzt und PDF heruntergeladen.</UiAlert>

    <UiButton v-if="selected && newImage" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Ersetze…' : 'Bild ersetzen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useToolRun } from '@/composables/useToolRun'
import { apiPost } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

interface PdfImage {
  xref: number
  page: number
  width: number
  height: number
  preview: string
}

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const images = ref<PdfImage[]>([])
const selected = ref<number | null>(null)
const newImage = ref<File | null>(null)
const loadingList = ref(false)
const listLoaded = ref(false)

watch(file, async (currentFile) => {
  images.value = []
  selected.value = null
  newImage.value = null
  listLoaded.value = false
  error.value = null
  if (!currentFile) return
  loadingList.value = true
  try {
    const fd = new FormData()
    fd.append('file', currentFile)
    const response = await apiPost('/api/pdf-more/images/list', fd)
    images.value = ((await response.json()) as { images: PdfImage[] }).images
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Bilder lesen fehlgeschlagen'
  } finally {
    loadingList.value = false
    listLoaded.value = true
  }
})

function onImage(event: Event): void {
  newImage.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function apply(): Promise<void> {
  if (!file.value || !selected.value || !newImage.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('xref', String(selected.value))
  fd.append('image', newImage.value)
  await run('/api/pdf-more/images/replace', fd, file.value.name.replace(/\.pdf$/i, '_bild.pdf'))
}
</script>
