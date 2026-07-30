<template>
  <div>
    <!-- Aktives Werkzeug -->
    <div v-if="activeTool">
      <component :is="toolComponents[activeTool]" @back="activeTool = null" />
    </div>

    <!-- Werkzeug-Auswahl -->
    <div v-else class="space-y-6">
      <!-- Ansicht-Umschalter -->
      <div class="flex justify-end">
        <div class="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-0.5" role="group" aria-label="Ansicht wählen">
          <button
            class="px-3 py-1.5 rounded-md text-sm transition-colors"
            :class="viewMode === 'grid' ? 'bg-primary-600 text-white' : 'text-gray-600 dark:text-gray-300 hover:text-primary-600'"
            @click="setViewMode('grid')"
          >
            ▦ Raster
          </button>
          <button
            class="px-3 py-1.5 rounded-md text-sm transition-colors"
            :class="viewMode === 'rolodex' ? 'bg-primary-600 text-white' : 'text-gray-600 dark:text-gray-300 hover:text-primary-600'"
            @click="setViewMode('rolodex')"
          >
            ▤ Rolodex
          </button>
        </div>
      </div>

      <!-- Raster-Ansicht -->
      <template v-if="viewMode === 'grid'">
        <div v-for="section in sections" :key="section.title">
          <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">{{ section.title }}</h3>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            <button
              v-for="tool in section.tools"
              :key="tool.id"
              class="relative flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                     rounded-xl shadow-sm transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 group"
              :class="isLocked(tool.id)
                ? 'opacity-60 hover:border-primary-300'
                : 'hover:shadow-md hover:-translate-y-0.5 hover:border-gray-300 dark:hover:border-gray-500'"
              :title="isLocked(tool.id) ? LOCK_HINT : tool.desc"
              @click="openTool(tool.id)"
            >
              <span
                v-if="isLocked(tool.id)"
                class="absolute top-1.5 right-2 text-xs text-gray-400 dark:text-gray-500"
                aria-hidden="true"
              >🔒</span>
              <div
                class="w-10 h-10 rounded-lg flex items-center justify-center text-xl"
                :class="[tool.color, isLocked(tool.id) ? 'grayscale' : '']"
              >
                {{ tool.icon }}
              </div>
              <span
                class="text-sm font-medium text-center"
                :class="isLocked(tool.id) ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'"
              >{{ tool.label }}</span>
              <span v-if="isLocked(tool.id)" class="text-xs text-primary-600 dark:text-primary-400 text-center">
                Nur mit Anmeldung
              </span>
              <span v-else class="text-xs text-gray-500 dark:text-gray-400 text-center">{{ tool.desc }}</span>
            </button>
          </div>
        </div>
      </template>

      <!-- Rolodex-Ansicht (3D-Kartenkarussell) -->
      <div v-else class="select-none">
        <div
          ref="rolodexEl"
          class="relative h-72 overflow-hidden outline-none"
          style="perspective: 1200px"
          tabindex="0"
          role="listbox"
          :aria-activedescendant="`rolodex-card-${rolodexIndex}`"
          aria-label="Werkzeug-Karussell — Pfeiltasten zum Blättern, Enter zum Öffnen"
          @keydown.left.prevent="step(-1)"
          @keydown.right.prevent="step(1)"
          @keydown.enter.prevent="openTool(allTools[rolodexIndex].id)"
          @wheel.prevent="onWheel"
        >
          <button
            v-for="(tool, i) in allTools"
            v-show="Math.abs(i - rolodexIndex) <= 4"
            :id="`rolodex-card-${i}`"
            :key="tool.id"
            role="option"
            :aria-selected="i === rolodexIndex"
            class="absolute left-1/2 top-1/2 w-52 h-56 flex flex-col items-center justify-center gap-3 p-5
                   bg-white dark:bg-gray-800 border rounded-2xl shadow-lg
                   transition-all duration-300 ease-out will-change-transform
                   focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            :class="[
              i === rolodexIndex ? 'border-primary-400 dark:border-primary-500' : 'border-gray-200 dark:border-gray-700',
              isLocked(tool.id) ? 'opacity-70' : '',
            ]"
            :style="cardStyle(i)"
            :title="isLocked(tool.id) ? LOCK_HINT : tool.desc"
            @click="i === rolodexIndex ? openTool(tool.id) : (rolodexIndex = i)"
          >
            <div
              class="w-14 h-14 rounded-xl flex items-center justify-center text-3xl"
              :class="[tool.color, isLocked(tool.id) ? 'grayscale' : '']"
            >
              {{ tool.icon }}
            </div>
            <span
              class="text-base font-semibold text-center"
              :class="isLocked(tool.id) ? 'text-gray-500 dark:text-gray-400' : 'text-gray-900 dark:text-white'"
            >{{ tool.label }}</span>
            <span v-if="isLocked(tool.id)" class="text-xs text-primary-600 dark:text-primary-400 text-center">
              🔒 Nur mit Anmeldung
            </span>
            <span v-else class="text-xs text-gray-500 dark:text-gray-400 text-center">{{ tool.desc }}</span>
            <span class="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500">{{ tool.section }}</span>
          </button>
        </div>

        <!-- Steuerung -->
        <div class="flex items-center justify-center gap-4 mt-4">
          <button
            class="w-10 h-10 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300
                   hover:border-primary-400 hover:text-primary-600 transition-colors disabled:opacity-30"
            :disabled="rolodexIndex === 0"
            aria-label="Vorheriges Werkzeug"
            @click="step(-1)"
          >
            ←
          </button>
          <span class="text-sm text-gray-500 dark:text-gray-400 tabular-nums min-w-[6rem] text-center">
            {{ rolodexIndex + 1 }} / {{ allTools.length }}
          </span>
          <button
            class="w-10 h-10 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300
                   hover:border-primary-400 hover:text-primary-600 transition-colors disabled:opacity-30"
            :disabled="rolodexIndex === allTools.length - 1"
            aria-label="Nächstes Werkzeug"
            @click="step(1)"
          >
            →
          </button>
        </div>
        <p class="text-center text-xs text-gray-400 dark:text-gray-500 mt-2">
          Pfeiltasten oder Mausrad zum Blättern · Klick auf die mittlere Karte öffnet das Werkzeug
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { apiGetJson } from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'

