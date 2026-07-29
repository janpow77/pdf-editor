<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center gap-3">
      <button
        class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1"
        @click="$emit('back')"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Zurueck
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF Vergleich</h2>
    </div>

    <!-- Upload area (before comparison) -->
    <div v-if="!result" class="space-y-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <!-- Version A upload -->
        <div
          class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
          :class="fileA ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
          @dragover.prevent
          @drop.prevent="onDropA"
        >
          <input
            ref="fileInputA"
            type="file"
            accept=".pdf"
            class="hidden"
            @change="(e: Event) => onSelectFile(e, 'A')"
          />
          <p class="text-xs text-gray-400 mb-2">Version A (Original)</p>
          <div v-if="!fileA">
            <p class="text-gray-500 dark:text-gray-400 mb-2 text-sm">PDF hierher ziehen oder</p>
            <button
              class="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700"
              @click="($refs.fileInputA as HTMLInputElement).click()"
            >
              Auswaehlen
            </button>
          </div>
          <div v-else class="space-y-1">
            <p class="font-medium text-gray-900 dark:text-white truncate">{{ fileA.name }}</p>
            <p class="text-xs text-gray-500">{{ formatSize(fileA.size) }}</p>
            <button class="text-xs text-red-500 hover:text-red-700" @click="fileA = null">
              Entfernen
            </button>
          </div>
        </div>

        <!-- Version B upload -->
        <div
          class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
          :class="fileB ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
          @dragover.prevent
          @drop.prevent="onDropB"
        >
          <input
            ref="fileInputB"
            type="file"
            accept=".pdf"
            class="hidden"
            @change="(e: Event) => onSelectFile(e, 'B')"
          />
          <p class="text-xs text-gray-400 mb-2">Version B (Geaendert)</p>
          <div v-if="!fileB">
            <p class="text-gray-500 dark:text-gray-400 mb-2 text-sm">PDF hierher ziehen oder</p>
            <button
              class="px-3 py-1.5 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700"
              @click="($refs.fileInputB as HTMLInputElement).click()"
            >
              Auswaehlen
            </button>
          </div>
          <div v-else class="space-y-1">
            <p class="font-medium text-gray-900 dark:text-white truncate">{{ fileB.name }}</p>
            <p class="text-xs text-gray-500">{{ formatSize(fileB.size) }}</p>
            <button class="text-xs text-red-500 hover:text-red-700" @click="fileB = null">
              Entfernen
            </button>
          </div>
        </div>
      </div>

      <!-- Visual toggle + compare button -->
      <div class="flex items-center justify-center gap-4">
        <label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <input
            v-model="includeVisual"
            type="checkbox"
            class="rounded border-gray-300 dark:border-gray-600 text-purple-600 focus:ring-purple-500"
          />
          Visuellen Vergleich einschliessen
        </label>
      </div>

      <div class="text-center">
        <button
          :disabled="!fileA || !fileB || loading"
          class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700
                 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
          @click="doCompare"
        >
          <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ loading ? 'Vergleiche...' : 'Vergleichen' }}
        </button>
      </div>
    </div>

    <!-- Results -->
    <div v-if="result" class="space-y-4">
      <!-- Summary bar -->
      <div
        class="flex flex-wrap items-center gap-4 p-4 bg-white dark:bg-gray-900
               border border-gray-200 dark:border-gray-700 rounded-xl"
      >
        <div class="text-center">
          <p
            class="text-3xl font-bold"
            :class="similarityColor(result.average_similarity)"
          >
            {{ result.average_similarity.toFixed(1) }}%
          </p>
          <p class="text-xs text-gray-500">Uebereinstimmung</p>
        </div>
        <div class="h-10 border-l border-gray-200 dark:border-gray-700" />
        <div class="text-center">
          <p class="text-lg font-semibold text-gray-900 dark:text-white">{{ result.pages_a }}</p>
          <p class="text-xs text-gray-500">Seiten A</p>
        </div>
        <div class="text-center">
          <p class="text-lg font-semibold text-gray-900 dark:text-white">{{ result.pages_b }}</p>
          <p class="text-xs text-gray-500">Seiten B</p>
        </div>
        <div class="text-center">
          <p class="text-lg font-semibold text-green-600">{{ identicalPages }}</p>
          <p class="text-xs text-gray-500">Identisch</p>
        </div>
        <div class="text-center">
          <p class="text-lg font-semibold text-amber-600">{{ modifiedPages }}</p>
          <p class="text-xs text-gray-500">Geaendert</p>
        </div>
        <button
          class="ml-auto text-sm text-gray-500 hover:text-purple-600 flex items-center gap-1"
          @click="resetAll"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Neuer Vergleich
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-gray-200 dark:border-gray-700">
        <button
          v-for="t in tabs"
          :key="t.id"
          class="px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px"
          :class="activeTab === t.id
            ? 'border-purple-500 text-purple-600 dark:text-purple-400'
            : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'"
          @click="activeTab = t.id"
        >
          {{ t.label }}
        </button>
      </div>

      <!-- Tab: Text-Diff -->
      <div v-if="activeTab === 'text'" class="space-y-2 max-h-[60vh] overflow-y-auto">
        <div
          v-for="pd in result.page_diffs"
          :key="pd.page"
          class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
        >
          <!-- Page header (collapsible) -->
          <div
            class="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800 cursor-pointer select-none"
            @click="togglePage(pd.page)"
          >
            <div class="flex items-center gap-2">
              <svg
                class="w-4 h-4 text-gray-400 transition-transform"
                :class="{ 'rotate-90': expandedPages.has(pd.page) }"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
              <span class="font-medium text-sm text-gray-900 dark:text-white">Seite {{ pd.page }}</span>
            </div>
            <span
              class="text-xs font-medium px-2 py-0.5 rounded-full"
              :class="similarityBadge(pd.similarity)"
            >
              {{ pd.similarity.toFixed(1) }}%
            </span>
          </div>

          <!-- Diff lines -->
          <div v-if="expandedPages.has(pd.page)" class="p-2 space-y-0 max-h-80 overflow-y-auto">
            <div
              v-for="(change, ci) in pd.changes"
              :key="ci"
              class="px-2 py-0.5 font-mono text-xs leading-relaxed rounded-sm"
              :class="changeClass(change.type)"
            >
              <span class="inline-block w-4 text-center select-none opacity-60">
                {{ changePrefix(change.type) }}
              </span>
              {{ change.text }}
            </div>
            <div
              v-if="!pd.changes || pd.changes.length === 0"
              class="py-4 text-center text-xs text-gray-400"
            >
              Keine Textunterschiede auf dieser Seite
            </div>
          </div>
        </div>

        <div
          v-if="!result.page_diffs || result.page_diffs.length === 0"
          class="py-8 text-center text-gray-400"
        >
          Keine Seitenvergleiche verfuegbar
        </div>
      </div>

      <!-- Tab: Visual-Diff -->
      <div v-else-if="activeTab === 'visual'" class="space-y-4">
        <div v-if="hasVisualData" class="space-y-4">
          <!-- Page navigation -->
          <div class="flex items-center justify-center gap-3">
            <button
              :disabled="visualPage <= 1"
              class="px-3 py-1 text-sm rounded-lg border border-gray-200 dark:border-gray-700
                     hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
              @click="visualPage = Math.max(1, visualPage - 1)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span class="text-sm text-gray-600 dark:text-gray-400">
              Seite {{ visualPage }} / {{ result.total_pages }}
            </span>
            <button
              :disabled="visualPage >= result.total_pages"
              class="px-3 py-1 text-sm rounded-lg border border-gray-200 dark:border-gray-700
                     hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
              @click="visualPage = Math.min(result.total_pages, visualPage + 1)"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </button>
            <label class="ml-4 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
              <input
                v-model="showDiffOverlay"
                type="checkbox"
                class="rounded border-gray-300 dark:border-gray-600 text-purple-600 focus:ring-purple-500"
              />
              Diff-Overlay
            </label>
          </div>

          <!-- Side-by-side images -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <p class="text-xs text-center mb-1 text-gray-500 dark:text-gray-400 font-medium">
                Version A
              </p>
              <div
                class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900"
              >
                <img
                  v-if="currentVisual?.image_a"
                  :src="'data:image/png;base64,' + currentVisual.image_a"
                  class="w-full h-auto"
                  alt="Version A"
                />
                <div v-else class="py-12 text-center text-xs text-gray-400">
                  Kein Bild verfuegbar
                </div>
              </div>
            </div>
            <div>
              <p class="text-xs text-center mb-1 text-gray-500 dark:text-gray-400 font-medium">
                {{ showDiffOverlay && currentVisual?.diff ? 'Diff-Overlay' : 'Version B' }}
              </p>
              <div
                class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-900"
              >
                <img
                  v-if="showDiffOverlay && currentVisual?.diff"
                  :src="'data:image/png;base64,' + currentVisual.diff"
                  class="w-full h-auto"
                  alt="Diff-Overlay"
                />
                <img
                  v-else-if="currentVisual?.image_b"
                  :src="'data:image/png;base64,' + currentVisual.image_b"
                  class="w-full h-auto"
                  alt="Version B"
                />
                <div v-else class="py-12 text-center text-xs text-gray-400">
                  Kein Bild verfuegbar
                </div>
              </div>
            </div>
          </div>

          <!-- Current page similarity -->
          <div v-if="currentPageDiff" class="text-center">
            <span
              class="text-xs font-medium px-3 py-1 rounded-full"
              :class="similarityBadge(currentPageDiff.similarity)"
            >
              Seite {{ visualPage }}: {{ currentPageDiff.similarity.toFixed(1) }}% Uebereinstimmung
            </span>
          </div>
        </div>

        <div v-else class="py-12 text-center text-gray-400">
          <p class="text-sm">Keine visuellen Daten verfuegbar.</p>
          <p class="text-xs mt-1">
            Fuehren Sie den Vergleich mit aktiviertem "Visuellen Vergleich" erneut durch.
          </p>
        </div>
      </div>

      <!-- Tab: Statistik -->
      <div v-else-if="activeTab === 'stats'" class="space-y-6 p-4">
        <!-- Overall similarity -->
        <div class="text-center">
          <p
            class="text-6xl font-bold"
            :class="similarityColor(result.average_similarity)"
          >
            {{ result.average_similarity.toFixed(1) }}%
          </p>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Durchschnittliche Uebereinstimmung
          </p>
        </div>

        <!-- Summary cards -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ result.pages_a }}</p>
            <p class="text-xs text-gray-500">Seiten A</p>
          </div>
          <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-gray-900 dark:text-white">{{ result.pages_b }}</p>
            <p class="text-xs text-gray-500">Seiten B</p>
          </div>
          <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-green-600">{{ identicalPages }}</p>
            <p class="text-xs text-gray-500">Identisch</p>
          </div>
          <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 text-center">
            <p class="text-2xl font-bold text-amber-600">{{ modifiedPages }}</p>
            <p class="text-xs text-gray-500">Geaendert</p>
          </div>
        </div>

        <!-- Per-page similarity bar chart -->
        <div
          class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4"
        >
          <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            Uebereinstimmung pro Seite
          </h3>
          <div class="space-y-2">
            <div
              v-for="pd in result.page_diffs"
              :key="'bar-' + pd.page"
              class="flex items-center gap-3"
            >
              <span class="text-xs text-gray-500 w-12 text-right shrink-0">
                S. {{ pd.page }}
              </span>
              <div class="flex-1 h-5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :class="barColor(pd.similarity)"
                  :style="{ width: pd.similarity + '%' }"
                />
              </div>
              <span
                class="text-xs font-medium w-12 text-right shrink-0"
                :class="similarityColor(pd.similarity)"
              >
                {{ pd.similarity.toFixed(0) }}%
              </span>
            </div>
          </div>
          <div
            v-if="!result.page_diffs || result.page_diffs.length === 0"
            class="py-6 text-center text-xs text-gray-400"
          >
            Keine Seitendaten verfuegbar
          </div>
        </div>

        <!-- Extra pages info -->
        <div
          v-if="extraPages > 0"
          class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg p-3"
        >
          <p class="text-sm text-amber-800 dark:text-amber-300">
            {{ extraPages }} Seite(n) nur in
            {{ result.pages_a > result.pages_b ? 'Version A' : 'Version B' }} vorhanden.
          </p>
        </div>
      </div>
    </div>

    <!-- Error message -->
    <p v-if="error" class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { runJob } from '@/lib/jobs'

