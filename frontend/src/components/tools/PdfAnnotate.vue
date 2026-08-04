<template>
  <div class="space-y-5">
    <ToolHeader title="Anmerkungen" description="Markieren, zeichnen, kommentieren, stempeln oder Bereiche dauerhaft schwärzen." @back="$emit('back')" />
    <UiAlert v-if="!workingBlob" tone="info">Werkzeug wählen und direkt auf der Seite zeichnen. Alle Änderungen bleiben bis „Anwenden“ lokal ausstehend.</UiAlert>

    <WorkSessionBar tool="annotate" :blob="workingBlob" :name="workingName" :state="sessionState" :change-count="pending.length" @restore="restoreSession" />
    <FileDrop v-if="!workingBlob" v-model="file" />

    <template v-if="workingBlob">
      <UiPanel padding="sm" class="flex flex-wrap items-center gap-2">
        <div class="flex flex-wrap gap-1" role="group" aria-label="Anmerkungswerkzeug">
          <UiButton v-for="item in tools" :key="item.id" size="sm" :variant="tool === item.id ? 'primary' : 'secondary'" :aria-pressed="tool === item.id" @click="tool = item.id">
            <span aria-hidden="true">{{ item.icon }}</span> {{ item.label }}
          </UiButton>
        </div>
        <label class="flex items-center gap-2 text-sm font-semibold">Farbe <input v-model="color" type="color" class="h-10 w-12 cursor-pointer rounded-xl" /></label>
        <UiField v-if="tool === 'stamp'" label="Stempel" for-id="annotation-stamp">
          <select id="annotation-stamp" v-model="stampText" class="ui-control"><option>ENTWURF</option><option>VERTRAULICH</option><option>GEPRÜFT</option><option>GENEHMIGT</option><option>KOPIE</option></select>
        </UiField>
        <UiButton :disabled="pending.length >= MAX_PENDING" @click="addKeyboardAnnotation">Anmerkung per Tastatur hinzufügen</UiButton>
      </UiPanel>

      <UiPanel padding="sm" class="flex flex-wrap items-center gap-2">
        <span class="text-sm text-gray-600 dark:text-gray-300">{{ pending.length }} Anmerkung(en) ausstehend</span>
        <UiButton v-if="pending.length" size="sm" @click="undoLast">Letzte rückgängig</UiButton>
        <span class="flex-1"></span>
        <UiButton variant="primary" size="sm" :loading="applying" :disabled="!pending.length" @click="applyAnnotations">Anwenden</UiButton>
        <UiButton size="sm" :disabled="Boolean(pending.length)" @click="download">Herunterladen</UiButton>
        <UiButton variant="danger" size="sm" @click="reset">Neues Dokument</UiButton>
      </UiPanel>

      <UiAlert v-if="tool === 'redact'" tone="warning">Schwärzungen entfernen den Inhalt beim Anwenden dauerhaft und nicht nur visuell.</UiAlert>
      <UiAlert v-if="pending.length >= MAX_PENDING" tone="warning">Maximal {{ MAX_PENDING }} ausstehende Anmerkungen. Bitte anwenden oder Einträge löschen.</UiAlert>

      <PdfViewer v-model="page" :source="workingBlob" @loaded="onDocumentLoaded" @rendered="measure">
        <template #overlay>
          <div
            ref="canvasBox"
            class="absolute inset-0 touch-none cursor-crosshair"
            tabindex="0"
            role="region"
            aria-label="Anmerkungszeichenfläche. Mit Zeiger zeichnen oder Enter drücken, um die gewählte Anmerkung an einer Standardposition einzufügen."
            @keydown.enter.prevent="addKeyboardAnnotation"
            @pointerdown="onPointerDown"
            @pointermove="onPointerMove"
            @pointerup="onPointerUp"
            @pointercancel="cancelDrawing"
          >
            <svg class="pointer-events-none absolute inset-0 h-full w-full" aria-hidden="true">
              <template v-for="annotation in pagePending" :key="annotation.id">
                <rect v-if="annotation.type === 'highlight'" :x="x(annotation.box.x0)" :y="y(annotation.box.y0)" :width="w(annotation.box.x1 - annotation.box.x0)" :height="h(annotation.box.y1 - annotation.box.y0)" :fill="annotation.color" :opacity="annotation.opacity" />
                <rect v-else-if="annotation.type === 'rect'" :x="x(annotation.box.x0)" :y="y(annotation.box.y0)" :width="w(annotation.box.x1 - annotation.box.x0)" :height="h(annotation.box.y1 - annotation.box.y0)" fill="none" :stroke="annotation.color" stroke-width="2" />
                <rect v-else-if="annotation.type === 'redact'" :x="x(annotation.box.x0)" :y="y(annotation.box.y0)" :width="w(annotation.box.x1 - annotation.box.x0)" :height="h(annotation.box.y1 - annotation.box.y0)" fill="black" opacity="0.85" />
                <line v-else-if="annotation.type === 'line'" :x1="x(annotation.from.x)" :y1="y(annotation.from.y)" :x2="x(annotation.to.x)" :y2="y(annotation.to.y)" :stroke="annotation.color" stroke-width="2" />
                <g v-else-if="annotation.type === 'freetext'"><rect :x="x(annotation.box.x0)" :y="y(annotation.box.y0)" :width="w(annotation.box.x1 - annotation.box.x0)" :height="h(annotation.box.y1 - annotation.box.y0)" fill="white" opacity="0.75" :stroke="annotation.color" stroke-dasharray="4" /><text :x="x(annotation.box.x0) + 3" :y="y(annotation.box.y0) + 14" :fill="annotation.color" font-size="12">{{ annotation.text.slice(0, 40) }}</text></g>
                <g v-else-if="annotation.type === 'text_comment'"><circle :cx="x(annotation.point.x)" :cy="y(annotation.point.y)" r="9" :fill="annotation.color" /><text :x="x(annotation.point.x) - 4" :y="y(annotation.point.y) + 4" fill="white" font-size="11">!</text></g>
                <g v-else-if="annotation.type === 'stamp'"><rect :x="x(annotation.box.x0)" :y="y(annotation.box.y0)" :width="w(annotation.box.x1 - annotation.box.x0)" :height="h(annotation.box.y1 - annotation.box.y0)" fill="none" :stroke="annotation.color" stroke-width="2" /><text :x="x(annotation.box.x0) + 4" :y="y(annotation.box.y0) + 17" :fill="annotation.color" font-size="13" font-weight="bold">{{ annotation.text }}</text></g>
                <polyline v-else-if="annotation.type === 'ink'" :points="inkPoints(annotation.points)" fill="none" :stroke="annotation.color" stroke-width="2" />
              </template>
              <rect v-if="draft && ['highlight','rect','redact','stamp','freetext'].includes(tool)" :x="x(Math.min(draft.x0, draft.x1))" :y="y(Math.min(draft.y0, draft.y1))" :width="w(Math.abs(draft.x1 - draft.x0))" :height="h(Math.abs(draft.y1 - draft.y0))" fill="none" stroke="#7c3aed" stroke-dasharray="4" stroke-width="2" />
              <line v-if="draft && tool === 'line'" :x1="x(draft.x0)" :y1="y(draft.y0)" :x2="x(draft.x1)" :y2="y(draft.y1)" stroke="#7c3aed" stroke-dasharray="4" stroke-width="2" />
              <polyline v-if="inkPath.length > 1 && tool === 'ink'" :points="inkPoints(inkPath)" fill="none" stroke="#7c3aed" stroke-width="2" />
            </svg>
          </div>
        </template>
      </PdfViewer>

      <UiPanel v-if="pending.length" class="space-y-2">
        <h3 class="font-semibold">Ausstehende Anmerkungen</h3>
        <ul class="max-h-64 space-y-1 overflow-y-auto">
          <li v-for="annotation in pending" :key="annotation.id" class="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-black/5 dark:hover:bg-white/10">
            <UiButton variant="ghost" size="sm" class="min-w-0 flex-1 justify-start" @click="page = annotation.page">{{ annotationLabel(annotation) }} · Seite {{ annotation.page }}</UiButton>
            <UiIconButton size="sm" variant="danger" :aria-label="`${annotationLabel(annotation)} entfernen`" @click="removeAnnotation(annotation.id)">×</UiIconButton>
          </li>
        </ul>
      </UiPanel>
    </template>

    <div v-if="textPrompt" class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" @mousedown.self="closeTextPrompt">
      <form ref="promptDialog" class="w-full max-w-sm space-y-4 rounded-[1.5rem] bg-white/95 p-5 shadow-apple dark:bg-gray-900/95" role="dialog" aria-modal="true" aria-labelledby="annotation-prompt-title" @submit.prevent="confirmText">
        <h3 id="annotation-prompt-title" class="font-semibold">{{ textPrompt.kind === 'freetext' ? 'Freitext' : 'Kommentar' }}</h3>
        <UiField label="Text" for-id="annotation-text" required><textarea id="annotation-text" ref="promptInput" v-model="textPrompt.text" rows="4" maxlength="5000" class="ui-control w-full"></textarea></UiField>
        <div class="flex justify-end gap-2"><UiButton @click="closeTextPrompt">Abbrechen</UiButton><UiButton variant="primary" type="submit" :disabled="!textPrompt.text.trim()">Übernehmen</UiButton></div>
      </form>
    </div>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import WorkSessionBar from '@/components/WorkSessionBar.vue'