interface Tool {
  id: string
  label: string
  desc: string
  icon: string
  color: string
}

const activeTool = ref<string | null>(null)
const aiAvailable = ref(false)
// Werkzeuge, die der Betreiber auf angemeldete Nutzer beschränkt hat
const lockedTools = ref<Set<string>>(new Set())
const router = useRouter()

const LOCK_HINT = 'Dieses Werkzeug steht nur angemeldeten Nutzern zur Verfügung — Konto ist kostenlos.'

function isLocked(id: string): boolean {
  return lockedTools.value.has(id) && !isAuthenticated.value
}

function openTool(id: string) {
  if (isLocked(id)) {
    router.push({ path: '/login', query: { werkzeug: id } })
    return
  }
  activeTool.value = id
}

// Werkzeuge werden erst beim Öffnen geladen — die Startseite bleibt leicht,
// obwohl der Editor-Teil pdf.js mitbringt.
const toolComponents: Record<string, Component> = {
  merge: defineAsyncComponent(() => import('@/components/tools/PdfMerge.vue')),
  split: defineAsyncComponent(() => import('@/components/tools/PdfSplit.vue')),
  rotate: defineAsyncComponent(() => import('@/components/tools/PdfRotate.vue')),
  toImages: defineAsyncComponent(() => import('@/components/tools/PdfToImages.vue')),
  compress: defineAsyncComponent(() => import('@/components/tools/PdfCompress.vue')),
  watermark: defineAsyncComponent(() => import('@/components/tools/PdfWatermark.vue')),
  imagesToPdf: defineAsyncComponent(() => import('@/components/tools/ImagesToPdf.vue')),
  pageEditor: defineAsyncComponent(() => import('@/components/tools/PdfPageEditor.vue')),
  metadata: defineAsyncComponent(() => import('@/components/tools/PdfMetadata.vue')),
  pdfCompare: defineAsyncComponent(() => import('@/components/tools/PdfCompare.vue')),
  protect: defineAsyncComponent(() => import('@/components/tools/PdfProtect.vue')),
  pdfToWord: defineAsyncComponent(() => import('@/components/tools/PdfToWord.vue')),
  pdfToExcel: defineAsyncComponent(() => import('@/components/tools/PdfToExcel.vue')),
  textEditor: defineAsyncComponent(() => import('@/components/tools/PdfTextEditor.vue')),
  pageNumbers: defineAsyncComponent(() => import('@/components/tools/PdfPageNumbers.vue')),
  headerFooter: defineAsyncComponent(() => import('@/components/tools/PdfHeaderFooter.vue')),
  searchReplace: defineAsyncComponent(() => import('@/components/tools/PdfSearchReplace.vue')),
  redact: defineAsyncComponent(() => import('@/components/tools/PdfRedact.vue')),
  flatten: defineAsyncComponent(() => import('@/components/tools/PdfFlatten.vue')),
  toText: defineAsyncComponent(() => import('@/components/tools/PdfToText.vue')),
  bates: defineAsyncComponent(() => import('@/components/tools/PdfBates.vue')),
  formFill: defineAsyncComponent(() => import('@/components/tools/PdfFormFill.vue')),
  formDesigner: defineAsyncComponent(() => import('@/components/tools/PdfFormDesigner.vue')),
  pdfa: defineAsyncComponent(() => import('@/components/tools/PdfPdfa.vue')),
  signImage: defineAsyncComponent(() => import('@/components/tools/PdfSignImage.vue')),
  imageReplace: defineAsyncComponent(() => import('@/components/tools/PdfImageReplace.vue')),
  annotate: defineAsyncComponent(() => import('@/components/tools/PdfAnnotate.vue')),
  signDigital: defineAsyncComponent(() => import('@/components/tools/PdfSignDigital.vue')),
  scanOptimize: defineAsyncComponent(() => import('@/components/tools/PdfScanOptimize.vue')),
  batch: defineAsyncComponent(() => import('@/components/tools/PdfBatch.vue')),
  tocEditor: defineAsyncComponent(() => import('@/components/tools/PdfTocEditor.vue')),
  ocr: defineAsyncComponent(() => import('@/components/tools/PdfOcr.vue')),
  pdfExport: defineAsyncComponent(() => import('@/components/tools/PdfExport.vue')),
  clean: defineAsyncComponent(() => import('@/components/tools/PdfClean.vue')),
  permissions: defineAsyncComponent(() => import('@/components/tools/PdfPermissions.vue')),
  verifySignatures: defineAsyncComponent(() => import('@/components/tools/PdfVerifySignatures.vue')),
  insertBlank: defineAsyncComponent(() => import('@/components/tools/PdfInsertBlank.vue')),
  pruefakte: defineAsyncComponent(() => import('@/components/tools/PdfPruefakte.vue')),
  qualityCheck: defineAsyncComponent(() => import('@/components/tools/PdfQualityCheck.vue')),
  aiAssistant: defineAsyncComponent(() => import('@/components/tools/PdfAiAssistant.vue')),
  officeToPdf: defineAsyncComponent(() => import('@/components/tools/OfficeToPdf.vue')),
  wordToPdf: defineAsyncComponent(() => import('@/components/tools/WordToPdf.vue')),
  wordMerge: defineAsyncComponent(() => import('@/components/tools/WordMerge.vue')),
  wordDiff: defineAsyncComponent(() => import('@/components/tools/WordDiff.vue')),
  wordMeta: defineAsyncComponent(() => import('@/components/tools/WordMetadata.vue')),
  excelMeta: defineAsyncComponent(() => import('@/components/tools/ExcelMetadata.vue')),
}

