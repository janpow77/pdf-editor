<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3 flex-wrap">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Anmerkungen (interaktiv)</h2>
    </div>

    <div v-if="!workingBlob" class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Werkzeug wählen und direkt auf der Seite zeichnen: Markieren, Rechteck, Linie,
      Freitext, Kommentar, Stempel, Freihand und Schwärzen. „Anwenden" schreibt alles
      ins Dokument.
    </div>

    <FileDrop v-if="!workingBlob" v-model="file" />

    <template v-if="workingBlob">
      <!-- Werkzeugleiste -->
      <div class="flex items-center gap-2 flex-wrap bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <button
          v-for="t in tools"
          :key="t.id"
          class="px-2.5 py-1.5 text-sm rounded-lg border transition-colors"
          :class="tool === t.id
            ? 'border-primary-600 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
            : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'"
          :title="t.label"
          @click="tool = t.id"
        >
          {{ t.icon }} {{ t.label }}
        </button>
        <input v-model="color" type="color" class="w-8 h-8 rounded cursor-pointer border border-gray-300 dark:border-gray-600" title="Farbe" />
        <select v-if="tool === 'stamp'" v-model="stampText" class="text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-gray-900 dark:text-white">
          <option>ENTWURF</option>
          <option>VERTRAULICH</option>
          <option>GEPRÜFT</option>
          <option>GENEHMIGT</option>
          <option>KOPIE</option>
        </select>
      </div>

      <div class="flex items-center gap-2 flex-wrap bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <button class="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-40" :disabled="page <= 1" @click="goToPage(page - 1)">←</button>
        <span class="text-sm text-gray-700 dark:text-gray-300">Seite {{ page }} / {{ pageCount }}</span>
        <button class="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-40" :disabled="page >= pageCount" @click="goToPage(page + 1)">→</button>
        <span class="mx-2 text-gray-300 dark:text-gray-600">|</span>
        <span class="text-sm text-gray-500 dark:text-gray-400">{{ pending.length }} Anmerkung(en) ausstehend</span>
        <button v-if="pending.length" class="text-sm text-red-500 hover:text-red-700" @click="undoLast">Letzte rückgängig</button>
        <span class="flex-1"></span>
        <button
          class="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="applying || pending.length === 0"
          @click="applyAnnotations"
        >
          {{ applying ? 'Wende an…' : 'Anwenden' }}
        </button>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-primary-600 text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 disabled:opacity-50"
          :disabled="pending.length > 0"
          :title="pending.length > 0 ? 'Erst Anmerkungen anwenden' : ''"
          @click="download"
        >
          Herunterladen
        </button>
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="reset">
          Neues Dokument
        </button>
      </div>

      <div v-if="loadingPage" class="text-sm text-gray-500 py-8 text-center">Lade Seite…</div>
      <div
        v-else-if="pageImage"
        ref="canvasBox"
        class="relative inline-block w-full border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden bg-white select-none"
        :class="tool === 'select' ? 'cursor-default' : 'cursor-crosshair'"
        @mousedown.prevent="onDown"
        @mousemove.prevent="onMove"
        @mouseup.prevent="onUp"
        @mouseleave="onUp"
      >
        <img :src="`data:image/png;base64,${pageImage}`" class="w-full pointer-events-none" alt="PDF-Seite" draggable="false" />
        <!-- Ausstehende Anmerkungen dieser Seite -->
        <svg class="absolute inset-0 w-full h-full pointer-events-none">
          <template v-for="(a, i) in pagePending" :key="i">
            <rect v-if="a.type === 'highlight'" :x="pct(a.quads[0].x0)" :y="pcty(a.quads[0].y0)" :width="pctw(a.quads[0].x1 - a.quads[0].x0)" :height="pcth(a.quads[0].y1 - a.quads[0].y0)" :fill="a.color" opacity="0.35" />
            <rect v-else-if="a.type === 'rect'" :x="pct(a.x0)" :y="pcty(a.y0)" :width="pctw(a.x1 - a.x0)" :height="pcth(a.y1 - a.y0)" fill="none" :stroke="a.color" stroke-width="2" />
            <rect v-else-if="a.type === 'redact'" :x="pct(a.x0)" :y="pcty(a.y0)" :width="pctw(a.x1 - a.x0)" :height="pcth(a.y1 - a.y0)" fill="black" opacity="0.85" />
            <line v-else-if="a.type === 'line'" :x1="pct(a.x0)" :y1="pcty(a.y0)" :x2="pct(a.x1)" :y2="pcty(a.y1)" :stroke="a.color" stroke-width="2" />
            <g v-else-if="a.type === 'freetext'">
              <rect :x="pct(a.x)" :y="pcty(a.y)" :width="pctw(a.width)" :height="pcth(a.height)" fill="white" opacity="0.7" :stroke="a.color" stroke-dasharray="4" />
              <text :x="pct(a.x) + 3" :y="pcty(a.y) + 14" :fill="a.color" font-size="12">{{ a.text.slice(0, 40) }}</text>
            </g>
            <g v-else-if="a.type === 'text_comment'">
              <circle :cx="pct(a.x)" :cy="pcty(a.y)" r="9" :fill="a.color" opacity="0.9" />
              <text :x="pct(a.x) - 4" :y="pcty(a.y) + 4" fill="white" font-size="11">💬</text>
            </g>
            <g v-else-if="a.type === 'stamp'">
              <rect :x="pct(a.x0)" :y="pcty(a.y0)" :width="pctw(a.x1 - a.x0)" :height="pcth(a.y1 - a.y0)" fill="none" :stroke="a.color" stroke-width="2" />
              <text :x="pct(a.x0) + 4" :y="pcty(a.y0) + 16" :fill="a.color" font-size="13" font-weight="bold">{{ a.text }}</text>
            </g>
            <polyline v-else-if="a.type === 'ink'" :points="inkPoints(a)" fill="none" :stroke="a.color" stroke-width="2" />
          </template>
          <!-- Aktive Zeichnung -->
          <rect v-if="draft && ['highlight','rect','redact','stamp','freetext'].includes(tool)" :x="pct(Math.min(draft.x0, draft.x1))" :y="pcty(Math.min(draft.y0, draft.y1))" :width="pctw(Math.abs(draft.x1 - draft.x0))" :height="pcth(Math.abs(draft.y1 - draft.y0))" fill="none" stroke="#7c3aed" stroke-dasharray="4" stroke-width="1.5" />
          <line v-if="draft && tool === 'line'" :x1="pct(draft.x0)" :y1="pcty(draft.y0)" :x2="pct(draft.x1)" :y2="pcty(draft.y1)" stroke="#7c3aed" stroke-dasharray="4" stroke-width="1.5" />
          <polyline v-if="inkPath.length > 1 && tool === 'ink'" :points="inkPoints({ paths: [inkPath] })" fill="none" stroke="#7c3aed" stroke-width="2" />
        </svg>
      </div>

      <!-- Texteingabe-Dialog für Freitext/Kommentar -->
      <div v-if="textPrompt" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <div class="w-full max-w-sm bg-white dark:bg-gray-800 rounded-xl shadow-xl p-5 space-y-3">
          <h3 class="text-sm font-semibold text-gray-900 dark:text-white">
            {{ textPrompt.kind === 'freetext' ? 'Freitext' : 'Kommentar' }}
          </h3>
          <textarea v-model="textPrompt.text" rows="3" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white" autofocus></textarea>
          <div class="flex justify-end gap-2">
            <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="textPrompt = null">Abbrechen</button>
            <button class="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700" :disabled="!textPrompt.text.trim()" @click="confirmText">Übernehmen</button>
          </div>
        </div>
      </div>
    </template>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

