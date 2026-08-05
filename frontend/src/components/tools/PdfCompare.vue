<template>
  <div class="space-y-5">
    <ToolHeader title="PDF-Vergleich" description="Textliche und optionale visuelle Unterschiede zweier Dokumentstände auswerten." @back="$emit('back')" />

    <template v-if="!result">
      <div class="grid gap-4 sm:grid-cols-2">
        <FileDrop v-model="fileA" label="Version A (Original)" />
        <FileDrop v-model="fileB" label="Version B (Geändert)" />
      </div>

      <label class="ui-choice">
        <input v-model="includeVisual" type="checkbox" class="rounded" /> Visuellen Vergleich einschließen
      </label>

      <UiButton variant="primary" size="lg" :loading="loading" :disabled="!fileA || !fileB" @click="doCompare">
        {{ loading ? 'Vergleiche…' : 'Vergleichen' }}
      </UiButton>
    </template>

    <template v-else>
      <UiPanel>
        <div class="flex flex-wrap items-center gap-5">
          <div class="text-center">
            <p class="text-3xl font-bold" :class="similarityColor(result.average_similarity)">{{ result.average_similarity.toFixed(1) }} %</p>
            <p class="text-xs opacity-70">Übereinstimmung</p>
          </div>
          <div class="text-center"><p class="text-lg font-semibold">{{ result.pages_a }}</p><p class="text-xs opacity-70">Seiten A</p></div>
          <div class="text-center"><p class="text-lg font-semibold">{{ result.pages_b }}</p><p class="text-xs opacity-70">Seiten B</p></div>
          <div class="text-center"><p class="text-lg font-semibold text-emerald-600">{{ identicalPages }}</p><p class="text-xs opacity-70">Identisch</p></div>
          <div class="text-center"><p class="text-lg font-semibold text-amber-600">{{ modifiedPages }}</p><p class="text-xs opacity-70">Geändert</p></div>
          <UiButton variant="secondary" size="sm" class="ml-auto" @click="resetAll">Neuer Vergleich</UiButton>
        </div>
      </UiPanel>

      <div class="flex flex-wrap gap-2" role="tablist" aria-label="Vergleichsansicht">
        <UiButton
          v-for="tab in tabs"
          :id="`compare-tab-${tab.id}`"
          :key="tab.id"
          role="tab"
          size="sm"
          :variant="activeTab === tab.id ? 'primary' : 'secondary'"
          :aria-selected="activeTab === tab.id"
          :aria-controls="`compare-panel-${tab.id}`"
          @click="activeTab = tab.id"
        >{{ tab.label }}</UiButton>
      </div>

      <section
        v-if="activeTab === 'text'"
        id="compare-panel-text"
        role="tabpanel"
        aria-labelledby="compare-tab-text"
        class="max-h-[65vh] space-y-3 overflow-y-auto"
      >
        <UiPanel v-for="pageDiff in result.page_diffs" :key="pageDiff.page" padding="sm" class="!p-0">
          <button
            type="button"
            class="flex w-full items-center justify-between gap-3 rounded-[1.25rem] px-4 py-3 text-left font-semibold hover:bg-black/5 dark:hover:bg-white/10"
            :aria-expanded="expandedPages.has(pageDiff.page)"
            @click="togglePage(pageDiff.page)"
          >
            <span>Seite {{ pageDiff.page }}</span>
            <span class="rounded-full px-2.5 py-1 text-xs" :class="similarityBadge(pageDiff.similarity)">{{ pageDiff.similarity.toFixed(1) }} %</span>
          </button>
          <div v-if="expandedPages.has(pageDiff.page)" class="max-h-80 space-y-0.5 overflow-y-auto border-t border-gray-200 p-3 dark:border-gray-700">
            <div
              v-for="(change, index) in pageDiff.changes"
              :key="`${pageDiff.page}-${index}`"
              class="rounded px-2 py-1 font-mono text-xs leading-relaxed"
              :class="changeClass(change.type)"
            >
              <span class="mr-1 inline-block w-4 select-none text-center opacity-60">{{ changePrefix(change.type) }}</span>{{ change.text }}
            </div>
            <p v-if="pageDiff.changes.length === 0" class="py-4 text-center text-xs opacity-70">Keine Textunterschiede auf dieser Seite.</p>
          </div>
        </UiPanel>
        <UiAlert v-if="result.page_diffs.length === 0" tone="info">Keine Seitenvergleiche verfügbar.</UiAlert>
      </section>

      <section
        v-else-if="activeTab === 'visual'"
        id="compare-panel-visual"
        role="tabpanel"
        aria-labelledby="compare-tab-visual"
        class="space-y-4"
      >
        <template v-if="hasVisualData">
          <div class="flex flex-wrap items-center justify-center gap-3">
            <UiIconButton :disabled="visualPage <= 1" aria-label="Vorherige Vergleichsseite" @click="visualPage = Math.max(1, visualPage - 1)">←</UiIconButton>
            <span class="text-sm font-semibold tabular-nums">Seite {{ visualPage }} / {{ result.total_pages }}</span>
            <UiIconButton :disabled="visualPage >= result.total_pages" aria-label="Nächste Vergleichsseite" @click="visualPage = Math.min(result.total_pages, visualPage + 1)">→</UiIconButton>
            <label class="ui-choice"><input v-model="showDiffOverlay" type="checkbox" class="rounded" /> Diff-Overlay</label>
          </div>

          <div class="grid gap-4 lg:grid-cols-2">
            <UiPanel padding="sm">
              <p class="mb-2 text-center text-sm font-semibold">Version A</p>
              <img v-if="currentVisual?.image_a" :src="`data:image/png;base64,${currentVisual.image_a}`" class="h-auto w-full rounded-xl bg-white" alt="Gerenderte Vergleichsseite der Version A" />
              <UiAlert v-else tone="warning">Kein Bild verfügbar.</UiAlert>
            </UiPanel>
            <UiPanel padding="sm">
              <p class="mb-2 text-center text-sm font-semibold">{{ showDiffOverlay && currentVisual?.diff ? 'Diff-Overlay' : 'Version B' }}</p>
              <img v-if="showDiffOverlay && currentVisual?.diff" :src="`data:image/png;base64,${currentVisual.diff}`" class="h-auto w-full rounded-xl bg-white" alt="Visuelles Diff-Overlay" />
              <img v-else-if="currentVisual?.image_b" :src="`data:image/png;base64,${currentVisual.image_b}`" class="h-auto w-full rounded-xl bg-white" alt="Gerenderte Vergleichsseite der Version B" />
              <UiAlert v-else tone="warning">Kein Bild verfügbar.</UiAlert>
            </UiPanel>
          </div>

          <UiAlert v-if="currentPageDiff" tone="info">Seite {{ visualPage }}: {{ currentPageDiff.similarity.toFixed(1) }} % Übereinstimmung.</UiAlert>
        </template>
        <UiAlert v-else tone="warning">Keine visuellen Daten verfügbar. Starte den Vergleich erneut mit aktivierter visueller Prüfung.</UiAlert>
      </section>

      <section
        v-else
        id="compare-panel-stats"
        role="tabpanel"
        aria-labelledby="compare-tab-stats"
        class="space-y-5"
      >
        <UiPanel>
          <p class="text-center text-5xl font-bold" :class="similarityColor(result.average_similarity)">{{ result.average_similarity.toFixed(1) }} %</p>
          <p class="mt-1 text-center text-sm opacity-70">Durchschnittliche Übereinstimmung</p>
        </UiPanel>

        <UiPanel class="space-y-3">
          <h3 class="font-semibold">Übereinstimmung pro Seite</h3>
          <div v-for="pageDiff in result.page_diffs" :key="`bar-${pageDiff.page}`" class="flex items-center gap-3">
            <span class="w-12 shrink-0 text-right text-xs">S. {{ pageDiff.page }}</span>
            <div class="h-5 flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
              <div class="h-full rounded-full" :class="barColor(pageDiff.similarity)" :style="{ width: `${pageDiff.similarity}%` }"></div>
            </div>
            <span class="w-12 shrink-0 text-right text-xs font-semibold" :class="similarityColor(pageDiff.similarity)">{{ pageDiff.similarity.toFixed(0) }} %</span>
          </div>
        </UiPanel>

        <UiAlert v-if="extraPages > 0" tone="warning">
          {{ extraPages }} Seite(n) sind nur in {{ result.pages_a > result.pages_b ? 'Version A' : 'Version B' }} vorhanden.
        </UiAlert>
      </section>
    </template>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { runJob } from '@/lib/jobs'