defineEmits<{ (e: 'back'): void }>()

// ── Types ──────────────────────────────────────────────────────────────────

interface DiffChange {
  type: 'added' | 'removed' | 'equal' | 'skip'
  text: string
}

interface VisualData {
  image_a?: string
  image_b?: string
  diff?: string
}

interface PageDiff {
  page: number
  similarity: number
  changes: DiffChange[]
  visual?: VisualData
}

interface CompareResult {
  pages_a: number
  pages_b: number
  total_pages: number
  average_similarity: number
  page_diffs: PageDiff[]
}

// ── Constants ──────────────────────────────────────────────────────────────

const API_BASE = '/api/pdf-editor'
const TIMEOUT = 5 * 60 * 1000

const tabs = [
  { id: 'text' as const, label: 'Text-Diff' },
  { id: 'visual' as const, label: 'Visueller Vergleich' },
  { id: 'stats' as const, label: 'Statistik' },
]

// ── State ──────────────────────────────────────────────────────────────────

const fileA = ref<File | null>(null)
const fileB = ref<File | null>(null)
const includeVisual = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<CompareResult | null>(null)

const activeTab = ref<'text' | 'visual' | 'stats'>('text')
const expandedPages = ref<Set<number>>(new Set())
const visualPage = ref(1)
const showDiffOverlay = ref(false)

