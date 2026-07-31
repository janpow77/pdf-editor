<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3 flex-wrap">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Text bearbeiten</h2>
    </div>

    <div v-if="!workingBlob" class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Textblock auf der Seite anklicken und <strong>direkt an Ort und Stelle tippen</strong> —
      Schriftgröße, Fettung und Farbe über die kleine Leiste am Block, Position und Größe
      über die Griffe. Grenze gegenüber Adobe Acrobat: Der Text bleibt in seinem Block,
      es gibt keinen Umbruch über Absätze und Seiten hinweg.
    </div>

    <WorkSessionBar
      tool="textEditor"
      :blob="workingBlob"
      :name="workingName"
      :state="sessionState"
      :change-count="editCount"
      @restore="restoreSession"
    />

    <FileDrop v-if="!workingBlob" v-model="file" />

    <template v-if="workingBlob">
      <!-- Werkzeugleiste -->
      <div class="flex items-center gap-2 flex-wrap bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <span class="text-sm text-gray-500 dark:text-gray-400">{{ editCount }} Änderung(en) ausstehend</span>

        <span class="flex-1"></span>
        <button
          class="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="applying || editCount === 0"
          @click="applyEdits"
        >
          {{ applying ? 'Wende an…' : 'Änderungen anwenden' }}
        </button>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-primary-600 text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 disabled:opacity-50"
          :disabled="editCount > 0"
          :title="editCount > 0 ? 'Erst Änderungen anwenden' : ''"
          @click="download"
        >
          Herunterladen
        </button>
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="reset">
          Neues Dokument
        </button>
      </div>

      <div v-if="warnings" class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300">
        Hinweis: {{ warnings }} Textbox(en) waren zu klein — die Schrift wurde verkleinert.
      </div>

      <div class="grid lg:grid-cols-3 gap-4">
        <!-- Seitenansicht mit Direktbearbeitung -->
        <div class="lg:col-span-2">
          <PdfViewer
            v-model="page"
            :source="workingBlob"
            @loaded="pageCount = $event"
            @rendered="loadBlocks"
          >
            <template #overlay="{ width, height, scale }">
              <!-- Nicht bearbeitete Blöcke: anklickbar -->
              <button
                v-for="(b, i) in blocks"
                v-show="editKey(i) !== activeKey"
                :key="`block-${i}`"
                class="absolute border transition-colors"
                :class="blockClass(i)"
                :style="boxStyle(boxOf(i), width, height)"
                :title="`Bearbeiten: ${b.text.slice(0, 80)}`"
                :aria-label="`Textblock ${i + 1} bearbeiten: ${b.text.slice(0, 60)}`"
                @click="startEdit(i, scale)"
              >
                <!-- Vorgemerkter Text deckt das Original ab (Live-Vorschau) -->
                <span
                  v-if="edits.has(editKey(i))"
                  class="absolute inset-0 bg-white dark:bg-white text-left overflow-hidden whitespace-pre-wrap break-words px-[1px] leading-tight"
                  :style="textStyle(edits.get(editKey(i))!, scale)"
                >{{ edits.get(editKey(i))!.text }}</span>
              </button>

              <!-- Aktiver Block: direkt auf der Seite tippen -->
              <template v-if="active">
                <div
                  class="absolute ring-2 ring-primary-500 bg-white shadow-lg"
                  :style="boxStyle(active.box, width, height)"
                >
                  <div
                    ref="editorEl"
                    class="w-full h-full outline-none overflow-hidden whitespace-pre-wrap break-words px-[1px] leading-tight cursor-text"
                    :style="textStyle(active, scale)"
                    contenteditable="plaintext-only"
                    role="textbox"
                    aria-multiline="true"
                    aria-label="Text an dieser Stelle bearbeiten"
                    @input="onInput"
                    @keydown.esc.prevent="finishEdit"
                    @keydown.stop
                  ></div>

                  <!-- Griff: verschieben -->
                  <span
                    class="absolute -top-2.5 -left-2.5 w-5 h-5 rounded-full bg-primary-600 cursor-move flex items-center justify-center text-[10px] text-white"
                    title="Block verschieben"
                    @mousedown.prevent="startDrag('move', $event, width, height)"
                  >✥</span>
                  <!-- Griff: Größe ändern -->
                  <span
                    class="absolute -bottom-2.5 -right-2.5 w-5 h-5 rounded-full bg-primary-600 cursor-nwse-resize flex items-center justify-center text-[10px] text-white"
                    title="Blockgröße ändern"
                    @mousedown.prevent="startDrag('resize', $event, width, height)"
                  >⇲</span>
                </div>

                <!-- Schwebende Leiste über dem Block -->
                <div
                  class="absolute z-10 flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-1 shadow-lg text-xs"
                  :style="toolbarStyle(active.box, width, height)"
                  @mousedown.prevent
                >
                  <button class="px-1.5 py-0.5 rounded hover:bg-gray-100" title="Schrift kleiner" @click="changeSize(-0.5)">A−</button>
                  <span class="tabular-nums w-8 text-center text-gray-600 dark:text-gray-400">{{ active.font_size.toFixed(1) }}</span>
                  <button class="px-1.5 py-0.5 rounded hover:bg-gray-100" title="Schrift größer" @click="changeSize(0.5)">A+</button>
                  <span class="mx-1 h-4 w-px bg-gray-200"></span>
                  <button
                    class="px-1.5 py-0.5 rounded font-bold"
                    :class="isBold ? 'bg-primary-100 text-primary-700' : 'hover:bg-gray-100'"
                    title="Fett"
                    @click="toggleBold"
                  >F</button>
                  <input
                    v-model="active.color"
                    type="color"
                    class="w-6 h-6 rounded border border-gray-200 bg-white p-0"
                    title="Schriftfarbe"
                    aria-label="Schriftfarbe"
                  />
                  <span class="mx-1 h-4 w-px bg-gray-200"></span>
                  <button class="px-1.5 py-0.5 rounded text-red-600 hover:bg-red-50" title="Text löschen" @click="clearText">Leeren</button>
                  <button class="px-1.5 py-0.5 rounded hover:bg-gray-100" title="Bearbeitung beenden (Esc)" @click="finishEdit">Fertig</button>
                </div>
              </template>
            </template>
          </PdfViewer>
        </div>

        <!-- Übersicht der Änderungen -->
        <div class="space-y-3">
          <div class="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl text-sm text-gray-600 dark:text-gray-300">
            <p class="font-medium text-gray-900 dark:text-white mb-1">Direkt auf der Seite bearbeiten</p>
            <p>
              Blauer Rahmen = Textblock, grün = geändert. Anklicken und tippen; Esc oder
              „Fertig" beendet. Die Seite zeigt Ihre Änderungen sofort — geschrieben wird
              die Datei erst mit „Änderungen anwenden".
            </p>
          </div>

          <div v-if="editCount" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">Offene Änderungen</h3>
            <ul class="text-sm divide-y divide-gray-100 dark:divide-gray-700 max-h-64 overflow-y-auto">
              <li v-for="[key, edit] in [...edits.entries()]" :key="key" class="py-1.5 flex items-start justify-between gap-2">
                <span class="truncate text-gray-700 dark:text-gray-300">
                  {{ edit.text.trim() ? edit.text.slice(0, 40) : '(Block wird geleert)' }}
                </span>
                <span class="shrink-0 flex items-center gap-2">
                  <span class="text-xs text-gray-600 dark:text-gray-400">S. {{ edit.page }}</span>
                  <button class="text-xs text-red-500 hover:text-red-700" title="Änderung verwerfen" @click="discardEdit(key)">✕</button>
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </template>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * Live-Textbearbeitung: Der Text wird direkt auf der gerenderten Seite
 * getippt (contenteditable in Seitenkoordinaten), nicht in einem Seitenpanel.
 *
 * Bewusste Grenze: Geschrieben wird die Datei weiterhin serverseitig
 * (PyMuPDF). Der Browser zeigt die Änderung sofort an derselben Stelle in
 * derselben Größe — der eigentliche Schreibvorgang bleibt an einer Stelle,
 * statt eine zweite PDF-Schreibimplementierung im Browser zu pflegen.
 */
