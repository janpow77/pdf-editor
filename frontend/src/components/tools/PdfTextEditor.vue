<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3 flex-wrap">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Text bearbeiten (WYSIWYG)</h2>
    </div>

    <div v-if="!workingBlob" class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Textblock in der Seitenansicht anklicken, Text ändern, anwenden — direkt im Dokument.
      Der Text bleibt in seiner Box (kein seitenübergreifender Umbruch wie in Adobe Acrobat);
      bei längerem Text wird die Schrift automatisch verkleinert.
    </div>

    <FileDrop v-if="!workingBlob" v-model="file" />

    <template v-if="workingBlob">
      <!-- Werkzeugleiste -->
      <div class="flex items-center gap-2 flex-wrap bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <button class="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-40" :disabled="page <= 1" @click="goToPage(page - 1)">←</button>
        <span class="text-sm text-gray-700 dark:text-gray-300">Seite {{ page }} / {{ pageCount }}</span>
        <button class="px-2 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 disabled:opacity-40" :disabled="page >= pageCount" @click="goToPage(page + 1)">→</button>

        <span class="mx-2 text-gray-300 dark:text-gray-600">|</span>
        <span class="text-sm text-gray-500 dark:text-gray-400">{{ editCount }} Änderung(en) ausstehend</span>

        <span class="flex-1"></span>
        <button
          class="px-3 py-1.5 text-sm rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50"
          :disabled="applying || editCount === 0"
          @click="applyEdits"
        >
          {{ applying ? 'Wende an…' : 'Änderungen anwenden' }}
        </button>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-purple-600 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 disabled:opacity-50"
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
          <div v-if="loadingPage" class="text-sm text-gray-500 py-8 text-center">Lade Seite…</div>
          <div v-else-if="pageImage" class="relative inline-block w-full border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden bg-white">
            <img :src="`data:image/png;base64,${pageImage}`" class="w-full select-none" alt="PDF-Seite" draggable="false" />
            <button
              v-for="(b, i) in blocks"
              :key="i"
              class="absolute border transition-colors"
              :class="blockClass(i)"
              :style="blockStyle(b)"
              :title="b.text.slice(0, 120)"
              @click="selectBlock(i)"
            ></button>
          </div>
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
              <button class="px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700" @click="saveDraft">
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
}

const file = ref<File | null>(null)
const workingBlob = ref<Blob | null>(null)
const workingName = ref('dokument.pdf')
const page = ref(1)
const pageCount = ref(1)
const pageImage = ref('')
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

watch(file, async (f) => {
  if (!f) return
  workingBlob.value = f
  workingName.value = f.name
  edits.value = new Map()
  page.value = 1
  error.value = null
  await loadMeta()
  await loadPage()
})

function editKey(blockIdx: number): string {
  return `${page.value}:${blockIdx}`
}

async function loadMeta() {
  const fd = new FormData()
  fd.append('file', workingBlob.value!, workingName.value)
  try {
    const resp = await apiPost('/api/pdf-tools/metadata/read', fd)
    const meta = await resp.json()
    pageCount.value = meta.page_count || 1
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Metadaten lesen fehlgeschlagen'
  }
}

async function loadPage() {
  if (!workingBlob.value) return
  loadingPage.value = true
  selected.value = null
  error.value = null
  try {
    const fdImg = new FormData()
    fdImg.append('file', workingBlob.value, workingName.value)
    const imgResp = await apiPost(`/api/pdf-tools/thumbnails?pages=${page.value}&max_width=1100`, fdImg)
    const imgData = await imgResp.json()
    pageImage.value = imgData.thumbnails[String(page.value)] || ''

    const fdBlocks = new FormData()
    fdBlocks.append('file', workingBlob.value, workingName.value)
    fdBlocks.append('page', String(page.value))
    const blockResp = await apiPost('/api/pdf-editor/text-blocks', fdBlocks)
    const blockData = await blockResp.json()
    blocks.value = blockData.blocks
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
  if (selected.value === i) return 'border-purple-600 bg-purple-400/25'
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
    await loadPage()
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
  pageImage.value = ''
  blocks.value = []
  edits.value = new Map()
  selected.value = null
  warnings.value = 0
}
</script>
