<template>
  <div class="space-y-5">
    <ToolHeader title="Text bearbeiten" description="Textblöcke direkt auf der PDF-Seite oder vollständig per Tastatur bearbeiten." @back="$emit('back')" />
    <UiAlert v-if="!workingBlob" tone="info">
      Textblöcke bleiben auf ihrer Seite und innerhalb ihrer Box. Ein automatischer Umbruch über Absätze oder Seiten hinweg ist nicht möglich.
    </UiAlert>

    <WorkSessionBar tool="textEditor" :blob="workingBlob" :name="workingName" :state="sessionState" :change-count="editCount" @restore="restoreSession" />
    <FileDrop v-if="!workingBlob" v-model="file" />

    <template v-if="workingBlob">
      <UiPanel padding="sm" class="flex flex-wrap items-center gap-2">
        <span class="text-sm text-gray-600 dark:text-gray-300">{{ editCount }} Änderung(en) ausstehend</span>
        <span v-if="loadingPage" class="text-sm text-gray-600 dark:text-gray-300" role="status">Textblöcke werden geladen…</span>
        <span class="flex-1"></span>
        <UiButton variant="primary" size="sm" :loading="applying" :disabled="!editCount" @click="applyEdits">Änderungen anwenden</UiButton>
        <UiButton size="sm" :disabled="Boolean(editCount)" @click="download">Herunterladen</UiButton>
        <UiButton variant="danger" size="sm" @click="reset">Neues Dokument</UiButton>
      </UiPanel>

      <UiAlert v-if="warnings" tone="warning">{{ warnings }} Textbox(en) waren zu klein; die Schrift wurde beim Anwenden verkleinert.</UiAlert>

      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr),24rem]">
        <div>
          <PdfViewer v-model="page" :source="workingBlob" @loaded="onDocumentLoaded" @rendered="loadBlocks">
            <template #overlay="{ width, height, scale }">
              <button
                v-for="(block, index) in blocks"
                v-show="editKey(page, index) !== activeKey"
                :key="editKey(page, index)"
                type="button"
                class="absolute border transition-colors"
                :class="blockClass(index)"
                :style="boxStyle(boxOf(index), width, height)"
                :aria-label="`Textblock ${index + 1} bearbeiten: ${block.text.slice(0, 60)}`"
                @click="startEdit(index)"
              >
                <span
                  v-if="edits.has(editKey(page, index))"
                  class="absolute inset-0 overflow-hidden whitespace-pre-wrap break-words bg-white px-px text-left leading-tight"
                  :style="textStyle(edits.get(editKey(page, index))!, scale)"
                >{{ edits.get(editKey(page, index))!.text }}</span>
              </button>

              <template v-if="active">
                <div class="absolute bg-white shadow-apple ring-2 ring-primary-500" :style="boxStyle(active.box, width, height)">
                  <div
                    ref="editorEl"
                    class="h-full w-full cursor-text overflow-hidden whitespace-pre-wrap break-words px-px leading-tight outline-none"
                    :style="textStyle(active, scale)"
                    contenteditable="plaintext-only"
                    role="textbox"
                    aria-multiline="true"
                    aria-label="Text des aktiven PDF-Blocks bearbeiten"
                    @input="onInlineInput"
                    @keydown.esc.prevent="finishEdit"
                    @keydown.stop
                  ></div>
                  <button type="button" class="absolute -left-3 -top-3 grid h-7 w-7 touch-none place-items-center rounded-full bg-primary-600 text-xs text-white shadow-sm" aria-label="Textblock verschieben" @pointerdown.prevent="startPointerDrag('move', $event, width, height)">✥</button>
                  <button type="button" class="absolute -bottom-3 -right-3 grid h-7 w-7 touch-none place-items-center rounded-full bg-primary-600 text-xs text-white shadow-sm" aria-label="Textblockgröße ändern" @pointerdown.prevent="startPointerDrag('resize', $event, width, height)">⇲</button>
                </div>

                <UiPanel padding="sm" class="absolute z-10 flex items-center gap-1 bg-white/95 text-xs dark:bg-gray-900/95" :style="toolbarStyle(active.box, width, height)" @pointerdown.prevent>
                  <UiIconButton size="sm" aria-label="Schrift verkleinern" @click="changeSize(-0.5)">A−</UiIconButton>
                  <span class="w-10 text-center tabular-nums">{{ active.font_size.toFixed(1) }}</span>
                  <UiIconButton size="sm" aria-label="Schrift vergrößern" @click="changeSize(0.5)">A+</UiIconButton>
                  <UiButton size="sm" :variant="isBold ? 'primary' : 'secondary'" :aria-pressed="isBold" @click="toggleBold">Fett</UiButton>
                  <input v-model="active.color" type="color" class="h-9 w-10 rounded-xl" aria-label="Schriftfarbe" />
                  <UiButton variant="danger" size="sm" @click="clearText">Leeren</UiButton>
                  <UiButton size="sm" @click="finishEdit">Fertig</UiButton>
                </UiPanel>
              </template>
            </template>
          </PdfViewer>
        </div>

        <div class="space-y-4">
          <UiPanel v-if="active" class="space-y-4">
            <h3 class="font-semibold">Aktiver Textblock</h3>
            <UiField label="Text" for-id="text-editor-content"><textarea id="text-editor-content" :value="active.text" rows="5" maxlength="100000" class="ui-control w-full" @input="onPanelInput"></textarea></UiField>
            <div class="grid grid-cols-2 gap-3">
              <UiField label="X (%)" for-id="text-editor-x"><input id="text-editor-x" :value="geometryValue('x')" type="number" min="0" max="99" step="0.5" class="ui-control w-full" @input="setGeometry('x', $event)" /></UiField>
              <UiField label="Y (%)" for-id="text-editor-y"><input id="text-editor-y" :value="geometryValue('y')" type="number" min="0" max="99" step="0.5" class="ui-control w-full" @input="setGeometry('y', $event)" /></UiField>
              <UiField label="Breite (%)" for-id="text-editor-width"><input id="text-editor-width" :value="geometryValue('width')" type="number" min="1" max="100" step="0.5" class="ui-control w-full" @input="setGeometry('width', $event)" /></UiField>
              <UiField label="Höhe (%)" for-id="text-editor-height"><input id="text-editor-height" :value="geometryValue('height')" type="number" min="1" max="100" step="0.5" class="ui-control w-full" @input="setGeometry('height', $event)" /></UiField>
            </div>
            <UiField label="Schriftgröße" for-id="text-editor-font"><input id="text-editor-font" v-model.number="active.font_size" type="number" min="5" max="72" step="0.5" class="ui-control w-full" @change="commitActive" /></UiField>
            <div class="flex gap-2"><UiButton :variant="isBold ? 'primary' : 'secondary'" :aria-pressed="isBold" @click="toggleBold">Fett</UiButton><UiButton @click="finishEdit">Bearbeitung beenden</UiButton></div>
          </UiPanel>

          <UiAlert v-else tone="info">Textblock auf der Seite oder in der Änderungsliste auswählen.</UiAlert>

          <UiPanel v-if="editCount" class="space-y-2">
            <h3 class="font-semibold">Offene Änderungen</h3>
            <ul class="max-h-72 space-y-1 overflow-y-auto">
              <li v-for="[key, edit] in editEntries" :key="key" class="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-black/5 dark:hover:bg-white/10">
                <UiButton variant="ghost" size="sm" class="min-w-0 flex-1 justify-start" @click="openEdit(key)"><span class="truncate">{{ edit.text.trim() ? edit.text.slice(0, 50) : '(Block wird geleert)' }}</span><span class="shrink-0 text-xs opacity-70">S. {{ edit.page }}</span></UiButton>
                <UiIconButton size="sm" variant="danger" aria-label="Änderung verwerfen" @click="discardEdit(key)">×</UiIconButton>
              </li>
            </ul>
          </UiPanel>
        </div>
      </div>
    </template>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