import { apiPost, downloadBlob } from '@/lib/api'

const PdfViewer = defineAsyncComponent(() => import('@/components/PdfViewer.vue'))
defineEmits<{ (event: 'back'): void }>()

type Tool = 'highlight' | 'rect' | 'line' | 'freetext' | 'text_comment' | 'stamp' | 'ink' | 'redact'
interface Point { x: number; y: number }
interface Box { x0: number; y0: number; x1: number; y1: number }
interface BaseAnnotation { id: string; page: number; color: string }
type Annotation =
  | (BaseAnnotation & { type: 'highlight'; box: Box; opacity: number })
  | (BaseAnnotation & { type: 'rect'; box: Box; width: number })
  | (BaseAnnotation & { type: 'redact'; box: Box; fill_color: string })
  | (BaseAnnotation & { type: 'line'; from: Point; to: Point; width: number })
  | (BaseAnnotation & { type: 'freetext'; box: Box; text: string; font_size: number })
  | (BaseAnnotation & { type: 'text_comment'; point: Point; content: string })
  | (BaseAnnotation & { type: 'stamp'; box: Box; text: string })
  | (BaseAnnotation & { type: 'ink'; points: Point[]; width: number })
interface TextPrompt { kind: 'freetext' | 'text_comment'; text: string; box: Box }