// ── Computed ───────────────────────────────────────────────────────────────

const identicalPages = computed(() => {
  if (!result.value?.page_diffs) return 0
  return result.value.page_diffs.filter((pd) => pd.similarity >= 99.9).length
})

const modifiedPages = computed(() => {
  if (!result.value?.page_diffs) return 0
  return result.value.page_diffs.filter((pd) => pd.similarity < 99.9).length
})

const extraPages = computed(() => {
  if (!result.value) return 0
  return Math.abs(result.value.pages_a - result.value.pages_b)
})

const currentVisual = computed<VisualData | null>(() => {
  if (!result.value?.page_diffs) return null
  const pd = result.value.page_diffs.find((p) => p.page === visualPage.value)
  return pd?.visual || null
})

const currentPageDiff = computed<PageDiff | null>(() => {
  if (!result.value?.page_diffs) return null
  return result.value.page_diffs.find((p) => p.page === visualPage.value) || null
})

const hasVisualData = computed(() => {
  if (!result.value?.page_diffs) return false
  return result.value.page_diffs.some(
    (pd) => pd.visual && (pd.visual.image_a || pd.visual.image_b)
  )
})

// ── File handling ──────────────────────────────────────────────────────────

function onSelectFile(e: Event, side: 'A' | 'B') {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0] || null
  if (side === 'A') fileA.value = f
  else fileB.value = f
}