/**
 * Textbearbeitung mit direkter Seitenvorschau und gleichwertiger
 * Tastaturalternative. Dokument-, Seiten- und Renderwechsel entwerten ältere
 * Textblockantworten; globale Pointerlistener werden vollständig entfernt.
 */
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import WorkSessionBar from '@/components/WorkSessionBar.vue'
import { useNotifications } from '@/composables/useNotifications'
import { apiPost, downloadBlob } from '@/lib/api'

const PdfViewer = defineAsyncComponent(() => import('@/components/PdfViewer.vue'))
defineEmits<{ (event: 'back'): void }>()

interface Box { x0: number; y0: number; x1: number; y1: number }
interface Block { text: string; bbox: Box; font_size: number; font_name: string; color: string }
interface Edit { page: number; bbox: Box; text: string; font_size: number; color: string; font: string }
interface ActiveEdit { key: string; page: number; box: Box; text: string; font_size: number; color: string; font: string }

const notifications = useNotifications()
const file = ref<File | null>(null)
const workingBlob = ref<Blob | null>(null)
const workingName = ref('dokument.pdf')
const page = ref(1)
const pageCount = ref(1)
const blocks = ref<Block[]>([])
const loadingPage = ref(false)
const applying = ref(false)
const error = ref<string | null>(null)
const warnings = ref(0)
const edits = ref<Map<string, Edit>>(new Map())
const active = ref<ActiveEdit | null>(null)
const editorEl = ref<HTMLElement | null>(null)
const pendingOpenKey = ref<string | null>(null)
let documentGeneration = 0
let blockRequest = 0
let blockController: AbortController | null = null
let dragCleanup: (() => void) | null = null
let ignoreNextFileReset = false