const MAX_PENDING = 500
const tools: { id: Tool; label: string; icon: string }[] = [
  { id: 'highlight', label: 'Markieren', icon: '🖍️' }, { id: 'rect', label: 'Rechteck', icon: '▭' },
  { id: 'line', label: 'Linie', icon: '╱' }, { id: 'freetext', label: 'Freitext', icon: '🔤' },
  { id: 'text_comment', label: 'Kommentar', icon: '💬' }, { id: 'stamp', label: 'Stempel', icon: '🔖' },
  { id: 'ink', label: 'Zeichnen', icon: '✏️' }, { id: 'redact', label: 'Schwärzen', icon: '⬛' },
]

const file = ref<File | null>(null)
const workingBlob = ref<Blob | null>(null)
const workingName = ref('dokument.pdf')
const page = ref(1)
const pageCount = ref(1)
const applying = ref(false)
const error = ref<string | null>(null)
const tool = ref<Tool>('highlight')
const color = ref('#ffde21')
const stampText = ref('ENTWURF')
const pending = ref<Annotation[]>([])
const canvasBox = ref<HTMLElement | null>(null)
const draft = ref<Box | null>(null)
const inkPath = ref<Point[]>([])
const textPrompt = ref<TextPrompt | null>(null)
const promptDialog = ref<HTMLFormElement | null>(null)
const promptInput = ref<HTMLTextAreaElement | null>(null)
const boxSize = ref({ w: 1, h: 1 })
const sessionState = computed(() => ({ pending: pending.value, page: page.value }))
const pagePending = computed(() => pending.value.filter((annotation) => annotation.page === page.value))
let nextId = 1
let documentGeneration = 0
let drawingPointer: number | null = null
let resizeObserver: ResizeObserver | null = null
let previousPromptFocus: HTMLElement | null = null
let ignoreNextFileReset = false