import { computed, defineAsyncComponent, nextTick, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
// pdf.js wiegt rund 370 kB. Als asynchrone Komponente erscheint die
// Werkzeug-Oberfläche sofort; der Viewer wird parallel nachgeladen und
// erst gebraucht, wenn tatsächlich ein Dokument geöffnet ist.
const PdfViewer = defineAsyncComponent(() => import('@/components/PdfViewer.vue'))
import WorkSessionBar from '@/components/WorkSessionBar.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface Box {
  x0: number
  y0: number
  x1: number
  y1: number
}

interface Block {
  text: string
  bbox: Box
  font_size: number
  font_name: string
  color: string
}

interface Edit {
  page: number
  bbox: Box
  text: string
  font_size: number
  color: string
  // Schriftname des Originalblocks — das Backend bettet eine dazu passende
  // Schrift ein, damit Umlaute und Sonderzeichen erhalten bleiben
  font: string
}

/** Aktiver Block während der Direktbearbeitung */
interface ActiveEdit extends Edit {
  key: string
  box: Box
}

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
const edits = ref(new Map<string, Edit>())
const active = ref<ActiveEdit | null>(null)
const editorEl = ref<HTMLElement | null>(null)

const editCount = computed(() => edits.value.size)
const activeKey = computed(() => active.value?.key ?? '')
const isBold = computed(() => /bold/i.test(active.value?.font ?? ''))