const TILE = 'bg-gray-100 dark:bg-gray-700/60'

const pdfTools = computed<Tool[]>(() => [
  { id: 'textEditor', label: 'Text bearbeiten', desc: 'WYSIWYG im Dokument', icon: '✏️', color: TILE },
  { id: 'annotate', label: 'Anmerkungen', desc: 'Markieren, Stempel, Zeichnen', icon: '🖍️', color: TILE },
  { id: 'merge', label: 'Zusammenführen', desc: 'Mehrere PDFs verbinden', icon: '📎', color: TILE },
  { id: 'split', label: 'Teilen', desc: 'PDF aufteilen', icon: '✂️', color: TILE },
  { id: 'rotate', label: 'Rotieren', desc: 'Seiten drehen', icon: '🔄', color: TILE },
  { id: 'toImages', label: 'PDF → Bilder', desc: 'Als PNG/JPG exportieren', icon: '🖼️', color: TILE },
  { id: 'compress', label: 'Komprimieren', desc: 'Dateigröße reduzieren', icon: '🗜️', color: TILE },
  { id: 'watermark', label: 'Wasserzeichen', desc: 'Text oder Bild', icon: '💧', color: TILE },
  { id: 'imagesToPdf', label: 'Bilder → PDF', desc: 'Bilder zu PDF', icon: '📄', color: TILE },
  { id: 'pageEditor', label: 'Seiten ordnen', desc: 'Umsortieren & löschen', icon: '📑', color: TILE },
  { id: 'insertBlank', label: 'Leere Seiten', desc: 'Seiten einfügen', icon: '➕', color: TILE },
  { id: 'pdfCompare', label: 'PDF Vergleich', desc: 'Zwei PDFs vergleichen', icon: '⚖️', color: TILE },
  { id: 'ocr', label: 'OCR', desc: 'Texterkennung', icon: '🔍', color: TILE },
  { id: 'protect', label: 'Schützen / Entsperren', desc: 'Passwortschutz', icon: '🔒', color: TILE },
  { id: 'permissions', label: 'Rechteverwaltung', desc: 'Drucken/Kopieren einschränken', icon: '🛡️', color: TILE },
  { id: 'clean', label: 'Bereinigen', desc: 'Metadaten & Verstecktes entfernen', icon: '🧽', color: TILE },
  { id: 'pdfToWord', label: 'PDF → Word', desc: 'Als DOCX exportieren', icon: '📝', color: TILE },
  { id: 'pdfToExcel', label: 'PDF → Excel', desc: 'Tabellen extrahieren', icon: '📊', color: TILE },
  { id: 'pdfExport', label: 'PDF exportieren', desc: 'Markdown, HTML, JSON, CSV', icon: '📤', color: TILE },
  { id: 'metadata', label: 'Metadaten', desc: 'Titel, Autor, Datum etc.', icon: 'ℹ️', color: TILE },
  { id: 'toText', label: 'PDF → Text', desc: 'Reinen Text extrahieren', icon: '📃', color: TILE },
  { id: 'searchReplace', label: 'Suchen & Ersetzen', desc: 'Text austauschen', icon: '🔁', color: TILE },
  { id: 'redact', label: 'Schwärzen', desc: 'Text unwiderruflich entfernen', icon: '⬛', color: TILE },
  { id: 'pageNumbers', label: 'Seitenzahlen', desc: 'Nummerierung einfügen', icon: '🔢', color: TILE },
  { id: 'headerFooter', label: 'Kopf-/Fußzeile', desc: 'Text oben/unten', icon: '📰', color: TILE },
  { id: 'bates', label: 'Bates-Nummern', desc: 'Akten-Kennzeichnung', icon: '🏷️', color: TILE },
  { id: 'pruefakte', label: 'Prüfakte', desc: 'Akte mit Lesezeichen + Bates', icon: '🗂️', color: TILE },
  { id: 'formDesigner', label: 'Formular-Designer', desc: 'Felder anlegen, Layout lokal speichern', icon: '🧩', color: TILE },
  { id: 'formFill', label: 'Formular ausfüllen', desc: 'AcroForm-Felder', icon: '📋', color: TILE },
  { id: 'signImage', label: 'Unterschrift', desc: 'Bild-Signatur einfügen', icon: '✍️', color: TILE },
  { id: 'imageReplace', label: 'Bild ersetzen', desc: 'Logo/Grafik austauschen', icon: '🖌️', color: TILE },
  { id: 'pdfa', label: 'PDF/A', desc: 'Archivformat', icon: '🗄️', color: TILE },
  { id: 'flatten', label: 'Einbrennen', desc: 'Anmerkungen fixieren', icon: '🔥', color: TILE },
  { id: 'signDigital', label: 'Digital signieren', desc: 'Mit Zertifikat (PAdES)', icon: '🔏', color: TILE },
  { id: 'verifySignatures', label: 'Signatur prüfen', desc: 'Integrität & Unterzeichner', icon: '✅', color: TILE },
  { id: 'scanOptimize', label: 'Scan optimieren', desc: 'Geraderücken + OCR', icon: '🧹', color: TILE },
  { id: 'qualityCheck', label: 'Qualitätsprüfung', desc: 'Leere/doppelte Seiten finden', icon: '🩺', color: TILE },
  { id: 'batch', label: 'Batch', desc: 'Viele Dateien auf einmal', icon: '📦', color: TILE },
  { id: 'tocEditor', label: 'Lesezeichen', desc: 'Inhaltsverzeichnis bearbeiten', icon: '🔖', color: TILE },
  ...(aiAvailable.value
    ? [{ id: 'aiAssistant', label: 'KI-Assistent', desc: 'Zusammenfassen & Fragen (lokal)', icon: '🤖', color: TILE }]
    : []),
])