function id(): string { return `annotation-${Date.now()}-${nextId++}` }
function clamp(value: number): number { return Math.max(0, Math.min(1, value)) }
function measure(): void { if (canvasBox.value) boxSize.value = { w: Math.max(1, canvasBox.value.clientWidth), h: Math.max(1, canvasBox.value.clientHeight) } }
function x(value: number): number { return value * boxSize.value.w }
function y(value: number): number { return value * boxSize.value.h }
function w(value: number): number { return Math.max(1, value * boxSize.value.w) }
function h(value: number): number { return Math.max(1, value * boxSize.value.h) }
function inkPoints(points: Point[]): string { return points.map((point) => `${x(point.x)},${y(point.y)}`).join(' ') }
function point(event: PointerEvent): Point { const rect = canvasBox.value!.getBoundingClientRect(); return { x: clamp((event.clientX - rect.left) / rect.width), y: clamp((event.clientY - rect.top) / rect.height) } }
function normalizedBox(box: Box): Box { return { x0: Math.min(box.x0, box.x1), y0: Math.min(box.y0, box.y1), x1: Math.max(box.x0, box.x1), y1: Math.max(box.y0, box.y1) } }

watch(file, (currentFile) => {
  if (ignoreNextFileReset) { ignoreNextFileReset = false; return }
  documentGeneration += 1
  resetDrafts()
  pending.value = []
  page.value = 1
  error.value = null
  if (!currentFile) { workingBlob.value = null; return }
  workingBlob.value = currentFile; workingName.value = currentFile.name
})
watch(canvasBox, (element) => { resizeObserver?.disconnect(); resizeObserver = null; if (element && typeof ResizeObserver !== 'undefined') { resizeObserver = new ResizeObserver(measure); resizeObserver.observe(element); void nextTick(measure) } })
watch(textPrompt, async (value) => { if (value) { previousPromptFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null; document.addEventListener('keydown', onPromptKeydown); await nextTick(); promptInput.value?.focus() } else { document.removeEventListener('keydown', onPromptKeydown); previousPromptFocus?.focus(); previousPromptFocus = null } })

function normalizeAnnotation(value: unknown): Annotation | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>; const type = String(raw.type) as Tool; const pageNumber = Math.max(1, Math.trunc(Number(raw.page) || 1)); const annotationColor = String(raw.color ?? '#ffde21')
  const boxFrom = (): Box => ({ x0: clamp(Number(raw.x0 ?? (raw.x as number) ?? .1)), y0: clamp(Number(raw.y0 ?? (raw.y as number) ?? .1)), x1: clamp(Number(raw.x1 ?? .3)), y1: clamp(Number(raw.y1 ?? .15)) })
  if (type === 'highlight') { const quad = Array.isArray(raw.quads) && raw.quads[0] && typeof raw.quads[0] === 'object' ? raw.quads[0] as Record<string, unknown> : raw; return { id: id(), type, page: pageNumber, color: annotationColor, box: normalizedBox({ x0: clamp(Number(quad.x0) || .1), y0: clamp(Number(quad.y0) || .1), x1: clamp(Number(quad.x1) || .3), y1: clamp(Number(quad.y1) || .15) }), opacity: Number(raw.opacity) || .4 } }
  if (type === 'rect') return { id: id(), type, page: pageNumber, color: annotationColor, box: normalizedBox(boxFrom()), width: Number(raw.width) || 2 }
  if (type === 'redact') return { id: id(), type, page: pageNumber, color: '#000000', box: normalizedBox(boxFrom()), fill_color: '#000000' }
  if (type === 'line') return { id: id(), type, page: pageNumber, color: annotationColor, from: { x: clamp(Number(raw.x0) || .1), y: clamp(Number(raw.y0) || .1) }, to: { x: clamp(Number(raw.x1) || .3), y: clamp(Number(raw.y1) || .2) }, width: Number(raw.width) || 2 }
  if (type === 'freetext') { const box = boxFrom(); box.x1 = clamp(Number(raw.x) + Number(raw.width) || box.x1); box.y1 = clamp(Number(raw.y) + Number(raw.height) || box.y1); return { id: id(), type, page: pageNumber, color: annotationColor, box: normalizedBox(box), text: String(raw.text ?? '').slice(0, 5000), font_size: Number(raw.font_size) || 11 } }
  if (type === 'text_comment') return { id: id(), type, page: pageNumber, color: annotationColor, point: { x: clamp(Number(raw.x) || .1), y: clamp(Number(raw.y) || .1) }, content: String(raw.content ?? '').slice(0, 5000) }
  if (type === 'stamp') return { id: id(), type, page: pageNumber, color: annotationColor, box: normalizedBox(boxFrom()), text: String(raw.text ?? 'ENTWURF').slice(0, 100) }
  if (type === 'ink') { const paths = Array.isArray(raw.paths) ? raw.paths : []; const first = Array.isArray(paths[0]) ? paths[0] : []; const points = first.flatMap((entry) => entry && typeof entry === 'object' ? [{ x: clamp(Number((entry as Record<string, unknown>).x) || 0), y: clamp(Number((entry as Record<string, unknown>).y) || 0) }] : []); return points.length > 1 ? { id: id(), type, page: pageNumber, color: annotationColor, points, width: Number(raw.width) || 2 } : null }
  return null
}

