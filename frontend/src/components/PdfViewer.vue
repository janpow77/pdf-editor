<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <button type="button" class="apple-icon-button !h-9 !w-9" :disabled="modelValue <= 1 || loading" aria-label="Vorherige Seite" @click="go(modelValue - 1)">←</button>
      <span class="rounded-full bg-gray-100 px-3 py-2 font-medium tabular-nums text-gray-700 dark:bg-white/10 dark:text-gray-200">Seite {{ modelValue }} / {{ pageCount || '…' }}</span>
      <button type="button" class="apple-icon-button !h-9 !w-9" :disabled="modelValue >= pageCount || loading" aria-label="Nächste Seite" @click="go(modelValue + 1)">→</button>

      <span class="mx-1 h-5 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>

      <button type="button" class="apple-icon-button !h-9 !w-9" :disabled="zoom <= MIN_ZOOM" aria-label="PDF verkleinern" @click="setZoom(zoom - 0.25)">−</button>
      <span class="w-16 text-center font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ Math.round(zoom * 100) }} %</span>
      <button type="button" class="apple-icon-button !h-9 !w-9" :disabled="zoom >= MAX_ZOOM" aria-label="PDF vergrößern" @click="setZoom(zoom + 0.25)">+</button>
      <button type="button" class="rounded-full bg-white/80 px-4 py-2 font-semibold text-gray-700 shadow-sm ring-1 ring-gray-300 hover:shadow-apple dark:bg-white/10 dark:text-gray-200 dark:ring-gray-600" @click="fitWidth">Breite anpassen</button>
      <span v-if="loading" class="text-sm font-medium text-gray-600 dark:text-gray-300" role="status">PDF wird gerendert…</span>
    </div>

    <div ref="scroller" class="max-h-[78vh] overflow-auto rounded-[1.35rem] bg-gray-200/70 p-3 shadow-inner ring-1 ring-gray-400/60 dark:bg-black/35 dark:ring-gray-600">
      <div ref="pageBox" class="relative mx-auto bg-white shadow-apple select-none" :style="{ width: cssWidth + 'px', height: cssHeight + 'px' }" data-testid="pdf-page">
        <canvas ref="canvasEl" class="block h-full w-full" />
        <div class="absolute inset-0">
          <slot name="overlay" :width="cssWidth" :height="cssHeight" :scale="zoom" />
        </div>
      </div>
    </div>

    <p v-if="error" class="apple-inline-error text-sm" role="alert">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * Lokaler PDF-Viewer auf Basis von pdf.js.
 *
 * Auf ausreichend breiten Arbeitsflächen startet die Seite mit mindestens
 * 150 Prozent Skalierung. Kleine Displays verwenden weiterhin die eingepasste
 * Breite, sodass das Layout responsiv bleibt. Ein Generationszähler verhindert,
 * dass ein langsamer Ladevorgang des vorherigen Dokuments den neuen Zustand
 * nachträglich überschreibt.
 */
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as pdfjs from 'pdfjs-dist'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).href

const props = defineProps<{ source: Blob | null; modelValue: number }>()
const emit = defineEmits<{
  (e: 'update:modelValue', page: number): void
  (e: 'loaded', pageCount: number): void
  (e: 'rendered', page: number): void
  (e: 'error', message: string): void
}>()

const MIN_ZOOM = 0.25
const MAX_ZOOM = 4
const DESKTOP_BASE_ZOOM = 1.5

const scroller = ref<HTMLElement | null>(null)
const pageBox = ref<HTMLElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const pageCount = ref(0)
const zoom = ref(1)
const cssWidth = ref(0)
const cssHeight = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

let doc: PDFDocumentProxy | null = null
let renderTask: RenderTask | null = null
let autoFit = true
let documentGeneration = 0

async function destroyDoc(): Promise<void> {
  renderTask?.cancel()
  renderTask = null
  if (doc) {
    await doc.destroy().catch(() => undefined)
    doc = null
  }
}

