<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Word-Dateien vergleichen</h2>
    </div>

    <!-- Two file uploads -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div
        class="border-2 border-dashed rounded-xl p-4 text-center transition-colors"
        :class="fileA ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
        @dragover.prevent
        @drop.prevent="onDropA"
      >
        <input ref="fileInputA" type="file" accept=".docx,.doc" class="hidden" @change="(e: Event) => fileA = (e.target as HTMLInputElement).files?.[0] || null" />
        <p class="text-xs text-gray-400 mb-1">Dokument A (Original)</p>
        <div v-if="!fileA">
          <button class="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700" @click="($refs.fileInputA as HTMLInputElement).click()">Auswählen</button>
        </div>
        <div v-else>
          <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ fileA.name }}</p>
          <button class="text-xs text-red-500 hover:text-red-700" @click="fileA = null; result = null">Entfernen</button>
        </div>
      </div>
      <div
        class="border-2 border-dashed rounded-xl p-4 text-center transition-colors"
        :class="fileB ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
        @dragover.prevent
        @drop.prevent="onDropB"
      >
        <input ref="fileInputB" type="file" accept=".docx,.doc" class="hidden" @change="(e: Event) => fileB = (e.target as HTMLInputElement).files?.[0] || null" />
        <p class="text-xs text-gray-400 mb-1">Dokument B (Geändert)</p>
        <div v-if="!fileB">
          <button class="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700" @click="($refs.fileInputB as HTMLInputElement).click()">Auswählen</button>
        </div>
        <div v-else>
          <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ fileB.name }}</p>
          <button class="text-xs text-red-500 hover:text-red-700" @click="fileB = null; result = null">Entfernen</button>
        </div>
      </div>
    </div>

    <button
      v-if="fileA && fileB"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doCompare"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Vergleiche...' : 'Vergleichen' }}
    </button>

    <!-- Results -->
    <div v-if="result" class="space-y-4">
      <!-- Stats -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-4 text-center">
          <div>
            <p class="text-2xl font-bold text-primary-600">{{ result.similarity }}%</p>
            <p class="text-xs text-gray-500">Übereinstimmung</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-green-600">+{{ result.stats.added }}</p>
            <p class="text-xs text-gray-500">Hinzugefügt</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-red-600">-{{ result.stats.removed }}</p>
            <p class="text-xs text-gray-500">Entfernt</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-amber-600">~{{ result.stats.changed }}</p>
            <p class="text-xs text-gray-500">Geändert</p>
          </div>
          <div>
            <p class="text-2xl font-bold text-gray-600 dark:text-gray-300">{{ result.stats.unchanged }}</p>
            <p class="text-xs text-gray-500">Unverändert</p>
          </div>
        </div>
      </div>

      <!-- Filter -->
      <div class="flex gap-2">
        <button
          v-for="f in filters"
          :key="f.value"
          class="px-3 py-1 text-xs rounded-full transition-colors"
          :class="showFilter === f.value ? 'bg-primary-600 text-white' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300'"
          @click="showFilter = f.value"
        >
          {{ f.label }}
        </button>
      </div>

      <!-- Diff view -->
      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden max-h-[500px] overflow-y-auto">
        <div
          v-for="(change, idx) in filteredChanges"
          :key="idx"
          class="px-4 py-2 border-b border-gray-100 dark:border-gray-800 text-sm font-mono"
          :class="{
            'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300': change.type === 'added',
            'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-300': change.type === 'removed',
            'text-gray-600 dark:text-gray-400': change.type === 'equal',
          }"
        >
          <span class="text-xs text-gray-400 mr-2 inline-block w-10">
            {{ change.type === 'added' ? '+' : change.type === 'removed' ? '-' : ' ' }}
            {{ change.line_a || change.line_b || '' }}
          </span>
          {{ change.text || '(leer)' }}
        </div>
        <div v-if="filteredChanges.length === 0" class="p-8 text-center text-gray-400">
          Keine Unterschiede für diesen Filter
        </div>
      </div>
    </div>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, wordDiff } = usePdfTools()
const fileA = ref<File | null>(null)
const fileB = ref<File | null>(null)
const result = ref<any>(null)
const showFilter = ref('all')

const filters = [
  { value: 'all', label: 'Alle' },
  { value: 'changes', label: 'Nur Änderungen' },
  { value: 'added', label: 'Hinzugefügt' },
  { value: 'removed', label: 'Entfernt' },
]

const filteredChanges = computed(() => {
  if (!result.value?.changes) return []
  if (showFilter.value === 'all') return result.value.changes
  if (showFilter.value === 'changes') return result.value.changes.filter((c: any) => c.type !== 'equal')
  return result.value.changes.filter((c: any) => c.type === showFilter.value)
})

function onDropA(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f && (f.name.endsWith('.docx') || f.name.endsWith('.doc'))) fileA.value = f
}

function onDropB(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f && (f.name.endsWith('.docx') || f.name.endsWith('.doc'))) fileB.value = f
}

async function doCompare() {
  if (!fileA.value || !fileB.value) return
  const data = await withLoading(() => wordDiff(fileA.value!, fileB.value!))
  if (data) result.value = data
}
</script>
