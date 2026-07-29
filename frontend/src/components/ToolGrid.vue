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
              class="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                     rounded-xl shadow-sm hover:shadow-md hover:-translate-y-0.5 hover:border-gray-300 dark:hover:border-gray-500
                     transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 group"
              @click="activeTool = tool.id"
            >
              <div class="w-10 h-10 rounded-lg flex items-center justify-center text-xl" :class="tool.color">
                {{ tool.icon }}
              </div>
              <span class="text-sm font-medium text-gray-900 dark:text-white text-center">{{ tool.label }}</span>
              <span class="text-xs text-gray-500 dark:text-gray-400 text-center">{{ tool.desc }}</span>
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
          @keydown.enter.prevent="activeTool = allTools[rolodexIndex].id"
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
            :class="i === rolodexIndex ? 'border-primary-400 dark:border-primary-500' : 'border-gray-200 dark:border-gray-700'"
            :style="cardStyle(i)"
            @click="i === rolodexIndex ? (activeTool = tool.id) : (rolodexIndex = i)"
          >
            <div class="w-14 h-14 rounded-xl flex items-center justify-center text-3xl" :class="tool.color">
              {{ tool.icon }}
            </div>
            <span class="text-base font-semibold text-gray-900 dark:text-white text-center">{{ tool.label }}</span>
            <span class="text-xs text-gray-500 dark:text-gray-400 text-center">{{ tool.desc }}</span>
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
import { computed, markRaw, onMounted, ref, type Component } from 'vue'
import { apiGetJson } from '@/lib/api'
import PdfMerge from '@/components/tools/PdfMerge.vue'
import PdfSplit from '@/components/tools/PdfSplit.vue'
import PdfRotate from '@/components/tools/PdfRotate.vue'
import PdfToImages from '@/components/tools/PdfToImages.vue'
import PdfCompress from '@/components/tools/PdfCompress.vue'
import PdfWatermark from '@/components/tools/PdfWatermark.vue'
import ImagesToPdf from '@/components/tools/ImagesToPdf.vue'
import PdfPageEditor from '@/components/tools/PdfPageEditor.vue'
import PdfMetadata from '@/components/tools/PdfMetadata.vue'
import PdfCompare from '@/components/tools/PdfCompare.vue'
import PdfProtect from '@/components/tools/PdfProtect.vue'
import PdfToWord from '@/components/tools/PdfToWord.vue'
import PdfToExcel from '@/components/tools/PdfToExcel.vue'
import PdfTextEditor from '@/components/tools/PdfTextEditor.vue'
import PdfPageNumbers from '@/components/tools/PdfPageNumbers.vue'
import PdfHeaderFooter from '@/components/tools/PdfHeaderFooter.vue'
import PdfSearchReplace from '@/components/tools/PdfSearchReplace.vue'
import PdfRedact from '@/components/tools/PdfRedact.vue'
import PdfFlatten from '@/components/tools/PdfFlatten.vue'
import PdfToText from '@/components/tools/PdfToText.vue'
import PdfBates from '@/components/tools/PdfBates.vue'
import PdfFormFill from '@/components/tools/PdfFormFill.vue'
import PdfFormDesigner from '@/components/tools/PdfFormDesigner.vue'
import PdfPdfa from '@/components/tools/PdfPdfa.vue'
import PdfSignImage from '@/components/tools/PdfSignImage.vue'
import PdfAnnotate from '@/components/tools/PdfAnnotate.vue'
import PdfSignDigital from '@/components/tools/PdfSignDigital.vue'
import PdfScanOptimize from '@/components/tools/PdfScanOptimize.vue'
import PdfBatch from '@/components/tools/PdfBatch.vue'
import PdfTocEditor from '@/components/tools/PdfTocEditor.vue'
import PdfOcr from '@/components/tools/PdfOcr.vue'
import PdfExport from '@/components/tools/PdfExport.vue'
import PdfClean from '@/components/tools/PdfClean.vue'
import PdfPermissions from '@/components/tools/PdfPermissions.vue'
import PdfVerifySignatures from '@/components/tools/PdfVerifySignatures.vue'
import PdfInsertBlank from '@/components/tools/PdfInsertBlank.vue'
import PdfPruefakte from '@/components/tools/PdfPruefakte.vue'
import PdfQualityCheck from '@/components/tools/PdfQualityCheck.vue'
import PdfAiAssistant from '@/components/tools/PdfAiAssistant.vue'
import OfficeToPdf from '@/components/tools/OfficeToPdf.vue'
import WordToPdf from '@/components/tools/WordToPdf.vue'
import WordMerge from '@/components/tools/WordMerge.vue'
import WordDiff from '@/components/tools/WordDiff.vue'
import WordMetadata from '@/components/tools/WordMetadata.vue'
import ExcelMetadata from '@/components/tools/ExcelMetadata.vue'

interface Tool {
  id: string
  label: string
  desc: string
  icon: string
  color: string
}

const activeTool = ref<string | null>(null)
const aiAvailable = ref(false)

const toolComponents: Record<string, Component> = {
  merge: markRaw(PdfMerge),
  split: markRaw(PdfSplit),
  rotate: markRaw(PdfRotate),
  toImages: markRaw(PdfToImages),
  compress: markRaw(PdfCompress),
  watermark: markRaw(PdfWatermark),
  imagesToPdf: markRaw(ImagesToPdf),
  pageEditor: markRaw(PdfPageEditor),
  metadata: markRaw(PdfMetadata),
  pdfCompare: markRaw(PdfCompare),
  protect: markRaw(PdfProtect),
  pdfToWord: markRaw(PdfToWord),
  pdfToExcel: markRaw(PdfToExcel),
  textEditor: markRaw(PdfTextEditor),
  pageNumbers: markRaw(PdfPageNumbers),
  headerFooter: markRaw(PdfHeaderFooter),
  searchReplace: markRaw(PdfSearchReplace),
  redact: markRaw(PdfRedact),
  flatten: markRaw(PdfFlatten),
  toText: markRaw(PdfToText),
  bates: markRaw(PdfBates),
  formFill: markRaw(PdfFormFill),
  formDesigner: markRaw(PdfFormDesigner),
  pdfa: markRaw(PdfPdfa),
  signImage: markRaw(PdfSignImage),
  annotate: markRaw(PdfAnnotate),
  signDigital: markRaw(PdfSignDigital),
  scanOptimize: markRaw(PdfScanOptimize),
  batch: markRaw(PdfBatch),
  tocEditor: markRaw(PdfTocEditor),
  ocr: markRaw(PdfOcr),
  pdfExport: markRaw(PdfExport),
  clean: markRaw(PdfClean),
  permissions: markRaw(PdfPermissions),
  verifySignatures: markRaw(PdfVerifySignatures),
  insertBlank: markRaw(PdfInsertBlank),
  pruefakte: markRaw(PdfPruefakte),
  qualityCheck: markRaw(PdfQualityCheck),
  aiAssistant: markRaw(PdfAiAssistant),
  officeToPdf: markRaw(OfficeToPdf),
  wordToPdf: markRaw(WordToPdf),
  wordMerge: markRaw(WordMerge),
  wordDiff: markRaw(WordDiff),
  wordMeta: markRaw(WordMetadata),
  excelMeta: markRaw(ExcelMetadata),
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
    const health = await apiGetJson<{ features?: Record<string, boolean> }>('/api/health')
    aiAvailable.value = Boolean(health.features?.ai)
  } catch {
    aiAvailable.value = false
  }
})
</script>
