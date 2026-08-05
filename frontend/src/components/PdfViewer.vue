<template>
  <div class="space-y-3">
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <UiIconButton :disabled="modelValue <= 1 || loading" aria-label="Vorherige Seite" @click="go(modelValue - 1)">←</UiIconButton>
      <span class="rounded-full bg-gray-100 px-3 py-2 font-medium tabular-nums text-gray-700 dark:bg-white/10 dark:text-gray-200">Seite {{ modelValue }} / {{ pageCount || '…' }}</span>
      <UiIconButton :disabled="modelValue >= pageCount || loading" aria-label="Nächste Seite" @click="go(modelValue + 1)">→</UiIconButton>

      <span class="mx-1 h-5 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>

      <UiIconButton :disabled="zoom <= MIN_ZOOM" aria-label="PDF verkleinern" @click="setZoom(zoom - 0.25)">−</UiIconButton>
      <span class="w-16 text-center font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ Math.round(zoom * 100) }} %</span>
      <UiIconButton :disabled="zoom >= MAX_ZOOM" aria-label="PDF vergrößern" @click="setZoom(zoom + 0.25)">+</UiIconButton>
      <UiButton size="sm" @click="fitWidth">Breite anpassen</UiButton>
      <span v-if="loading" class="text-sm font-medium text-gray-600 dark:text-gray-300" role="status">PDF wird gerendert…</span>
    </div>

    <div ref="scroller" class="max-h-[78vh] overflow-auto rounded-[1.35rem] bg-gray-200/70 p-3 shadow-inner ring-1 ring-gray-400/60 dark:bg-black/35 dark:ring-gray-600">
      <div class="relative mx-auto select-none bg-white shadow-apple" :style="{ width: cssWidth + 'px', height: cssHeight + 'px' }" data-testid="pdf-page">
        <canvas ref="canvasEl" class="block h-full w-full" />
        <div class="absolute inset-0">
          <slot name="overlay" :width="cssWidth" :height="cssHeight" :scale="zoom" />
        </div>
      </div>
    </div>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
/**
 * Lokaler PDF-Viewer auf Basis von pdf.js.
 *
 * Ein Dokument- und ein separater Renderzähler schützen sowohl Dateiwechsel als
 * auch schnelles Blättern beziehungsweise Zoomen. Ein ResizeObserver rendert im
 * Modus „Breite anpassen“ bei Größenänderungen neu, ohne eine ältere Seite über
 * die aktuelle zu schreiben.
 */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as pdfjs from 'pdfjs-dist'
import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from 'pdfjs-dist'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).href

/** `rotation`: zusätzliche Ansichtsdrehung in Grad (0/90/180/270) — pdf.js
 *  dreht das Viewport nativ, z. B. für die Drehvorschau der Werkbank. */
const props = defineProps<{ source: Blob | null; modelValue: number; rotation?: number }>()
const emit = defineEmits<{
  (event: 'update:modelValue', page: number): void
  (event: 'loaded', pageCount: number): void
  (event: 'rendered', page: number): void
  (event: 'error', message: string): void
}>()

const MIN_ZOOM = 0.25
const MAX_ZOOM = 4
const DESKTOP_BASE_ZOOM = 1.5

const scroller = ref<HTMLElement | null>(null)
const canvasEl = ref<HTMLCanvasElement | null>(null)
const pageCount = ref(0)
const zoom = ref(1)
const cssWidth = ref(0)
const cssHeight = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)

let doc: PDFDocumentProxy | null = null
let renderTask: RenderTask | null = null
let fitMode = true
let documentGeneration = 0
let renderGeneration = 0
let resizeObserver: ResizeObserver | null = null
let resizeTimer: ReturnType<typeof globalThis.setTimeout> | null = null

function isRenderingCancelled(value: unknown): boolean {
  return Boolean(
    value
    && typeof value === 'object'
    && 'name' in value
    && value.name === 'RenderingCancelledException',
  )
}

async function destroyDoc(): Promise<void> {
  renderGeneration += 1
  renderTask?.cancel()
  renderTask = null
  if (doc) {
    const oldDoc = doc
    doc = null
    await oldDoc.destroy().catch(() => undefined)
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
    // Bei einem unmittelbaren `immediate`-Watch kann das Canvas noch nicht
    // gemountet sein. Ein Tick macht den ersten Render deterministisch.
    await nextTick()
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
    if (props.modelValue < 1 || props.modelValue > loadedDoc.numPages) {
      emit('update:modelValue', 1)
      await nextTick()
    }
    fitMode = true
    await render(generation)
  } catch (loadError: unknown) {
    if (generation !== documentGeneration) return
    const message = loadError instanceof Error ? loadError.message : 'Dokument konnte nicht geladen werden.'
    error.value = message
    emit('error', message)
  } finally {
    if (generation === documentGeneration && renderGeneration === 0) loading.value = false
  }
}