function restoreSession(payload: { name: string; blob: Blob; state: unknown }): void { documentGeneration += 1; if (file.value) { ignoreNextFileReset = true; file.value = null } workingBlob.value = payload.blob; workingName.value = payload.name; resetDrafts(); const state = payload.state && typeof payload.state === 'object' ? payload.state as { pending?: unknown[]; page?: number } : null; pending.value = Array.isArray(state?.pending) ? state.pending.slice(0, MAX_PENDING).flatMap((item) => { const normalized = normalizeAnnotation(item); return normalized ? [normalized] : [] }) : []; page.value = Math.max(1, Math.trunc(Number(state?.page) || 1)); error.value = null }
function onDocumentLoaded(count: number): void { pageCount.value = Math.max(1, count); page.value = Math.min(page.value, pageCount.value) }
function resetDrafts(): void { draft.value = null; inkPath.value = []; drawingPointer = null; textPrompt.value = null }

function onPointerDown(event: PointerEvent): void { if (!canvasBox.value || event.button !== 0 || pending.value.length >= MAX_PENDING) return; measure(); const current = point(event); if (tool.value === 'text_comment') { openTextPrompt('text_comment', { x0: current.x, y0: current.y, x1: current.x, y1: current.y }); return } drawingPointer = event.pointerId; canvasBox.value.setPointerCapture(event.pointerId); if (tool.value === 'ink') inkPath.value = [current]; else draft.value = { x0: current.x, y0: current.y, x1: current.x, y1: current.y } }
function onPointerMove(event: PointerEvent): void { if (drawingPointer !== event.pointerId) return; const current = point(event); if (tool.value === 'ink') inkPath.value.push(current); else if (draft.value) draft.value = { ...draft.value, x1: current.x, y1: current.y } }
function onPointerUp(event: PointerEvent): void { if (drawingPointer !== event.pointerId) return; const currentDraft = draft.value; const currentInk = [...inkPath.value]; cancelDrawing(event); if (tool.value === 'ink') { if (currentInk.length > 2) add({ id: id(), type: 'ink', page: page.value, color: color.value, points: currentInk, width: 2 }); return } if (!currentDraft) return; finishBox(currentDraft) }
function cancelDrawing(event?: PointerEvent): void { if (event && canvasBox.value?.hasPointerCapture(event.pointerId)) canvasBox.value.releasePointerCapture(event.pointerId); drawingPointer = null; draft.value = null; inkPath.value = [] }

function finishBox(raw: Box): void { const box = normalizedBox(raw); if (tool.value !== 'line' && (box.x1 - box.x0 < .005 || box.y1 - box.y0 < .005)) return; if (tool.value === 'highlight') add({ id: id(), type: 'highlight', page: page.value, color: color.value, box, opacity: .4 }); else if (tool.value === 'rect') add({ id: id(), type: 'rect', page: page.value, color: color.value, box, width: 2 }); else if (tool.value === 'redact') add({ id: id(), type: 'redact', page: page.value, color: '#000000', box, fill_color: '#000000' }); else if (tool.value === 'line') add({ id: id(), type: 'line', page: page.value, color: color.value, from: { x: raw.x0, y: raw.y0 }, to: { x: raw.x1, y: raw.y1 }, width: 2 }); else if (tool.value === 'stamp') add({ id: id(), type: 'stamp', page: page.value, color: color.value, box, text: stampText.value }); else if (tool.value === 'freetext') openTextPrompt('freetext', box) }
function add(annotation: Annotation): void { if (pending.value.length < MAX_PENDING) pending.value.push(annotation) }
function addKeyboardAnnotation(): void { if (pending.value.length >= MAX_PENDING) return; const offset = (pagePending.value.length % 8) * .04; const box = { x0: .08 + offset, y0: .08 + offset, x1: .38 + offset, y1: .16 + offset }; if (tool.value === 'text_comment' || tool.value === 'freetext') openTextPrompt(tool.value, box); else if (tool.value === 'ink') add({ id: id(), type: 'ink', page: page.value, color: color.value, width: 2, points: [{ x: box.x0, y: box.y0 }, { x: box.x0 + .08, y: box.y0 + .04 }, { x: box.x0 + .16, y: box.y0 }] }); else finishBox(box) }