const editCount = computed(() => edits.value.size)
const editEntries = computed(() => [...edits.value.entries()].sort((a, b) => a[1].page - b[1].page || a[0].localeCompare(b[0])))
const activeKey = computed(() => active.value?.key ?? '')
const isBold = computed(() => /bold/i.test(active.value?.font ?? ''))
const sessionState = computed(() => ({ edits: [...edits.value.entries()], page: page.value }))

function clamp(value: number, min = 0, max = 1): number { return Math.max(min, Math.min(max, value)) }
function validBox(value: unknown): Box | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  const values = [Number(raw.x0), Number(raw.y0), Number(raw.x1), Number(raw.y1)]
  if (!values.every(Number.isFinite)) return null
  const [rawX0, rawY0, rawX1, rawY1] = values
  const x0 = clamp(rawX0); const y0 = clamp(rawY0); const x1 = clamp(rawX1); const y1 = clamp(rawY1)
  return x1 > x0 && y1 > y0 ? { x0, y0, x1, y1 } : null
}
function editKey(pageNumber: number, blockIndex: number): string { return `${pageNumber}:${blockIndex}` }
function normalizeBlocks(value: unknown): Block[] {
  const source = value && typeof value === 'object' && 'blocks' in value ? (value as { blocks?: unknown }).blocks : []
  if (!Array.isArray(source)) return []
  return source.slice(0, 5000).flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const raw = item as Record<string, unknown>; const bbox = validBox(raw.bbox); if (!bbox) return []
    return [{ text: String(raw.text ?? '').slice(0, 100000), bbox, font_size: clamp(Number(raw.font_size) || 11, 5, 72), font_name: String(raw.font_name ?? ''), color: String(raw.color ?? '#000000') }]
  })
}
function normalizeSessionEdits(value: unknown): Map<string, Edit> {
  const result = new Map<string, Edit>()
  if (!Array.isArray(value)) return result
  for (const item of value.slice(0, 5000)) {
    if (!Array.isArray(item) || item.length !== 2 || typeof item[0] !== 'string' || !item[1] || typeof item[1] !== 'object') continue
    const raw = item[1] as Record<string, unknown>; const bbox = validBox(raw.bbox); if (!bbox) continue
    result.set(item[0], { page: Math.max(1, Math.trunc(Number(raw.page) || 1)), bbox, text: String(raw.text ?? '').slice(0, 100000), font_size: clamp(Number(raw.font_size) || 11, 5, 72), color: String(raw.color ?? '#000000'), font: String(raw.font ?? '') })
  }
  return result
}