const wordTools: Tool[] = [
  { id: 'wordToPdf', label: 'Word → PDF', desc: 'DOCX konvertieren', icon: '📝', color: TILE },
  { id: 'wordMerge', label: 'Word verbinden', desc: 'DOCX zusammenführen', icon: '📋', color: TILE },
  { id: 'wordDiff', label: 'Word Vergleich', desc: 'Unterschiede finden', icon: '🔍', color: TILE },
  { id: 'wordMeta', label: 'Word Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: TILE },
]

const excelTools: Tool[] = [
  { id: 'excelMeta', label: 'Excel Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: TILE },
  { id: 'officeToPdf', label: 'Office → PDF', desc: 'Excel, PowerPoint, ODF, RTF', icon: '🗃️', color: TILE },
]

const sections = computed(() => [
  { title: 'PDF Werkzeuge', tools: pdfTools.value },
  { title: 'Word Werkzeuge', tools: wordTools },
  { title: 'Excel & Office Werkzeuge', tools: excelTools },
])

// ── Rolodex-Ansicht ───────────────────────────────────────────

type ViewMode = 'grid' | 'rolodex'
const VIEW_KEY = 'pdfapp_view_mode'
const viewMode = ref<ViewMode>(
  localStorage.getItem(VIEW_KEY) === 'rolodex' ? 'rolodex' : 'grid',
)
const rolodexIndex = ref(0)
const rolodexEl = ref<HTMLElement | null>(null)

const allTools = computed(() =>
  sections.value.flatMap((s) => s.tools.map((t) => ({ ...t, section: s.title }))),
)

function setViewMode(mode: ViewMode) {
  viewMode.value = mode
  localStorage.setItem(VIEW_KEY, mode)
  if (mode === 'rolodex') {
    rolodexIndex.value = Math.min(rolodexIndex.value, allTools.value.length - 1)
  }
}

function step(dir: number) {
  const next = rolodexIndex.value + dir
  if (next >= 0 && next < allTools.value.length) rolodexIndex.value = next
}

let wheelLock = 0
function onWheel(e: WheelEvent) {
  const now = Date.now()
  if (now - wheelLock < 150) return
  wheelLock = now
  const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY
  if (delta > 0) step(1)
  else if (delta < 0) step(-1)
}

function cardStyle(i: number): Record<string, string> {
  const offset = i - rolodexIndex.value
  const abs = Math.abs(offset)
  const translateX = offset * 150
  const rotateY = Math.max(-55, Math.min(55, offset * -35))
  const translateZ = -abs * 120
  const scale = offset === 0 ? 1 : Math.max(0.7, 1 - abs * 0.1)
  return {
    transform: `translate(-50%, -50%) translateX(${translateX}px) translateZ(${translateZ}px) rotateY(${rotateY}deg) scale(${scale})`,
    opacity: String(Math.max(0.25, 1 - abs * 0.22)),
    zIndex: String(100 - abs),
    cursor: offset === 0 ? 'pointer' : 'ew-resize',
  }
}

onMounted(async () => {
  try {
    const health = await apiGetJson<{
      features?: Record<string, boolean>
      login_required_tools?: string[]
    }>('/api/health')
    aiAvailable.value = Boolean(health.features?.ai)
    lockedTools.value = new Set(health.login_required_tools ?? [])
  } catch {
    aiAvailable.value = false
    lockedTools.value = new Set()
  }
})
</script>
