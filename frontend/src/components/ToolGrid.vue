<template>
  <div>
    <!-- Aktives Werkzeug -->
    <div v-if="activeTool">
      <component :is="toolComponents[activeTool]" @back="activeTool = null" />
    </div>

    <!-- Werkzeug-Auswahl -->
    <div v-else class="space-y-8">
      <!-- Ansicht-Schalter: ein Schalter, zwei Zustände -->
      <div class="flex justify-end">
        <button
          type="button"
          role="switch"
          :aria-checked="viewMode === 'rolodex'"
          class="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-300 focus-visible:outline-none
                 focus-visible:ring-2 focus-visible:ring-primary-500 rounded-full px-1 py-0.5 group"
          @click="setViewMode(viewMode === 'grid' ? 'rolodex' : 'grid')"
        >
          <span :class="viewMode === 'grid' ? 'font-semibold text-gray-900 dark:text-white' : ''">▦ Raster</span>
          <span
            class="relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors duration-200"
            :class="viewMode === 'rolodex' ? 'bg-primary-600' : 'bg-gray-300 dark:bg-gray-600'"
            aria-hidden="true"
          >
            <span
              class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all duration-200"
              :class="viewMode === 'rolodex' ? 'left-[1.375rem]' : 'left-0.5'"
            />
          </span>
          <span :class="viewMode === 'rolodex' ? 'font-semibold text-gray-900 dark:text-white' : ''">▤ Rolodex</span>
        </button>
      </div>

      <!-- Raster-Ansicht: Werkzeuge in thematischen Gruppen -->
      <template v-if="viewMode === 'grid'">
        <section v-for="group in groups" :key="group.key" :aria-label="group.title">
          <div class="flex items-baseline gap-2 mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">
            <span aria-hidden="true" class="text-lg">{{ group.icon }}</span>
            <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wider">{{ group.title }}</h3>
            <span class="text-xs text-gray-400 dark:text-gray-500">{{ group.tools.length }} Werkzeuge</span>
          </div>
          <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            <button
              v-for="tool in group.tools"
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
                class="absolute top-1.5 right-2 text-xs text-gray-600 dark:text-gray-400"
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
        </section>
      </template>

      <!-- Rolodex-Ansicht: eine Gruppe wählen, durch ihre Karten blättern.
           Mehrere Karten bleiben nebeneinander sichtbar (Coverflow). -->
      <div v-else class="select-none space-y-4">
        <!-- Gruppen-Wahl -->
        <div class="flex flex-wrap justify-center gap-2" role="tablist" aria-label="Werkzeug-Gruppe wählen">
          <button
            v-for="group in groups"
            :key="group.key"
            role="tab"
            :aria-selected="group.key === activeGroupKey"
            class="px-3 py-1.5 rounded-full text-sm border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            :class="group.key === activeGroupKey
              ? 'bg-primary-600 border-primary-600 text-white'
              : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-600'"
            @click="setGroup(group.key)"
          >
            <span aria-hidden="true">{{ group.icon }}</span> {{ group.title }}
            <span class="opacity-70">({{ group.tools.length }})</span>
          </button>
        </div>

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
          @keydown.enter.prevent="openTool(groupTools[rolodexIndex].id)"
          @wheel.prevent="onWheel"
        >
          <button
            v-for="(tool, i) in groupTools"
            :id="`rolodex-card-${i}`"
            :key="tool.id"
            role="option"
            :aria-selected="i === rolodexIndex"
            class="absolute left-0 top-1/2 w-52 h-56 flex flex-col items-center justify-center gap-3 p-5
                   bg-white dark:bg-gray-800 border rounded-2xl shadow-lg
                   will-change-transform
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
          </button>
        </div>

        <!-- Steuerung -->
        <div class="flex items-center justify-center gap-4">
          <button
            class="w-10 h-10 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300
                   hover:border-primary-400 hover:text-primary-600 transition-colors disabled:opacity-30"
            :disabled="rolodexIndex === 0"
            aria-label="Vorheriges Werkzeug"
            @click="stepAndFocus(-1)"
          >
            ←
          </button>
          <span class="text-sm text-gray-500 dark:text-gray-400 tabular-nums min-w-[6rem] text-center">
            {{ rolodexIndex + 1 }} / {{ groupTools.length }}
          </span>
          <button
            class="w-10 h-10 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300
                   hover:border-primary-400 hover:text-primary-600 transition-colors disabled:opacity-30"
            :disabled="rolodexIndex === groupTools.length - 1"
            aria-label="Nächstes Werkzeug"
            @click="stepAndFocus(1)"
          >
            →
          </button>
        </div>
        <p class="text-center text-xs text-gray-600 dark:text-gray-400">
          Pfeiltasten oder Mausrad zum Blättern · Klick auf die vordere Karte öffnet das Werkzeug
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { isAuthenticated } from '@/lib/auth'
import { getHealth } from '@/lib/health'