function restoreSession(payload: { name: string; blob: Blob; state: unknown }): void {
  documentGeneration += 1; blockRequest += 1; blockController?.abort(); finishEdit(); cleanupDrag()
  if (file.value) { ignoreNextFileReset = true; file.value = null }
  workingBlob.value = payload.blob; workingName.value = payload.name
  const state = payload.state && typeof payload.state === 'object' ? payload.state as { edits?: unknown; page?: number } : null
  edits.value = normalizeSessionEdits(state?.edits); page.value = Math.max(1, Math.trunc(Number(state?.page) || 1)); blocks.value = []; warnings.value = 0; error.value = null
}

watch(file, (currentFile) => {
  if (ignoreNextFileReset) { ignoreNextFileReset = false; return }
  documentGeneration += 1; blockRequest += 1; blockController?.abort(); finishEdit(); cleanupDrag(); blocks.value = []; edits.value = new Map(); page.value = 1; warnings.value = 0; error.value = null; pendingOpenKey.value = null
  if (!currentFile) { workingBlob.value = null; return }
  workingBlob.value = currentFile; workingName.value = currentFile.name
})
watch(page, () => { blockRequest += 1; blockController?.abort(); finishEdit(); blocks.value = []; error.value = null })
watch(() => active.value?.color, () => commitActive())

function onDocumentLoaded(count: number): void { pageCount.value = Math.max(1, count); page.value = Math.min(page.value, pageCount.value) }

async function loadBlocks(renderedPage: number): Promise<void> {
  const blob = workingBlob.value
  if (!blob || renderedPage !== page.value) return
  const requestId = ++blockRequest; const generation = documentGeneration; const currentPage = page.value
  blockController?.abort(); const controller = new AbortController(); blockController = controller
  loadingPage.value = true; active.value = null; error.value = null
  try {
    const formData = new FormData(); formData.append('file', blob, workingName.value); formData.append('page', String(currentPage))
    const response = await apiPost('/api/pdf-editor/text-blocks', formData, { signal: controller.signal, notifyOnError: false })
    const normalized = normalizeBlocks(await response.json())
    if (requestId !== blockRequest || generation !== documentGeneration || workingBlob.value !== blob || page.value !== currentPage) return
    blocks.value = normalized
    const key = pendingOpenKey.value
    if (key?.startsWith(`${currentPage}:`)) {
      pendingOpenKey.value = null
      const index = Number(key.split(':')[1])
      if (Number.isInteger(index)) await startEdit(index)
    }
  } catch (caught: unknown) {
    if (!controller.signal.aborted && requestId === blockRequest && generation === documentGeneration) {
      error.value = caught instanceof Error ? caught.message : 'Textblöcke konnten nicht geladen werden.'
      notifications.error('Textblöcke nicht geladen', error.value)
    }
  } finally {
    if (requestId === blockRequest) loadingPage.value = false
    if (blockController === controller) blockController = null
  }
}