async function render(expectedDocument = documentGeneration): Promise<void> {
  if (!doc || !canvasEl.value || expectedDocument !== documentGeneration) return

  const currentDoc = doc
  const renderId = ++renderGeneration
  const pageNo = Math.min(Math.max(1, props.modelValue), currentDoc.numPages)
  let page: PDFPageProxy | null = null
  let task: RenderTask | null = null
  loading.value = true
  error.value = null

  try {
    renderTask?.cancel()
    page = await currentDoc.getPage(pageNo)
    if (renderId !== renderGeneration || expectedDocument !== documentGeneration || currentDoc !== doc) return

    const totalRotation = ((page.rotate ?? 0) + (props.rotation ?? 0)) % 360

    if (fitMode) {
      const base = page.getViewport({ scale: 1, rotation: totalRotation })
      const available = Math.max(280, (scroller.value?.clientWidth ?? 900) - 28)
      const fittedZoom = available / base.width
      zoom.value = available >= 900
        ? Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, fittedZoom, DESKTOP_BASE_ZOOM))
        : Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, fittedZoom))
    }

    const viewport = page.getViewport({ scale: zoom.value, rotation: totalRotation })
    const ratio = Math.min(typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1, 2)
    const canvas = canvasEl.value
    canvas.width = Math.max(1, Math.floor(viewport.width * ratio))
    canvas.height = Math.max(1, Math.floor(viewport.height * ratio))
    cssWidth.value = Math.max(1, Math.floor(viewport.width))
    cssHeight.value = Math.max(1, Math.floor(viewport.height))
    await nextTick()

    const context = canvas.getContext('2d')
    if (!context || renderId !== renderGeneration || expectedDocument !== documentGeneration) return
    context.setTransform(ratio, 0, 0, ratio, 0, 0)
    context.clearRect(0, 0, viewport.width, viewport.height)

    task = page.render({ canvasContext: context, viewport })
    renderTask = task
    await task.promise
    if (renderId !== renderGeneration || expectedDocument !== documentGeneration || currentDoc !== doc) return
    emit('rendered', pageNo)
  } catch (renderError: unknown) {
    if (isRenderingCancelled(renderError)) return
    if (renderId !== renderGeneration || expectedDocument !== documentGeneration) return
    const message = renderError instanceof Error ? renderError.message : 'Seite konnte nicht dargestellt werden.'
    error.value = message
    emit('error', message)
  } finally {
    page?.cleanup()
    if (renderTask === task) renderTask = null
    if (renderId === renderGeneration && expectedDocument === documentGeneration) loading.value = false
  }
}

function go(page: number): void {
  if (page < 1 || (pageCount.value && page > pageCount.value)) return
  emit('update:modelValue', page)
}

function setZoom(value: number): void {
  fitMode = false
  zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100))
  void render()
}

function fitWidth(): void {
  fitMode = true
  void render()
}

function scheduleResizeRender(): void {
  if (!fitMode || !doc) return
  if (resizeTimer) globalThis.clearTimeout(resizeTimer)
  resizeTimer = globalThis.setTimeout(() => {
    resizeTimer = null
    void render()
  }, 80)
}

watch(() => props.source, (blob) => {
  if (blob) void load(blob)
  else {
    documentGeneration += 1
    renderGeneration += 1
    void destroyDoc()
    clearCanvas()
    loading.value = false
    error.value = null
  }
}, { immediate: true })

watch(() => props.modelValue, () => {
  if (doc) void render()
})

watch(() => props.rotation, () => {
  if (doc) void render()
})

onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !scroller.value) return
  resizeObserver = new ResizeObserver(scheduleResizeRender)
  resizeObserver.observe(scroller.value)
})

onBeforeUnmount(() => {
  documentGeneration += 1
  renderGeneration += 1
  resizeObserver?.disconnect()
  resizeObserver = null
  if (resizeTimer) globalThis.clearTimeout(resizeTimer)
  resizeTimer = null
  void destroyDoc()
})

defineExpose({ pageCount, refresh: render, fitWidth })
</script>