function openTextPrompt(kind: TextPrompt['kind'], box: Box): void { textPrompt.value = { kind, text: '', box } }
function closeTextPrompt(): void { textPrompt.value = null }
function confirmText(): void { const prompt = textPrompt.value; if (!prompt?.text.trim()) return; if (prompt.kind === 'freetext') add({ id: id(), type: 'freetext', page: page.value, color: color.value, box: normalizedBox(prompt.box), text: prompt.text.trim(), font_size: 11 }); else add({ id: id(), type: 'text_comment', page: page.value, color: color.value, point: { x: prompt.box.x0, y: prompt.box.y0 }, content: prompt.text.trim() }); closeTextPrompt() }
function onPromptKeydown(event: KeyboardEvent): void { if (event.key === 'Escape') { event.preventDefault(); closeTextPrompt(); return } if (event.key !== 'Tab' || !promptDialog.value) return; const items = Array.from(promptDialog.value.querySelectorAll<HTMLElement>('textarea, button:not([disabled])')); if (!items.length) return; const first = items[0]; const last = items[items.length - 1]; if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() } else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() } }

function annotationLabel(annotation: Annotation): string { return tools.find((item) => item.id === annotation.type)?.label ?? annotation.type }
function removeAnnotation(annotationId: string): void { pending.value = pending.value.filter((annotation) => annotation.id !== annotationId) }
function undoLast(): void { pending.value = pending.value.slice(0, -1) }
function backendPayload(annotation: Annotation): object { if (annotation.type === 'highlight') return { type: annotation.type, page: annotation.page, quads: [annotation.box], color: annotation.color, opacity: annotation.opacity }; if (annotation.type === 'rect' || annotation.type === 'redact' || annotation.type === 'stamp') return { type: annotation.type, page: annotation.page, ...annotation.box, color: annotation.color, width: 'width' in annotation ? annotation.width : undefined, fill_color: 'fill_color' in annotation ? annotation.fill_color : undefined, text: 'text' in annotation ? annotation.text : undefined }; if (annotation.type === 'line') return { type: annotation.type, page: annotation.page, x0: annotation.from.x, y0: annotation.from.y, x1: annotation.to.x, y1: annotation.to.y, color: annotation.color, width: annotation.width }; if (annotation.type === 'freetext') return { type: annotation.type, page: annotation.page, x: annotation.box.x0, y: annotation.box.y0, width: annotation.box.x1 - annotation.box.x0, height: annotation.box.y1 - annotation.box.y0, text: annotation.text, font_size: annotation.font_size, color: annotation.color }; if (annotation.type === 'text_comment') return { type: annotation.type, page: annotation.page, x: annotation.point.x, y: annotation.point.y, content: annotation.content, color: annotation.color }; return { type: annotation.type, page: annotation.page, paths: [annotation.points], color: annotation.color, width: annotation.width } }

async function applyAnnotations(): Promise<void> { const blob = workingBlob.value; if (!blob || !pending.value.length || applying.value) return; const generation = documentGeneration; applying.value = true; error.value = null; try { const formData = new FormData(); formData.append('file', blob, workingName.value); formData.append('annotations', JSON.stringify(pending.value.map(backendPayload))); const response = await apiPost('/api/pdf-editor/annotations', formData); const newBlob = await response.blob(); if (generation !== documentGeneration || workingBlob.value !== blob) return; workingBlob.value = newBlob; pending.value = [] } catch (caught: unknown) { if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Anwenden fehlgeschlagen.' } finally { if (generation === documentGeneration) applying.value = false } }
async function download(): Promise<void> { if (!workingBlob.value) return; await downloadBlob(new Response(workingBlob.value), workingName.value.replace(/\.pdf$/i, '_annotiert.pdf')) }
function reset(): void { documentGeneration += 1; resizeObserver?.disconnect(); resizeObserver = null; file.value = null; workingBlob.value = null; pending.value = []; page.value = 1; pageCount.value = 1; resetDrafts(); error.value = null }

onBeforeUnmount(() => { documentGeneration += 1; resizeObserver?.disconnect(); document.removeEventListener('keydown', onPromptKeydown) })
</script>