function boxOf(index: number): Box { return edits.value.get(editKey(page.value, index))?.bbox ?? blocks.value[index]?.bbox ?? { x0: 0, y0: 0, x1: .1, y1: .05 } }
function boxStyle(box: Box, width: number, height: number): Record<string, string> { return { left: `${box.x0 * width}px`, top: `${box.y0 * height}px`, width: `${Math.max(4, (box.x1 - box.x0) * width)}px`, height: `${Math.max(4, (box.y1 - box.y0) * height)}px` } }
function toolbarStyle(box: Box, width: number, height: number): Record<string, string> { return { left: `${Math.min(Math.max(0, box.x0 * width), Math.max(0, width - 360))}px`, top: `${Math.max(0, box.y0 * height - 48)}px` } }
function textStyle(edit: Pick<Edit, 'font_size' | 'color' | 'font'>, scale: number): Record<string, string> { return { fontSize: `${edit.font_size * scale}px`, color: edit.color || '#000000', fontWeight: /bold/i.test(edit.font) ? '700' : '400', fontFamily: /courier|mono/i.test(edit.font) ? 'monospace' : /times|serif|roman/i.test(edit.font) ? 'serif' : 'sans-serif' } }
function blockClass(index: number): string { return edits.value.has(editKey(page.value, index)) ? 'border-emerald-500 bg-emerald-400/10 hover:bg-emerald-400/20' : 'border-primary-400/70 bg-transparent hover:bg-primary-300/20' }

async function startEdit(index: number): Promise<void> {
  finishEdit(); const block = blocks.value[index]; if (!block) return
  const key = editKey(page.value, index); const pending = edits.value.get(key)
  active.value = { key, page: page.value, box: { ...(pending?.bbox ?? block.bbox) }, text: pending?.text ?? block.text, font_size: pending?.font_size ?? block.font_size, color: pending?.color ?? block.color, font: pending?.font ?? block.font_name }
  await nextTick(); if (!editorEl.value || !active.value) return
  editorEl.value.textContent = active.value.text; editorEl.value.focus()
  const range = document.createRange(); range.selectNodeContents(editorEl.value); range.collapse(false)
  const selection = window.getSelection(); selection?.removeAllRanges(); selection?.addRange(range)
}
function openEdit(key: string): void {
  const [pagePart, indexPart] = key.split(':'); const targetPage = Number(pagePart); const index = Number(indexPart)
  if (!Number.isInteger(targetPage) || !Number.isInteger(index)) return
  if (targetPage === page.value && blocks.value[index]) void startEdit(index)
  else { pendingOpenKey.value = key; page.value = targetPage }
}
function onInlineInput(): void { if (!active.value || !editorEl.value) return; active.value.text = editorEl.value.textContent ?? ''; commitActive() }
function onPanelInput(event: Event): void { if (!active.value) return; active.value.text = (event.target as HTMLTextAreaElement).value; if (editorEl.value) editorEl.value.textContent = active.value.text; commitActive() }
function originalForActive(): Block | null { const index = Number(active.value?.key.split(':')[1]); return Number.isFinite(index) ? blocks.value[index] ?? null : null }
function commitActive(): void {
  const current = active.value; if (!current) return; const original = originalForActive()
  const unchanged = original && current.text === original.text && current.font_size === original.font_size && current.color === original.color && current.font === original.font_name && JSON.stringify(current.box) === JSON.stringify(original.bbox)
  if (unchanged) edits.value.delete(current.key)
  else edits.value.set(current.key, { page: current.page, bbox: { ...current.box }, text: current.text, font_size: current.font_size, color: current.color, font: current.font })
  edits.value = new Map(edits.value)
}
function finishEdit(): void { if (!active.value) return; commitActive(); active.value = null }
function changeSize(delta: number): void { if (!active.value) return; active.value.font_size = clamp(active.value.font_size + delta, 5, 72); commitActive() }
function toggleBold(): void { if (!active.value) return; const font = active.value.font || 'Helvetica'; active.value.font = isBold.value ? font.replace(/[-,]?bold/gi, '') || 'Helvetica' : `${font}-Bold`; commitActive() }
function clearText(): void { if (!active.value) return; active.value.text = ''; if (editorEl.value) editorEl.value.textContent = ''; commitActive() }
function discardEdit(key: string): void { edits.value.delete(key); edits.value = new Map(edits.value); if (active.value?.key === key) active.value = null }