// Für „Bearbeitung unterbrechen": offene Änderungen + Seite sichern
const sessionState = computed(() => ({
  edits: [...edits.value.entries()],
  page: page.value,
}))

function restoreSession(payload: { name: string; blob: Blob; state: unknown }) {
  workingBlob.value = payload.blob
  workingName.value = payload.name
  const state = payload.state as { edits?: [string, Edit][]; page?: number } | null
  edits.value = new Map(state?.edits ?? [])
  page.value = state?.page && state.page > 0 ? state.page : 1
  active.value = null
  error.value = null
}

watch(file, async (f) => {
  if (!f) return
  workingBlob.value = f
  workingName.value = f.name
  edits.value = new Map()
  page.value = 1
  error.value = null
})

function editKey(blockIdx: number): string {
  return `${page.value}:${blockIdx}`
}

async function loadBlocks() {
  if (!workingBlob.value) return
  loadingPage.value = true
  active.value = null
  error.value = null
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    fd.append('page', String(page.value))
    const resp = await apiPost('/api/pdf-editor/text-blocks', fd)
    blocks.value = (await resp.json()).blocks
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Textblöcke laden fehlgeschlagen'
  } finally {
    loadingPage.value = false
  }
}

// ── Darstellung in Seitenkoordinaten ────────────────────────

function boxOf(i: number): Box {
  return edits.value.get(editKey(i))?.bbox ?? blocks.value[i].bbox
}

function boxStyle(box: Box, width: number, height: number) {
  return {
    left: `${box.x0 * width}px`,
    top: `${box.y0 * height}px`,
    width: `${Math.max(4, (box.x1 - box.x0) * width)}px`,
    height: `${Math.max(4, (box.y1 - box.y0) * height)}px`,
  }
}

function toolbarStyle(box: Box, width: number, height: number) {
  // Über dem Block, an der Seitenkante gehalten
  const top = Math.max(0, box.y0 * height - 34)
  const left = Math.min(Math.max(0, box.x0 * width), Math.max(0, width - 300))
  return { left: `${left}px`, top: `${top}px` }
}

function textStyle(edit: Edit, scale: number) {
  return {
    fontSize: `${edit.font_size * scale}px`,
    color: edit.color || '#000000',
    fontWeight: /bold/i.test(edit.font) ? '700' : '400',
    fontFamily: /courier|mono/i.test(edit.font)
      ? 'monospace'
      : /times|serif|roman/i.test(edit.font)
        ? 'serif'
        : 'sans-serif',
  }
}

function blockClass(i: number) {
  if (edits.value.has(editKey(i)))
    return 'border-green-500 bg-green-400/10 hover:bg-green-400/20'
  return 'border-blue-400/70 bg-transparent hover:bg-blue-300/20'
}

// ── Direktbearbeitung ───────────────────────────────────────

async function startEdit(i: number, _scale: number) {
  finishEdit()
  const key = editKey(i)
  const pending = edits.value.get(key)
  const block = blocks.value[i]
  active.value = {
    key,
    page: page.value,
    bbox: pending?.bbox ?? { ...block.bbox },
    box: pending?.bbox ?? { ...block.bbox },
    text: pending?.text ?? block.text,
    font_size: pending?.font_size ?? block.font_size ?? 11,
    color: pending?.color ?? block.color ?? '#000000',
    font: pending?.font ?? block.font_name ?? '',
  }
  await nextTick()
  if (editorEl.value) {
    editorEl.value.textContent = active.value.text
    editorEl.value.focus()
    // Cursor ans Ende setzen
    const range = document.createRange()
    range.selectNodeContents(editorEl.value)
    range.collapse(false)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
  }
}

