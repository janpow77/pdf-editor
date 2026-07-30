<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3 flex-wrap">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Text bearbeiten (WYSIWYG)</h2>
    </div>

    <div v-if="!workingBlob" class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Textblock in der Seitenansicht anklicken, Text ändern, anwenden — direkt im Dokument.
      Der Text bleibt in seiner Box (kein seitenübergreifender Umbruch wie in Adobe Acrobat);
      bei längerem Text wird die Schrift automatisch verkleinert.
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
        <!-- Seitenansicht mit Block-Overlay -->
        <div class="lg:col-span-2">
          <PdfViewer
            v-model="page"
            :source="workingBlob"
            @loaded="pageCount = $event"
            @rendered="loadBlocks"
          >
            <template #overlay>
              <button
                v-for="(b, i) in blocks"
                :key="i"
                class="absolute border transition-colors"
                :class="blockClass(i)"
                :style="blockStyle(b)"
                :title="b.text.slice(0, 120)"
                @click="selectBlock(i)"
              ></button>
            </template>
          </PdfViewer>
        </div>

        <!-- Bearbeitungs-Panel -->
        <div class="space-y-3">
          <div v-if="selected === null" class="p-4 bg-gray-50 dark:bg-gray-800 rounded-xl text-sm text-gray-500 dark:text-gray-400">
            Einen Textblock in der Seitenansicht anklicken, um ihn zu bearbeiten.
            Blaue Rahmen = Textblöcke, grüne = bereits geändert.
          </div>
          <div v-else class="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl space-y-3">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Textblock bearbeiten</h3>
            <textarea
              v-model="draftText"
              rows="6"
              class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-3 py-2 text-sm text-gray-900 dark:text-white font-mono"
            ></textarea>
            <div class="flex items-center gap-3">
              <label class="text-sm text-gray-700 dark:text-gray-300">Schriftgröße</label>
              <input v-model.number="draftSize" type="number" min="5" max="72" step="0.5" class="w-20 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 px-2 py-1 text-sm text-gray-900 dark:text-white" />
            </div>
            <p class="text-xs text-gray-400">Leerer Text entfernt den Block.</p>
            <div class="flex gap-2 flex-wrap">
              <button class="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700" @click="saveDraft">
                Änderung vormerken
              </button>
              <button
                v-if="edits.has(editKey(selected))"
                class="px-3 py-1.5 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
                @click="discardDraft"
              >
                Änderung verwerfen
              </button>
              <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="selected = null">
                Schließen
              </button>
            </div>
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
import PdfViewer from '@/components/PdfViewer.vue'
import WorkSessionBar from '@/components/WorkSessionBar.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface Block {
  text: string
  bbox: { x0: number; y0: number; x1: number; y1: number }
  font_size: number
  font_name: string
  color: string
}

interface Edit {
  page: number
  bbox: Block['bbox']
  text: string
  font_size: number
  color: string
  // Schriftname des Originalblocks — das Backend bettet eine dazu passende
  // Schrift ein, damit Umlaute und Sonderzeichen erhalten bleiben
  font: string
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
const selected = ref<number | null>(null)
const draftText = ref('')
const draftSize = ref(11)
// Vorgemerkte Änderungen über alle Seiten (Key: page:blockIndex)
const edits = ref(new Map<string, Edit>())

const editCount = computed(() => edits.value.size)

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
  selected.value = null
  error.value = null
}

watch(file, async (f) => {
  if (!f) return
  workingBlob.value = f
  workingName.value = f.name
  edits.value = new Map()
  page.value = 1
  error.value = null
  // Seitenzahl und Darstellung liefert der Viewer lokal — hier nur die Blöcke
})

function editKey(blockIdx: number): string {
  return `${page.value}:${blockIdx}`
}

async function loadBlocks() {
  if (!workingBlob.value) return
  loadingPage.value = true
  selected.value = null
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

function blockStyle(b: Block) {
  return {
    left: `${b.bbox.x0 * 100}%`,
    top: `${b.bbox.y0 * 100}%`,
    width: `${(b.bbox.x1 - b.bbox.x0) * 100}%`,
    height: `${(b.bbox.y1 - b.bbox.y0) * 100}%`,
  }
}

function blockClass(i: number) {
  if (edits.value.has(editKey(i)))
    return 'border-green-500 bg-green-400/20 hover:bg-green-400/30'
  if (selected.value === i) return 'border-primary-600 bg-primary-400/25'
  return 'border-blue-400/70 bg-transparent hover:bg-blue-300/20'
}

function selectBlock(i: number) {
  selected.value = i
  const pending = edits.value.get(editKey(i))
  draftText.value = pending ? pending.text : blocks.value[i].text
  draftSize.value = pending ? pending.font_size : blocks.value[i].font_size || 11
}

function saveDraft() {
  if (selected.value === null) return
  const b = blocks.value[selected.value]
  edits.value.set(editKey(selected.value), {
    page: page.value,
    bbox: b.bbox,
    text: draftText.value,
    font_size: draftSize.value,
    color: b.color || '#000000',
    font: b.font_name || '',
  })
  edits.value = new Map(edits.value)
  selected.value = null
}

function discardDraft() {
  if (selected.value === null) return
  edits.value.delete(editKey(selected.value))
  edits.value = new Map(edits.value)
  selected.value = null
}

async function applyEdits() {
  if (!workingBlob.value || edits.value.size === 0) return
  applying.value = true
  error.value = null
  warnings.value = 0
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
  const resp = new Response(workingBlob.value, {
    headers: { 'Content-Disposition': `attachment; filename="${workingName.value.replace(/\.pdf$/i, '_bearbeitet.pdf')}"` },
  })
  await downloadBlob(resp, workingName.value.replace(/\.pdf$/i, '_bearbeitet.pdf'))
}

function reset() {
  file.value = null
  workingBlob.value = null
  blocks.value = []
  edits.value = new Map()
  selected.value = null
  warnings.value = 0
}
</script>
