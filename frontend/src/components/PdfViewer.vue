<template>
  <div class="space-y-2">
    <!-- Steuerleiste -->
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <button
        class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 disabled:opacity-40"
        :disabled="modelValue <= 1 || loading"
        aria-label="Vorherige Seite"
        @click="go(modelValue - 1)"
      >←</button>
      <span class="text-gray-600 dark:text-gray-300 tabular-nums">
        Seite {{ modelValue }} / {{ pageCount || '…' }}
      </span>
      <button
        class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 disabled:opacity-40"
        :disabled="modelValue >= pageCount || loading"
        aria-label="Nächste Seite"
        @click="go(modelValue + 1)"
      >→</button>

      <span class="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700"></span>

      <button
        class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 disabled:opacity-40"
        :disabled="zoom <= MIN_ZOOM"
        aria-label="Verkleinern"
        @click="setZoom(zoom - 0.25)"
      >−</button>
      <span class="text-gray-500 dark:text-gray-400 tabular-nums w-14 text-center">{{ Math.round(zoom * 100) }} %</span>
      <button
        class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 disabled:opacity-40"
        :disabled="zoom >= MAX_ZOOM"
        aria-label="Vergrößern"
        @click="setZoom(zoom + 0.25)"
      >+</button>
      <button
        class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300"
        @click="fitWidth()"
      >Breite anpassen</button>
      <span v-if="loading" class="text-gray-600 dark:text-gray-400">rendert…</span>
    </div>

    <!-- Seitenfläche -->
    <div ref="scroller" class="overflow-auto max-h-[75vh] rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-100 dark:bg-gray-900 p-2">
      <div
        ref="pageBox"
        class="relative mx-auto bg-white shadow-sm select-none"
        :style="{ width: cssWidth + 'px', height: cssHeight + 'px' }"
        data-testid="pdf-page"
      >
        <canvas ref="canvasEl" class="block w-full h-full" />
        <!-- Overlay in Seitenkoordinaten: Kinder rechnen mit 0–1.
             `scale` = Bildschirmpunkte je PDF-Punkt, damit Overlays
             Schriftgrößen maßstabsgerecht darstellen können. -->
        <div class="absolute inset-0">
          <slot name="overlay" :width="cssWidth" :height="cssHeight" :scale="zoom" />
        </div>
      </div>
    </div>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * PDF-Anzeige direkt im Browser (pdf.js) — ohne Server-Runde.
 *
 * Ersetzt die frühere Vorschau über serverseitig gerenderte Thumbnails:
 * Seitenwechsel und Zoom laufen lokal, die Darstellung ist vektorbasiert
 * (scharf in jeder Vergrößerung) und die Datei verlässt den Browser für die
 * reine Ansicht überhaupt nicht mehr.
 */
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as pdfjs from 'pdfjs-dist'
import type { PDFDocumentProxy, RenderTask } from 'pdfjs-dist'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).href

const props = withDefaults(
  defineProps<{
    /** Arbeitskopie des Dokuments */
    source: Blob | null
    /** aktuelle Seite (v-model) */
    modelValue: number
  }>(),
  {},
)

const emit = defineEmits<{
  (e: 'update:modelValue', page: number): void
  (e: 'loaded', pageCount: number): void
  (e: 'rendered', page: number): void
  (e: 'error', message: string): void
}>()

const MIN_ZOOM = 0.25
const MAX_ZOOM = 4

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

async function destroyDoc() {
  renderTask?.cancel()
  renderTask = null
  if (doc) {
    await doc.destroy().catch(() => undefined)
    doc = null
  }
}

async function load(blob: Blob) {
  await destroyDoc()
  loading.value = true
  error.value = null
  try {
    // Eigene Kopie: pdf.js übernimmt den Puffer und gibt ihn nicht zurück
    const data = new Uint8Array(await blob.arrayBuffer())
    doc = await pdfjs.getDocument({ data, isEvalSupported: false }).promise
    pageCount.value = doc.numPages
    emit('loaded', doc.numPages)
    if (props.modelValue > doc.numPages) emit('update:modelValue', 1)
    autoFit = true
    await render()
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : 'Dokument konnte nicht geladen werden'
    error.value = message
    emit('error', message)
  } finally {
    loading.value = false
  }
}

async function render() {
  if (!doc || !canvasEl.value) return
  const pageNo = Math.min(Math.max(1, props.modelValue), doc.numPages)
  loading.value = true
  try {
    renderTask?.cancel()
    const page = await doc.getPage(pageNo)
    if (autoFit) {
      const base = page.getViewport({ scale: 1 })
      const available = (scroller.value?.clientWidth ?? 900) - 24
      zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, available / base.width))
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
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
    ctx.clearRect(0, 0, viewport.width, viewport.height)
    renderTask = page.render({ canvasContext: ctx, viewport })
    await renderTask.promise
    renderTask = null
    emit('rendered', pageNo)
  } catch (e: unknown) {
    // Abbruch beim schnellen Blättern ist kein Fehler
    if (e && typeof e === 'object' && 'name' in e && e.name === 'RenderingCancelledException') return
    const message = e instanceof Error ? e.message : 'Seite konnte nicht dargestellt werden'
    error.value = message
    emit('error', message)
  } finally {
    loading.value = false
  }
}

function go(page: number) {
  if (page < 1 || (pageCount.value && page > pageCount.value)) return
  emit('update:modelValue', page)
}

function setZoom(value: number) {
  zoom.value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.round(value * 100) / 100))
  render()
}

function fitWidth() {
  autoFit = true
  render()
}

watch(() => props.source, (blob) => { if (blob) load(blob) }, { immediate: true })
watch(() => props.modelValue, () => render())

onBeforeUnmount(destroyDoc)

defineExpose({ pageCount, refresh: render, fitWidth })
</script>