function onInput() {
  if (!active.value || !editorEl.value) return
  active.value.text = editorEl.value.textContent ?? ''
  commitActive()
}

function commitActive() {
  const a = active.value
  if (!a) return
  const original = blocks.value[Number(a.key.split(':')[1])]
  const unchanged =
    original &&
    a.text === original.text &&
    a.font_size === (original.font_size || 11) &&
    a.color === (original.color || '#000000') &&
    a.font === (original.font_name || '') &&
    a.box.x0 === original.bbox.x0 &&
    a.box.y0 === original.bbox.y0 &&
    a.box.x1 === original.bbox.x1 &&
    a.box.y1 === original.bbox.y1
  if (unchanged) {
    edits.value.delete(a.key)
  } else {
    edits.value.set(a.key, {
      page: a.page,
      bbox: { ...a.box },
      text: a.text,
      font_size: a.font_size,
      color: a.color,
      font: a.font,
    })
  }
  edits.value = new Map(edits.value)
}

function finishEdit() {
  if (!active.value) return
  commitActive()
  active.value = null
}

function changeSize(delta: number) {
  if (!active.value) return
  active.value.font_size = Math.max(5, Math.min(72, active.value.font_size + delta))
  commitActive()
}

function toggleBold() {
  if (!active.value) return
  const font = active.value.font || 'Helvetica'
  active.value.font = isBold.value ? font.replace(/[-,]?bold/gi, '') : `${font}-Bold`
  commitActive()
}

watch(
  () => active.value?.color,
  () => commitActive(),
)

function clearText() {
  if (!active.value) return
  active.value.text = ''
  if (editorEl.value) editorEl.value.textContent = ''
  commitActive()
}

function discardEdit(key: string) {
  edits.value.delete(key)
  edits.value = new Map(edits.value)
  if (active.value?.key === key) active.value = null
}

// ── Verschieben und Größe ändern ────────────────────────────

function startDrag(mode: 'move' | 'resize', event: MouseEvent, width: number, height: number) {
  const a = active.value
  if (!a) return
  const startX = event.clientX
  const startY = event.clientY
  const start = { ...a.box }
  const clamp = (v: number) => Math.max(0, Math.min(1, v))

  const onMove = (e: MouseEvent) => {
    const dx = (e.clientX - startX) / width
    const dy = (e.clientY - startY) / height
    if (!active.value) return
    if (mode === 'move') {
      const w = start.x1 - start.x0
      const h = start.y1 - start.y0
      const x0 = clamp(start.x0 + dx)
      const y0 = clamp(start.y0 + dy)
      active.value.box = { x0, y0, x1: clamp(x0 + w), y1: clamp(y0 + h) }
    } else {
      active.value.box = {
        ...start,
        x1: clamp(Math.max(start.x0 + 0.02, start.x1 + dx)),
        y1: clamp(Math.max(start.y0 + 0.01, start.y1 + dy)),
      }
    }
  }
  const onUp = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
    commitActive()
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

// ── Anwenden, Herunterladen, Zurücksetzen ───────────────────

async function applyEdits() {
  if (!workingBlob.value || edits.value.size === 0) return
  finishEdit()
  applying.value = true
  error.value = null
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    fd.append('edits', JSON.stringify([...edits.value.values()]))
    const resp = await apiPost('/api/pdf-extras/edit-text-blocks', fd)
    warnings.value = Number(resp.headers.get('X-Warnings') || 0)
    workingBlob.value = await resp.blob()
    edits.value = new Map()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Anwenden fehlgeschlagen'
  } finally {
    applying.value = false
  }
}

async function download() {
  if (!workingBlob.value) return
  const name = workingName.value.replace(/\.pdf$/i, '_bearbeitet.pdf')
  const resp = new Response(workingBlob.value, {
    headers: { 'Content-Disposition': `attachment; filename="${name}"` },
  })
  await downloadBlob(resp, name)
}

function reset() {
  file.value = null
  workingBlob.value = null
  blocks.value = []
  edits.value = new Map()
  active.value = null
  warnings.value = 0
  error.value = null
}
</script>
