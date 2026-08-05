<template>
  <div class="space-y-5">
    <ToolHeader title="Word-Dateien vergleichen" description="Inhaltliche Unterschiede zwischen Original und geändertem Dokument auswerten." @back="$emit('back')" />

    <div class="grid gap-4 sm:grid-cols-2">
      <FileDrop v-model="fileA" accept=".docx,.doc" label="Dokument A (Original)" />
      <FileDrop v-model="fileB" accept=".docx,.doc" label="Dokument B (Geändert)" />
    </div>

    <UiButton v-if="fileA && fileB" variant="primary" size="lg" :loading="loading" @click="doCompare">
      {{ loading ? 'Vergleiche…' : 'Vergleichen' }}
    </UiButton>

    <div v-if="result" class="space-y-4">
      <UiPanel>
        <div class="grid grid-cols-2 gap-4 text-center sm:grid-cols-5">
          <div><p class="text-2xl font-bold text-primary-600">{{ result.similarity }} %</p><p class="text-xs opacity-70">Übereinstimmung</p></div>
          <div><p class="text-2xl font-bold text-emerald-600">+{{ result.stats.added }}</p><p class="text-xs opacity-70">Hinzugefügt</p></div>
          <div><p class="text-2xl font-bold text-rose-600">−{{ result.stats.removed }}</p><p class="text-xs opacity-70">Entfernt</p></div>
          <div><p class="text-2xl font-bold text-amber-600">~{{ result.stats.changed }}</p><p class="text-xs opacity-70">Geändert</p></div>
          <div><p class="text-2xl font-bold">{{ result.stats.unchanged }}</p><p class="text-xs opacity-70">Unverändert</p></div>
        </div>
      </UiPanel>

      <div class="flex flex-wrap gap-2" aria-label="Vergleich filtern">
        <UiButton
          v-for="filter in filters"
          :key="filter.value"
          :variant="showFilter === filter.value ? 'primary' : 'secondary'"
          size="sm"
          :aria-pressed="showFilter === filter.value"
          @click="showFilter = filter.value"
        >{{ filter.label }}</UiButton>
      </div>

      <UiPanel padding="sm" class="max-h-[500px] overflow-y-auto !p-0">
        <div
          v-for="(change, index) in filteredChanges"
          :key="`${change.type}-${change.line_a ?? 0}-${change.line_b ?? 0}-${index}`"
          class="border-b border-gray-200 px-4 py-2 font-mono text-sm last:border-b-0 dark:border-gray-700"
          :class="{
            'bg-emerald-50 text-emerald-900 dark:bg-emerald-500/10 dark:text-emerald-100': change.type === 'added',
            'bg-rose-50 text-rose-900 dark:bg-rose-500/10 dark:text-rose-100': change.type === 'removed',
            'text-gray-600 dark:text-gray-300': change.type === 'equal',
          }"
        >
          <span class="mr-2 inline-block w-10 text-xs opacity-60">
            {{ change.type === 'added' ? '+' : change.type === 'removed' ? '−' : ' ' }}
            {{ change.line_a || change.line_b || '' }}
          </span>
          {{ change.text || '(leer)' }}
        </div>
        <p v-if="filteredChanges.length === 0" class="p-8 text-center text-gray-600 dark:text-gray-300">Keine Unterschiede für diesen Filter.</p>
      </UiPanel>
    </div>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (event: 'back'): void }>()

type ChangeType = 'added' | 'removed' | 'equal'
type FilterValue = 'all' | 'changes' | 'added' | 'removed'

interface WordChange {
  type: ChangeType
  text: string
  line_a?: number | null
  line_b?: number | null
}

interface WordDiffResult {
  similarity: number
  stats: {
    added: number
    removed: number
    changed: number
    unchanged: number
  }
  changes: WordChange[]
}

const { loading, error, withLoading, wordDiff } = usePdfTools()
const fileA = ref<File | null>(null)
const fileB = ref<File | null>(null)
const result = ref<WordDiffResult | null>(null)
const showFilter = ref<FilterValue>('all')

const filters: { value: FilterValue; label: string }[] = [
  { value: 'all', label: 'Alle' },
  { value: 'changes', label: 'Nur Änderungen' },
  { value: 'added', label: 'Hinzugefügt' },
  { value: 'removed', label: 'Entfernt' },
]

const filteredChanges = computed<WordChange[]>(() => {
  const changes = result.value?.changes ?? []
  if (showFilter.value === 'all') return changes
  if (showFilter.value === 'changes') return changes.filter((change) => change.type !== 'equal')
  return changes.filter((change) => change.type === showFilter.value)
})

async function doCompare(): Promise<void> {
  if (!fileA.value || !fileB.value) return
  result.value = null
  const data = await withLoading(() => wordDiff(fileA.value!, fileB.value!))
  if (data) result.value = data as WordDiffResult
}
</script>