function geometryValue(key: 'x' | 'y' | 'width' | 'height'): number { if (!active.value) return 0; const box = active.value.box; const value = key === 'x' ? box.x0 : key === 'y' ? box.y0 : key === 'width' ? box.x1 - box.x0 : box.y1 - box.y0; return Math.round(value * 1000) / 10 }
function setGeometry(key: 'x' | 'y' | 'width' | 'height', event: Event): void {
  if (!active.value) return; const value = Number((event.target as HTMLInputElement).value) / 100; if (!Number.isFinite(value)) return
  const box = active.value.box; const width = box.x1 - box.x0; const height = box.y1 - box.y0
  if (key === 'x') { box.x0 = clamp(value, 0, 1 - width); box.x1 = box.x0 + width }
  else if (key === 'y') { box.y0 = clamp(value, 0, 1 - height); box.y1 = box.y0 + height }
  else if (key === 'width') box.x1 = clamp(box.x0 + Math.max(.01, value), box.x0 + .01, 1)
  else box.y1 = clamp(box.y0 + Math.max(.01, value), box.y0 + .01, 1)
  commitActive()
}

function cleanupDrag(): void { dragCleanup?.(); dragCleanup = null }
function startPointerDrag(mode: 'move' | 'resize', event: PointerEvent, width: number, height: number): void {
  const current = active.value; if (!current) return; cleanupDrag()
  const startX = event.clientX; const startY = event.clientY; const start = { ...current.box }
  const move = (pointerEvent: PointerEvent) => {
    if (!active.value) return
    const dx = (pointerEvent.clientX - startX) / Math.max(1, width); const dy = (pointerEvent.clientY - startY) / Math.max(1, height)
    if (mode === 'move') { const boxWidth = start.x1 - start.x0; const boxHeight = start.y1 - start.y0; const x0 = clamp(start.x0 + dx, 0, 1 - boxWidth); const y0 = clamp(start.y0 + dy, 0, 1 - boxHeight); active.value.box = { x0, y0, x1: x0 + boxWidth, y1: y0 + boxHeight } }
    else active.value.box = { ...start, x1: clamp(start.x1 + dx, start.x0 + .02, 1), y1: clamp(start.y1 + dy, start.y0 + .01, 1) }
  }
  const end = () => { cleanupDrag(); commitActive() }
  window.addEventListener('pointermove', move); window.addEventListener('pointerup', end, { once: true }); window.addEventListener('pointercancel', end, { once: true })
  dragCleanup = () => { window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', end); window.removeEventListener('pointercancel', end) }
}

async function applyEdits(): Promise<void> {
  const blob = workingBlob.value; if (!blob || !edits.value.size || applying.value) return
  finishEdit(); const generation = documentGeneration; applying.value = true; error.value = null
  try {
    const formData = new FormData(); formData.append('file', blob, workingName.value); formData.append('edits', JSON.stringify([...edits.value.values()]))
    const response = await apiPost('/api/pdf-extras/edit-text-blocks', formData); const newBlob = await response.blob()
    if (generation !== documentGeneration || workingBlob.value !== blob) return
    warnings.value = Number(response.headers.get('X-Warnings') || 0); workingBlob.value = newBlob; blocks.value = []; edits.value = new Map(); active.value = null
  } catch (caught: unknown) { if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Anwenden fehlgeschlagen.' }
  finally { if (generation === documentGeneration) applying.value = false }
}
async function download(): Promise<void> { if (!workingBlob.value) return; await downloadBlob(new Response(workingBlob.value), workingName.value.replace(/\.pdf$/i, '_bearbeitet.pdf')) }
function reset(): void { documentGeneration += 1; blockRequest += 1; blockController?.abort(); cleanupDrag(); file.value = null; workingBlob.value = null; blocks.value = []; edits.value = new Map(); active.value = null; pendingOpenKey.value = null; warnings.value = 0; page.value = 1; pageCount.value = 1; error.value = null }

onBeforeUnmount(() => { documentGeneration += 1; blockController?.abort(); cleanupDrag() })
</script>
