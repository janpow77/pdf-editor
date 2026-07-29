<template>
  <div>
    <!-- Aktives Werkzeug -->
    <div v-if="activeTool">
      <component :is="toolComponents[activeTool]" @back="activeTool = null" />
    </div>

    <!-- Werkzeug-Auswahl -->
    <div v-else class="space-y-6">
      <div>
        <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">PDF Werkzeuge</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <button
            v-for="tool in pdfTools"
            :key="tool.id"
            class="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                   rounded-xl hover:border-primary-400 hover:shadow-md transition-all group"
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

      <div>
        <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Word Werkzeuge</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <button
            v-for="tool in wordTools"
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

      <div>
        <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Excel Werkzeuge</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <button
            v-for="tool in excelTools"
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { markRaw, ref, type Component } from 'vue'
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
import PdfPdfa from '@/components/tools/PdfPdfa.vue'
import PdfSignImage from '@/components/tools/PdfSignImage.vue'
import PdfAnnotate from '@/components/tools/PdfAnnotate.vue'
import PdfSignDigital from '@/components/tools/PdfSignDigital.vue'
import PdfScanOptimize from '@/components/tools/PdfScanOptimize.vue'
import PdfBatch from '@/components/tools/PdfBatch.vue'
import PdfTocEditor from '@/components/tools/PdfTocEditor.vue'
import PdfOcr from '@/components/tools/PdfOcr.vue'
import WordToPdf from '@/components/tools/WordToPdf.vue'
import WordMerge from '@/components/tools/WordMerge.vue'
import WordDiff from '@/components/tools/WordDiff.vue'
import WordMetadata from '@/components/tools/WordMetadata.vue'
import ExcelMetadata from '@/components/tools/ExcelMetadata.vue'

const activeTool = ref<string | null>(null)

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
  pdfa: markRaw(PdfPdfa),
  signImage: markRaw(PdfSignImage),
  annotate: markRaw(PdfAnnotate),
  signDigital: markRaw(PdfSignDigital),
  scanOptimize: markRaw(PdfScanOptimize),
  batch: markRaw(PdfBatch),
  tocEditor: markRaw(PdfTocEditor),
  ocr: markRaw(PdfOcr),
  wordToPdf: markRaw(WordToPdf),
  wordMerge: markRaw(WordMerge),
  wordDiff: markRaw(WordDiff),
  wordMeta: markRaw(WordMetadata),
  excelMeta: markRaw(ExcelMetadata),
}

const pdfTools = [
  { id: 'textEditor', label: 'Text bearbeiten', desc: 'WYSIWYG im Dokument', icon: '✏️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'annotate', label: 'Anmerkungen', desc: 'Markieren, Stempel, Zeichnen', icon: '🖍️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'merge', label: 'Zusammenführen', desc: 'Mehrere PDFs verbinden', icon: '📎', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'split', label: 'Teilen', desc: 'PDF aufteilen', icon: '✂️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'rotate', label: 'Rotieren', desc: 'Seiten drehen', icon: '🔄', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'toImages', label: 'PDF → Bilder', desc: 'Als PNG/JPG exportieren', icon: '🖼️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'compress', label: 'Komprimieren', desc: 'Dateigröße reduzieren', icon: '🗜️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'watermark', label: 'Wasserzeichen', desc: 'Text oder Bild', icon: '💧', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'imagesToPdf', label: 'Bilder → PDF', desc: 'Bilder zu PDF', icon: '📄', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'pageEditor', label: 'Seiten ordnen', desc: 'Umsortieren & löschen', icon: '📑', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'pdfCompare', label: 'PDF Vergleich', desc: 'Zwei PDFs vergleichen', icon: '⚖️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'ocr', label: 'OCR', desc: 'Texterkennung', icon: '🔍', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'protect', label: 'Schützen / Entsperren', desc: 'Passwortschutz', icon: '🔒', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'pdfToWord', label: 'PDF → Word', desc: 'Als DOCX exportieren', icon: '📝', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'pdfToExcel', label: 'PDF → Excel', desc: 'Tabellen extrahieren', icon: '📊', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'metadata', label: 'Metadaten', desc: 'Titel, Autor, Datum etc.', icon: 'ℹ️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'toText', label: 'PDF → Text', desc: 'Reinen Text extrahieren', icon: '📃', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'searchReplace', label: 'Suchen & Ersetzen', desc: 'Text austauschen', icon: '🔁', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'redact', label: 'Schwärzen', desc: 'Text unwiderruflich entfernen', icon: '⬛', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'pageNumbers', label: 'Seitenzahlen', desc: 'Nummerierung einfügen', icon: '🔢', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'headerFooter', label: 'Kopf-/Fußzeile', desc: 'Text oben/unten', icon: '📰', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'bates', label: 'Bates-Nummern', desc: 'Akten-Kennzeichnung', icon: '🏷️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'formFill', label: 'Formular ausfüllen', desc: 'AcroForm-Felder', icon: '📋', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'signImage', label: 'Unterschrift', desc: 'Bild-Signatur einfügen', icon: '✍️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'pdfa', label: 'PDF/A', desc: 'Archivformat', icon: '🗄️', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'flatten', label: 'Einbrennen', desc: 'Anmerkungen fixieren', icon: '🔥', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'signDigital', label: 'Digital signieren', desc: 'Mit Zertifikat (PAdES)', icon: '🔏', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'scanOptimize', label: 'Scan optimieren', desc: 'Geraderücken + OCR', icon: '🧹', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'batch', label: 'Batch', desc: 'Viele Dateien auf einmal', icon: '📦', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'tocEditor', label: 'Lesezeichen', desc: 'Inhaltsverzeichnis bearbeiten', icon: '🔖', color: 'bg-gray-100 dark:bg-gray-700/60' },
]

const wordTools = [
  { id: 'wordToPdf', label: 'Word → PDF', desc: 'DOCX konvertieren', icon: '📝', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'wordMerge', label: 'Word verbinden', desc: 'DOCX zusammenführen', icon: '📋', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'wordDiff', label: 'Word Vergleich', desc: 'Unterschiede finden', icon: '🔍', color: 'bg-gray-100 dark:bg-gray-700/60' },
  { id: 'wordMeta', label: 'Word Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: 'bg-gray-100 dark:bg-gray-700/60' },
]

const excelTools = [
  { id: 'excelMeta', label: 'Excel Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: 'bg-gray-100 dark:bg-gray-700/60' },
]
</script>