function onDropA(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f && f.name.toLowerCase().endsWith('.pdf')) fileA.value = f
}

function onDropB(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f && f.name.toLowerCase().endsWith('.pdf')) fileB.value = f
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// ── Compare ────────────────────────────────────────────────────────────────

async function doCompare() {
  if (!fileA.value || !fileB.value) return

  loading.value = true
  error.value = null
  result.value = null

  try {
    const fd = new FormData()
    fd.append('file_a', fileA.value)
    fd.append('file_b', fileB.value)
    fd.append('include_visual', String(includeVisual.value))

    // Async-Job: übersteht auch sehr große Dateien ohne Browser-Timeout
    const response = await runJob('/api/pdf-extras/jobs/compare', fd)

    const data: CompareResult = await response.json()
    result.value = data

    // Reset view state
    activeTab.value = 'text'
    visualPage.value = 1
    showDiffOverlay.value = false
    expandedPages.value = new Set()

    // Auto-expand first page with changes
    if (data.page_diffs && data.page_diffs.length > 0) {
      const firstModified = data.page_diffs.find((pd) => pd.similarity < 99.9)
      if (firstModified) {
        expandedPages.value.add(firstModified.page)
      } else {
        expandedPages.value.add(data.page_diffs[0].page)
      }
    }
  } catch (e: any) {
    if (e.name === 'AbortError') {
      error.value = 'Zeitueberschreitung: Der Vergleich hat zu lange gedauert.'
    } else {
      error.value = e.message || 'Unbekannter Fehler beim Vergleich'
    }
  } finally {
    loading.value = false
  }
}

// ── UI helpers ─────────────────────────────────────────────────────────────

function resetAll() {
  result.value = null
  fileA.value = null
  fileB.value = null
  error.value = null
  activeTab.value = 'text'
  visualPage.value = 1
  showDiffOverlay.value = false
  expandedPages.value = new Set()
}

function togglePage(page: number) {
  const pages = new Set(expandedPages.value)
  if (pages.has(page)) {
    pages.delete(page)
  } else {
    pages.add(page)
  }
  expandedPages.value = pages
}

function changeClass(type: string): string {
  switch (type) {
    case 'removed':
      return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
    case 'added':
      return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
    case 'skip':
      return 'text-gray-400 dark:text-gray-600 italic'
    default:
      return 'text-gray-700 dark:text-gray-300'
  }
}

function changePrefix(type: string): string {
  switch (type) {
    case 'removed':
      return '-'
    case 'added':
      return '+'
    default:
      return ' '
  }
}

function similarityColor(similarity: number): string {
  if (similarity >= 95) return 'text-green-600 dark:text-green-400'
  if (similarity >= 70) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function similarityBadge(similarity: number): string {
  if (similarity >= 95)
    return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
  if (similarity >= 70)
    return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
  return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
}

function barColor(similarity: number): string {
  if (similarity >= 95) return 'bg-green-500'
  if (similarity >= 70) return 'bg-amber-500'
  return 'bg-red-500'
}
</script>
