<template>
  <div>
    <!-- Aktives Werkzeug -->
    <div v-if="activeTool">
      <button
        class="mb-4 inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
        @click="activeTool = null"
      >
        ← Zurück zur Übersicht
      </button>
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
                   rounded-xl hover:border-purple-400 hover:shadow-md transition-all group"
            @click="activeTool = tool.id"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-xl" :class="tool.color">
              {{ tool.icon }}
            </div>
            <span class="text-sm font-medium text-gray-900 dark:text-white text-center">{{ tool.label }}</span>
            <span class="text-xs text-gray-400 text-center">{{ tool.desc }}</span>
          </button>
          <!-- Visueller Editor folgt in Phase 2 -->
          <div
            class="flex flex-col items-center gap-2 p-4 bg-gray-50 dark:bg-gray-800/50 border border-dashed border-gray-300 dark:border-gray-600
                   rounded-xl opacity-60 cursor-not-allowed"
            title="Der visuelle PDF-Editor folgt in einer späteren Version"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-xl bg-purple-200 dark:bg-purple-900/50">✏️</div>
            <span class="text-sm font-medium text-gray-900 dark:text-white text-center">PDF Editor</span>
            <span class="text-xs text-gray-400 text-center">Demnächst</span>
          </div>
        </div>
      </div>

      <div>
        <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">Word Werkzeuge</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <button
            v-for="tool in wordTools"
            :key="tool.id"
            class="flex flex-col items-center gap-2 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700
                   rounded-xl hover:border-blue-400 hover:shadow-md transition-all group"
            @click="activeTool = tool.id"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-xl" :class="tool.color">
              {{ tool.icon }}
            </div>
            <span class="text-sm font-medium text-gray-900 dark:text-white text-center">{{ tool.label }}</span>
            <span class="text-xs text-gray-400 text-center">{{ tool.desc }}</span>
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
                   rounded-xl hover:border-green-400 hover:shadow-md transition-all group"
            @click="activeTool = tool.id"
          >
            <div class="w-10 h-10 rounded-lg flex items-center justify-center text-xl" :class="tool.color">
              {{ tool.icon }}
            </div>
            <span class="text-sm font-medium text-gray-900 dark:text-white text-center">{{ tool.label }}</span>
            <span class="text-xs text-gray-400 text-center">{{ tool.desc }}</span>
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
  ocr: markRaw(PdfOcr),
  wordToPdf: markRaw(WordToPdf),
  wordMerge: markRaw(WordMerge),
  wordDiff: markRaw(WordDiff),
  wordMeta: markRaw(WordMetadata),
  excelMeta: markRaw(ExcelMetadata),
}

const pdfTools = [
  { id: 'merge', label: 'Zusammenführen', desc: 'Mehrere PDFs verbinden', icon: '📎', color: 'bg-red-100 dark:bg-red-900/30' },
  { id: 'split', label: 'Teilen', desc: 'PDF aufteilen', icon: '✂️', color: 'bg-orange-100 dark:bg-orange-900/30' },
  { id: 'rotate', label: 'Rotieren', desc: 'Seiten drehen', icon: '🔄', color: 'bg-yellow-100 dark:bg-yellow-900/30' },
  { id: 'toImages', label: 'PDF → Bilder', desc: 'Als PNG/JPG exportieren', icon: '🖼️', color: 'bg-teal-100 dark:bg-teal-900/30' },
  { id: 'compress', label: 'Komprimieren', desc: 'Dateigröße reduzieren', icon: '🗜️', color: 'bg-blue-100 dark:bg-blue-900/30' },
  { id: 'watermark', label: 'Wasserzeichen', desc: 'Text oder Bild', icon: '💧', color: 'bg-indigo-100 dark:bg-indigo-900/30' },
  { id: 'imagesToPdf', label: 'Bilder → PDF', desc: 'Bilder zu PDF', icon: '📄', color: 'bg-purple-100 dark:bg-purple-900/30' },
  { id: 'pageEditor', label: 'Seiten ordnen', desc: 'Umsortieren & löschen', icon: '📑', color: 'bg-pink-100 dark:bg-pink-900/30' },
  { id: 'pdfCompare', label: 'PDF Vergleich', desc: 'Zwei PDFs vergleichen', icon: '⚖️', color: 'bg-amber-100 dark:bg-amber-900/30' },
  { id: 'ocr', label: 'OCR', desc: 'Texterkennung', icon: '🔍', color: 'bg-cyan-100 dark:bg-cyan-900/30' },
  { id: 'protect', label: 'Schützen / Entsperren', desc: 'Passwortschutz', icon: '🔒', color: 'bg-emerald-100 dark:bg-emerald-900/30' },
  { id: 'pdfToWord', label: 'PDF → Word', desc: 'Als DOCX exportieren', icon: '📝', color: 'bg-sky-100 dark:bg-sky-900/30' },
  { id: 'pdfToExcel', label: 'PDF → Excel', desc: 'Tabellen extrahieren', icon: '📊', color: 'bg-lime-100 dark:bg-lime-900/30' },
  { id: 'metadata', label: 'Metadaten', desc: 'Titel, Autor, Datum etc.', icon: 'ℹ️', color: 'bg-gray-100 dark:bg-gray-700' },
]

const wordTools = [
  { id: 'wordToPdf', label: 'Word → PDF', desc: 'DOCX konvertieren', icon: '📝', color: 'bg-blue-100 dark:bg-blue-900/30' },
  { id: 'wordMerge', label: 'Word verbinden', desc: 'DOCX zusammenführen', icon: '📋', color: 'bg-blue-100 dark:bg-blue-900/30' },
  { id: 'wordDiff', label: 'Word Vergleich', desc: 'Unterschiede finden', icon: '🔍', color: 'bg-blue-100 dark:bg-blue-900/30' },
  { id: 'wordMeta', label: 'Word Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: 'bg-blue-100 dark:bg-blue-900/30' },
]

const excelTools = [
  { id: 'excelMeta', label: 'Excel Metadaten', desc: 'Eigenschaften ändern', icon: 'ℹ️', color: 'bg-green-100 dark:bg-green-900/30' },
]
</script>