type Annotation = Record<string, any> & { type: string; page: number }

const tools = [
  { id: 'highlight', label: 'Markieren', icon: '🖍️' },
  { id: 'rect', label: 'Rechteck', icon: '▭' },
  { id: 'line', label: 'Linie', icon: '╱' },
  { id: 'freetext', label: 'Freitext', icon: '🔤' },
  { id: 'text_comment', label: 'Kommentar', icon: '💬' },
  { id: 'stamp', label: 'Stempel', icon: '🔖' },
  { id: 'ink', label: 'Zeichnen', icon: '✏️' },
  { id: 'redact', label: 'Schwärzen', icon: '⬛' },
]

const file = ref<File | null>(null)
const workingBlob = ref<Blob | null>(null)
const workingName = ref('dokument.pdf')
const page = ref(1)
const pageCount = ref(1)
const pageImage = ref('')
const loadingPage = ref(false)
const applying = ref(false)
const error = ref<string | null>(null)
const tool = ref('highlight')
const color = ref('#ffde21')
const stampText = ref('ENTWURF')
const pending = ref<Annotation[]>([])
const canvasBox = ref<HTMLElement | null>(null)
const draft = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null)
const inkPath = ref<{ x: number; y: number }[]>([])
const textPrompt = ref<{ kind: 'freetext' | 'text_comment'; text: string; box: { x0: number; y0: number; x1: number; y1: number } } | null>(null)
const boxSize = ref({ w: 1, h: 1 })

const pagePending = computed(() => pending.value.filter((a) => a.page === page.value))

watch(file, async (f) => {
  if (!f) return
  workingBlob.value = f
  workingName.value = f.name
  pending.value = []
  page.value = 1
  error.value = null
  await loadMeta()
  await loadPage()
})

async function loadMeta() {
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value!, workingName.value)
    const resp = await apiPost('/api/pdf-tools/metadata/read', fd)
    pageCount.value = (await resp.json()).page_count || 1
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Metadaten lesen fehlgeschlagen'
  }
}

async function loadPage() {
  if (!workingBlob.value) return
  loadingPage.value = true
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    const resp = await apiPost(`/api/pdf-tools/thumbnails?pages=${page.value}&max_width=1100`, fd)
    pageImage.value = (await resp.json()).thumbnails[String(page.value)] || ''
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Seite laden fehlgeschlagen'
  } finally {
    loadingPage.value = false
  }
}

async function goToPage(p: number) {
  page.value = Math.min(Math.max(1, p), pageCount.value)
  await loadPage()
}