interface Tool {
  id: string
  label: string
  desc: string
  icon: string
  color: string
}

interface ToolGroup {
  key: string
  title: string
  icon: string
  tools: Tool[]
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

// Thematische Gruppen statt einer langen Liste: Die Startseite gliedert die
// Werkzeuge nach Tätigkeit, und der Rolodex blättert je Gruppe — so bleiben
// im Karussell immer nur eine Handvoll Karten, nicht alle 45.
const groups = computed<ToolGroup[]>(() => [
  {
    key: 'bearbeiten',
    title: 'Bearbeiten & Anmerken',
    icon: '✏️',
    tools: [
      { id: 'textEditor', label: 'Text bearbeiten', desc: 'WYSIWYG im Dokument', icon: '✏️', color: TILE },
      { id: 'annotate', label: 'Anmerkungen', desc: 'Markieren, Stempel, Zeichnen', icon: '🖍️', color: TILE },
      { id: 'searchReplace', label: 'Suchen & Ersetzen', desc: 'Text austauschen', icon: '🔁', color: TILE },
      { id: 'signImage', label: 'Unterschrift', desc: 'Bild-Signatur einfügen', icon: '✍️', color: TILE },
      { id: 'imageReplace', label: 'Bild ersetzen', desc: 'Logo/Grafik austauschen', icon: '🖌️', color: TILE },
      { id: 'formDesigner', label: 'Formular-Designer', desc: 'Felder anlegen, Layout lokal speichern', icon: '🧩', color: TILE },
      { id: 'formFill', label: 'Formular ausfüllen', desc: 'AcroForm-Felder', icon: '📋', color: TILE },
      { id: 'tocEditor', label: 'Lesezeichen', desc: 'Inhaltsverzeichnis bearbeiten', icon: '🔖', color: TILE },
    ],
  },
  {
    key: 'seiten',
    title: 'Seiten & Struktur',
    icon: '📑',
    tools: [
      { id: 'merge', label: 'Zusammenführen', desc: 'Mehrere PDFs verbinden', icon: '📎', color: TILE },
      { id: 'split', label: 'Teilen', desc: 'PDF aufteilen', icon: '✂️', color: TILE },
      { id: 'rotate', label: 'Rotieren', desc: 'Seiten drehen', icon: '🔄', color: TILE },
      { id: 'pageEditor', label: 'Seiten ordnen', desc: 'Umsortieren & löschen', icon: '📑', color: TILE },
      { id: 'insertBlank', label: 'Leere Seiten', desc: 'Seiten einfügen', icon: '➕', color: TILE },
      { id: 'pdfCompare', label: 'PDF Vergleich', desc: 'Zwei PDFs vergleichen', icon: '⚖️', color: TILE },
    ],
  },
  {
    key: 'umwandeln',
    title: 'Umwandeln & Exportieren',
    icon: '🔁',
    tools: [
      { id: 'pdfToWord', label: 'PDF → Word', desc: 'Als DOCX exportieren', icon: '📝', color: TILE },
      { id: 'pdfToExcel', label: 'PDF → Excel', desc: 'Tabellen extrahieren', icon: '📊', color: TILE },
      { id: 'toImages', label: 'PDF → Bilder', desc: 'Als PNG/JPG exportieren', icon: '🖼️', color: TILE },
      { id: 'imagesToPdf', label: 'Bilder → PDF', desc: 'Bilder zu PDF', icon: '📄', color: TILE },
      { id: 'toText', label: 'PDF → Text', desc: 'Reinen Text extrahieren', icon: '📃', color: TILE },
      { id: 'pdfExport', label: 'PDF exportieren', desc: 'Markdown, HTML, JSON, CSV', icon: '📤', color: TILE },
      { id: 'ocr', label: 'OCR', desc: 'Texterkennung', icon: '🔍', color: TILE },
      { id: 'pdfa', label: 'PDF/A', desc: 'Archivformat', icon: '🗄️', color: TILE },
    ],
  },
  {
    key: 'schuetzen',
    title: 'Schützen & Signieren',
    icon: '🔏',
    tools: [
      { id: 'protect', label: 'Schützen / Entsperren', desc: 'Passwortschutz', icon: '🔒', color: TILE },
      { id: 'permissions', label: 'Rechteverwaltung', desc: 'Drucken/Kopieren einschränken', icon: '🛡️', color: TILE },
      { id: 'redact', label: 'Schwärzen', desc: 'Text unwiderruflich entfernen', icon: '⬛', color: TILE },
      { id: 'clean', label: 'Bereinigen', desc: 'Metadaten & Verstecktes entfernen', icon: '🧽', color: TILE },
      { id: 'flatten', label: 'Einbrennen', desc: 'Anmerkungen fixieren', icon: '🔥', color: TILE },
      { id: 'signDigital', label: 'Digital signieren', desc: 'Mit Zertifikat (PAdES)', icon: '🔏', color: TILE },
      { id: 'verifySignatures', label: 'Signatur prüfen', desc: 'Integrität & Unterzeichner', icon: '✅', color: TILE },
    ],
  },
  {
    key: 'stempel',
    title: 'Stempel & Nummern',
    icon: '🏷️',
    tools: [
      { id: 'watermark', label: 'Wasserzeichen', desc: 'Text oder Bild', icon: '💧', color: TILE },
      { id: 'pageNumbers', label: 'Seitenzahlen', desc: 'Nummerierung einfügen', icon: '🔢', color: TILE },
      { id: 'headerFooter', label: 'Kopf-/Fußzeile', desc: 'Text oben/unten', icon: '📰', color: TILE },
      { id: 'bates', label: 'Bates-Nummern', desc: 'Akten-Kennzeichnung', icon: '🏷️', color: TILE },
      { id: 'pruefakte', label: 'Prüfakte', desc: 'Akte mit Lesezeichen + Bates', icon: '🗂️', color: TILE },
    ],
  },
  {
    key: 'pruefen',
    title: 'Prüfen & Optimieren',
    icon: '🩺',
    tools: [
      { id: 'compress', label: 'Komprimieren', desc: 'Dateigröße reduzieren', icon: '🗜️', color: TILE },
      { id: 'scanOptimize', label: 'Scan optimieren', desc: 'Geraderücken + OCR', icon: '🧹', color: TILE },
      { id: 'qualityCheck', label: 'Qualitätsprüfung', desc: 'Leere/doppelte Seiten finden', icon: '🩺', color: TILE },
      { id: 'metadata', label: 'Metadaten', desc: 'Titel, Autor, Datum etc.', icon: 'ℹ️', color: TILE },
      { id: 'batch', label: 'Batch', desc: 'Viele Dateien auf einmal', icon: '📦', color: TILE },
      ...(aiAvailable.value
        ? [{ id: 'aiAssistant', label: 'KI-Assistent', desc: 'Zusammenfassen & Fragen (lokal)', icon: '🤖', color: TILE }]
        : []),
    ],
  },
  {
    key: 'office',
    title: 'Word & Office',
    icon: '🗃️',
    tools: [
      { id: 'wordToPdf', label: 'Word → PDF', desc: 'DOCX konvertieren', icon: '📝', color: TILE },
      { id: 'wordMerge', label: 'Word verbinden', desc: 'DOCX zusammenführen', icon: '📋', color: TILE },
      { id: 'wordDiff', label: 'Word Vergleich', desc: 'Unterschiede finden', icon: '🔍', color: TILE },
      { id: 'wordMeta', label: 'Word Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: TILE },
      { id: 'excelMeta', label: 'Excel Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: TILE },
      { id: 'officeToPdf', label: 'Office → PDF', desc: 'Excel, PowerPoint, ODF, RTF', icon: '🗃️', color: TILE },
    ],
  },
])

// ── Ansicht (ein Schalter) + Rolodex je Gruppe ────────────────

type ViewMode = 'grid' | 'rolodex'
const VIEW_KEY = 'pdfapp_view_mode'
const GROUP_KEY = 'pdfapp_rolodex_group'

const viewMode = ref<ViewMode>(
  localStorage.getItem(VIEW_KEY) === 'rolodex' ? 'rolodex' : 'grid',
)
const activeGroupKey = ref<string>(localStorage.getItem(GROUP_KEY) ?? 'bearbeiten')
const rolodexIndex = ref(0)
const rolodexEl = ref<HTMLElement | null>(null)

const groupTools = computed<Tool[]>(() => {
  const g = groups.value.find((g) => g.key === activeGroupKey.value)
  return g ? g.tools : groups.value[0].tools
})

function setViewMode(mode: ViewMode) {
  viewMode.value = mode
  localStorage.setItem(VIEW_KEY, mode)
  if (mode === 'rolodex') {
    rolodexIndex.value = Math.min(rolodexIndex.value, groupTools.value.length - 1)
  }
}

function setGroup(key: string) {
  activeGroupKey.value = key
  localStorage.setItem(GROUP_KEY, key)
  rolodexIndex.value = 0
  rolodexEl.value?.focus()
}

function step(dir: number) {
  const next = rolodexIndex.value + dir
  if (next >= 0 && next < groupTools.value.length) rolodexIndex.value = next
}

// Nach Klick auf die Pfeil-Knöpfe zurück zur Kartenliste fokussieren,
// damit die Pfeiltasten sofort weiterblättern (Befund aus dem UI-Test).
function stepAndFocus(dir: number) {
  step(dir)
  rolodexEl.value?.focus()
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
  // Linksbündiger Fächer wie im Videoarchiv: die aktive Karte steht am linken
  // Rand, die folgenden fächern nach rechts auf — kein Start in der Mitte.
  const offset = i - rolodexIndex.value
  const abs = Math.abs(offset)
  const translateX = 24 + offset * 165
  const rotateY = Math.max(-55, Math.min(55, offset * -35))
  const translateZ = -abs * 110
  const scale = offset === 0 ? 1 : Math.max(0.72, 1 - abs * 0.09)
  return {
    transform: `translateY(-50%) translateX(${translateX}px) translateZ(${translateZ}px) rotateY(${rotateY}deg) scale(${scale})`,
    // Nur transform animieren (GPU-Pfad, kein Layout/Paint je Frame) mit
    // ausklingender Kurve — animiert alles zugleich ruckelte spürbar.
    transition: 'transform 450ms cubic-bezier(0.22, 1, 0.36, 1), border-color 200ms',
    // Bewusst kein Ausblenden per opacity: die Tiefe entsteht über Skalierung,
    // Drehung und z-Index. Ein Fade würde den Textkontrast der hinteren Karten
    // unter die 4,5:1-Schwelle der BITV drücken (axe-Befund color-contrast).
    opacity: '1',
    zIndex: String(100 - abs),
    cursor: offset === 0 ? 'pointer' : 'ew-resize',
  }
}

onMounted(async () => {
  try {
    const health = await getHealth()
    aiAvailable.value = Boolean(health.features?.ai)
    lockedTools.value = new Set(health.login_required_tools ?? [])
  } catch {
    aiAvailable.value = false
    lockedTools.value = new Set()
  }
})
</script>