defineEmits<{ (event: 'back'): void }>()

type CompareTab = 'text' | 'visual' | 'stats'
type DiffChangeType = 'added' | 'removed' | 'equal' | 'skip'

interface DiffChange {
  type: DiffChangeType
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

const tabs: { id: CompareTab; label: string }[] = [
  { id: 'text', label: 'Text-Diff' },
  { id: 'visual', label: 'Visueller Vergleich' },
  { id: 'stats', label: 'Statistik' },
]

const fileA = ref<File | null>(null)
const fileB = ref<File | null>(null)
const includeVisual = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<CompareResult | null>(null)
const activeTab = ref<CompareTab>('text')
const expandedPages = ref<Set<number>>(new Set())
const visualPage = ref(1)
const showDiffOverlay = ref(false)

const identicalPages = computed(() => result.value?.page_diffs.filter((page) => page.similarity >= 99.9).length ?? 0)
const modifiedPages = computed(() => result.value?.page_diffs.filter((page) => page.similarity < 99.9).length ?? 0)
const extraPages = computed(() => result.value ? Math.abs(result.value.pages_a - result.value.pages_b) : 0)
const currentPageDiff = computed(() => result.value?.page_diffs.find((page) => page.page === visualPage.value) ?? null)
const currentVisual = computed(() => currentPageDiff.value?.visual ?? null)
const hasVisualData = computed(() => result.value?.page_diffs.some((page) => Boolean(page.visual?.image_a || page.visual?.image_b)) ?? false)

async function doCompare(): Promise<void> {
  if (!fileA.value || !fileB.value) return
  loading.value = true
  error.value = null
  result.value = null
  try {
    const fd = new FormData()
    fd.append('file_a', fileA.value)
    fd.append('file_b', fileB.value)
    fd.append('include_visual', String(includeVisual.value))
    const response = await runJob('/api/pdf-extras/jobs/compare', fd)
    const data = await response.json() as CompareResult
    result.value = data
    activeTab.value = 'text'
    visualPage.value = 1
    showDiffOverlay.value = false
    const firstModified = data.page_diffs.find((page) => page.similarity < 99.9) ?? data.page_diffs[0]
    expandedPages.value = firstModified ? new Set([firstModified.page]) : new Set()
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler beim Vergleich.'
  } finally {
    loading.value = false
  }
}

function resetAll(): void {
  result.value = null
  fileA.value = null
  fileB.value = null
  error.value = null
  activeTab.value = 'text'
  visualPage.value = 1
  showDiffOverlay.value = false
  expandedPages.value = new Set()
}

function togglePage(page: number): void {
  const next = new Set(expandedPages.value)
  if (next.has(page)) next.delete(page)
  else next.add(page)
  expandedPages.value = next
}

function changeClass(type: DiffChangeType): string {
  if (type === 'removed') return 'bg-rose-100 text-rose-900 dark:bg-rose-500/15 dark:text-rose-100'
  if (type === 'added') return 'bg-emerald-100 text-emerald-900 dark:bg-emerald-500/15 dark:text-emerald-100'
  if (type === 'skip') return 'italic text-gray-500 dark:text-gray-400'
  return 'text-gray-700 dark:text-gray-200'
}

function changePrefix(type: DiffChangeType): string {
  if (type === 'removed') return '−'
  if (type === 'added') return '+'
  return ' '
}

function similarityColor(similarity: number): string {
  if (similarity >= 95) return 'text-emerald-600 dark:text-emerald-400'
  if (similarity >= 70) return 'text-amber-600 dark:text-amber-400'
  return 'text-rose-600 dark:text-rose-400'
}

function similarityBadge(similarity: number): string {
  if (similarity >= 95) return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200'
  if (similarity >= 70) return 'bg-amber-100 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200'
  return 'bg-rose-100 text-rose-800 dark:bg-rose-500/15 dark:text-rose-200'
}

function barColor(similarity: number): string {
  if (similarity >= 95) return 'bg-emerald-500'
  if (similarity >= 70) return 'bg-amber-500'
  return 'bg-rose-500'
}
</script>
