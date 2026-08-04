<template>
  <div class="space-y-5">
    <ToolHeader title="Seiten rotieren" description="Einzelne oder alle PDF-Seiten in 90-Grad-Schritten drehen." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <div v-if="file && Object.keys(thumbnails).length" class="flex flex-wrap gap-2">
      <UiButton size="sm" @click="rotateAll(90)">Alle 90° rechts</UiButton>
      <UiButton size="sm" @click="rotateAll(180)">Alle 180°</UiButton>
      <UiButton size="sm" @click="rotateAll(270)">Alle 90° links</UiButton>
      <UiButton variant="danger" size="sm" @click="rotations = {}">Zurücksetzen</UiButton>
    </div>

    <UiAlert v-if="file && Object.keys(thumbnails).length" tone="info">
      {{ Object.keys(rotations).length }} Seite(n) werden rotiert. Einzelne Seiten lassen sich direkt an ihrer Vorschau drehen.
    </UiAlert>

    <PageThumbnailGrid
      v-if="loadingThumbs || Object.keys(thumbnails).length"
      :key="previewGeneration"
      :thumbnails="thumbnails"
      :loading="loadingThumbs"
      :show-rotation="true"
      :rotations="rotations"
      @rotate="onRotatePage"
    />

    <UiButton
      v-if="file && Object.keys(rotations).length"
      variant="primary"
      size="lg"
      :loading="loading"
      @click="doRotate"
    >{{ loading ? 'Rotiere…' : `${Object.keys(rotations).length} Seite(n) rotieren` }}</UiButton>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import { usePdfTools } from '@/composables/usePdfTools'
import PageThumbnailGrid from './PageThumbnailGrid.vue'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, rotatePdf, getThumbnails } = usePdfTools()
const file = ref<File | null>(null)
const thumbnails = ref<Record<string, string>>({})
const loadingThumbs = ref(false)
const rotations = ref<Record<number, number>>({})
const previewGeneration = ref(0)
let latestPreviewRequest = 0

watch(file, async (currentFile) => {
  const requestId = ++latestPreviewRequest
  thumbnails.value = {}
  rotations.value = {}
  error.value = null
  previewGeneration.value += 1

  if (!currentFile) {
    loadingThumbs.value = false
    return
  }

  loadingThumbs.value = true
  try {
    const data = await getThumbnails(currentFile) as { thumbnails: Record<string, string> }
    if (requestId !== latestPreviewRequest || file.value !== currentFile) return
    thumbnails.value = data.thumbnails
  } catch (caught: unknown) {
    if (requestId !== latestPreviewRequest) return
    error.value = caught instanceof Error ? caught.message : 'Die Seitenvorschau konnte nicht geladen werden.'
  } finally {
    if (requestId === latestPreviewRequest) loadingThumbs.value = false
  }
})

function onRotatePage(page: number, angle: number): void {
  const current = rotations.value[page] || 0
  const nextAngle = (current + angle) % 360
  const next = { ...rotations.value }
  if (nextAngle === 0) delete next[page]
  else next[page] = nextAngle
  rotations.value = next
}

function rotateAll(angle: number): void {
  const next: Record<number, number> = {}
  for (const page of Object.keys(thumbnails.value).map(Number)) next[page] = angle
  rotations.value = next
}

async function doRotate(): Promise<void> {
  if (!file.value) return
  await withLoading(() => rotatePdf(file.value!, rotations.value))
}
</script>