// ── Koordinaten-Helfer (SVG rendert in Pixeln, Modell ist 0-1-normiert) ──
function measure() {
  if (canvasBox.value) {
    boxSize.value = { w: canvasBox.value.clientWidth, h: canvasBox.value.clientHeight }
  }
}
function pct(x: number) { return x * boxSize.value.w }
function pcty(y: number) { return y * boxSize.value.h }
function pctw(w: number) { return Math.max(1, w * boxSize.value.w) }
function pcth(h: number) { return Math.max(1, h * boxSize.value.h) }
function inkPoints(a: Record<string, unknown>) {
  const paths = (a.paths as { x: number; y: number }[][] | undefined) ?? []
  return (paths[0] ?? []).map((p) => `${pct(p.x)},${pcty(p.y)}`).join(' ')
}

function norm(e: MouseEvent) {
  const r = canvasBox.value!.getBoundingClientRect()
  return {
    x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
    y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
  }
}

let drawing = false

function onDown(e: MouseEvent) {
  if (tool.value === 'select' || !canvasBox.value) return
  measure()
  const p = norm(e)
  drawing = true
  if (tool.value === 'ink') {
    inkPath.value = [p]
  } else if (tool.value === 'text_comment') {
    textPrompt.value = { kind: 'text_comment', text: '', box: { x0: p.x, y0: p.y, x1: p.x, y1: p.y } }
    drawing = false
  } else {
    draft.value = { x0: p.x, y0: p.y, x1: p.x, y1: p.y }
  }
}

function onMove(e: MouseEvent) {
  if (!drawing) return
  const p = norm(e)
  if (tool.value === 'ink') inkPath.value = [...inkPath.value, p]
  else if (draft.value) draft.value = { ...draft.value, x1: p.x, y1: p.y }
}

function onUp() {
  if (!drawing) return
  drawing = false
  if (tool.value === 'ink') {
    if (inkPath.value.length > 2) {
      pending.value.push({ type: 'ink', page: page.value, paths: [inkPath.value], color: color.value, width: 2 })
    }
    inkPath.value = []
    return
  }
  if (!draft.value) return
  const d = draft.value
  draft.value = null
  const x0 = Math.min(d.x0, d.x1), x1 = Math.max(d.x0, d.x1)
  const y0 = Math.min(d.y0, d.y1), y1 = Math.max(d.y0, d.y1)
  if (tool.value !== 'line' && (x1 - x0 < 0.005 || y1 - y0 < 0.005)) return

  if (tool.value === 'highlight') {
    pending.value.push({ type: 'highlight', page: page.value, quads: [{ x0, y0, x1, y1 }], color: color.value, opacity: 0.4 })
  } else if (tool.value === 'rect') {
    pending.value.push({ type: 'rect', page: page.value, x0, y0, x1, y1, color: color.value, width: 2 })
  } else if (tool.value === 'redact') {
    pending.value.push({ type: 'redact', page: page.value, x0, y0, x1, y1, fill_color: '#000000' })
  } else if (tool.value === 'line') {
    pending.value.push({ type: 'line', page: page.value, x0: d.x0, y0: d.y0, x1: d.x1, y1: d.y1, color: color.value, width: 2 })
  } else if (tool.value === 'stamp') {
    pending.value.push({ type: 'stamp', page: page.value, x0, y0, x1, y1, text: stampText.value, color: color.value })
  } else if (tool.value === 'freetext') {
    textPrompt.value = { kind: 'freetext', text: '', box: { x0, y0, x1, y1 } }
  }
}

function confirmText() {
  if (!textPrompt.value) return
  const t = textPrompt.value
  if (t.kind === 'freetext') {
    pending.value.push({
      type: 'freetext', page: page.value,
      x: t.box.x0, y: t.box.y0,
      width: Math.max(0.08, t.box.x1 - t.box.x0), height: Math.max(0.03, t.box.y1 - t.box.y0),
      text: t.text, font_size: 11, color: color.value,
    })
  } else {
    pending.value.push({ type: 'text_comment', page: page.value, x: t.box.x0, y: t.box.y0, content: t.text, color: color.value })
  }
  textPrompt.value = null
}

function undoLast() {
  pending.value = pending.value.slice(0, -1)
}

async function applyAnnotations() {
  if (!workingBlob.value || pending.value.length === 0) return
  applying.value = true
  error.value = null
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    fd.append('annotations', JSON.stringify(pending.value))
    const resp = await apiPost('/api/pdf-editor/annotations', fd)
    workingBlob.value = await resp.blob()
    pending.value = []
    await loadPage()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Anwenden fehlgeschlagen'
  } finally {
    applying.value = false
  }
}

async function download() {
  if (!workingBlob.value) return
  const name = workingName.value.replace(/\.pdf$/i, '_annotiert.pdf')
  const resp = new Response(workingBlob.value)
  await downloadBlob(resp, name)
}

function reset() {
  file.value = null
  workingBlob.value = null
  pageImage.value = ''
  pending.value = []
  inkPath.value = []
  draft.value = null
}
</script>