function clearCanvas(): void {
  const canvas = canvasEl.value
  if (canvas) {
    const context = canvas.getContext('2d')
    context?.clearRect(0, 0, canvas.width, canvas.height)
    canvas.width = 0
    canvas.height = 0
  }
  cssWidth.value = 0
  cssHeight.value = 0
  pageCount.value = 0
}

async function load(blob: Blob): Promise<void> {
  const generation = ++documentGeneration
  await destroyDoc()
  clearCanvas()
  loading.value = true
  error.value = null

  try {
    const data = new Uint8Array(await blob.arrayBuffer())
    if (generation !== documentGeneration) return

    const loadedDoc = await pdfjs.getDocument({ data, isEvalSupported: false }).promise
    if (generation !== documentGeneration) {
      await loadedDoc.destroy().catch(() => undefined)
      return
    }

    doc = loadedDoc
    pageCount.value = loadedDoc.numPages
    emit('loaded', loadedDoc.numPages)
    if (props.modelValue > loadedDoc.numPages) emit('update:modelValue', 1)
    autoFit = true
    await render(generation)
  } catch (loadError: unknown) {
    if (generation !== documentGeneration) return
    const message = loadError instanceof Error ? loadError.message : 'Dokument konnte nicht geladen werden.'
    error.value = message
    emit('error', message)
  } finally {
    if (generation === documentGeneration) loading.value = false
  }
}

async function render(expectedGeneration = documentGeneration): Promise<void> {
  if (!doc || !canvasEl.value || expectedGeneration !== documentGeneration) return
  const currentDoc = doc
  const pageNo = Math.min(Math.max(1, props.modelValue), currentDoc.numPages)
  loading.value = true

  try {
    renderTask?.cancel()
    const page = await currentDoc.getPage(pageNo)
    if (expectedGeneration !== documentGeneration || currentDoc !== doc) return

    if (autoFit) {
      const base = page.getViewport({ scale: 1 })
      const available = Math.max(280, (scroller.value?.clientWidth ?? 900) - 28)
      const fittedZoom = available / base.width
      zoom.value = available >= 900
        ? Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, fittedZoom, DESKTOP_BASE_ZOOM))
        : Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, fittedZoom))
      autoFit = false
    }

    const viewport = page.getViewport({ scale: zoom.value })
    const ratio = Math.min(window.devicePixelRatio || 1, 2)
    const canvas = canvasEl.value
    canvas.width = Math.floor(viewport.width * ratio)
    canvas.height = Math.floor(viewport.height * ratio)
    cssWidth.value = Math.floor(viewport.width)
    cssHeight.value = Math.floor(viewport.height)
    await nextTick()

    const context = canvas.getContext('2d')
    if (!context || expectedGeneration !== documentGeneration) return
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
    context.clearRect(0, 0, viewport.width, viewport.height)
    renderTask = page.render({ canvasContext: context, viewport })
    await renderTask.promise
    renderTask = null
    if (expectedGeneration === documentGeneration) emit('rendered', pageNo)
  } catch (renderError: unknown) {
    if (renderError && typeof renderError === 'object' && 'name' in renderError && renderError.name === 'RenderingCancelledException') return
    if (expectedGeneration !== documentGeneration) return
    const message = renderError instanceof Error ? renderError.message : 'Seite konnte nicht dargestellt werden.'
    error.value = message
    emit('error', message)
  } finally {
    if (expectedGeneration === documentGeneration) loading.value = false
  }
}

function go(page: number): void {
  if (page < 1 || (pageCount.value && page > pageCount.value)) return
  emit('update:modelValue', page)
}

function setZoom(value: number): void {
  zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100))
  void render()
}

function fitWidth(): void {
  autoFit = true
  void render()
}

watch(() => props.source, (blob) => {
  if (blob) void load(blob)
  else {
    documentGeneration += 1
    void destroyDoc()
    clearCanvas()
  }
}, { immediate: true })
watch(() => props.modelValue, () => void render())

onBeforeUnmount(() => {
  documentGeneration += 1
  void destroyDoc()
})

defineExpose({ pageCount, refresh: render, fitWidth })
</script>
