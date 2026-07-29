<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF exportieren</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Exportiert den Inhalt als Markdown (mit Überschriften-Erkennung), HTML,
      strukturiertes JSON oder Tabellen als CSV.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zielformat</label>
        <select v-model="format" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="markdown">Markdown (.md)</option>
          <option value="html">HTML (.html)</option>
          <option value="json">JSON (Textblöcke + Positionen)</option>
          <option value="csv">CSV (erkannte Tabellen)</option>
        </select>
      </div>
      <div v-if="format === 'csv'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Seitenbereich (leer = alle)</label>
        <input
          v-model="pages"
          type="text"
          placeholder="z.B. 1-3,5"
          class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Export heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Exportiere…' : 'Exportieren' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const format = ref('markdown')
const pages = ref('')

const EXT: Record<string, string> = { markdown: '.md', html: '.html', json: '.json', csv: '.csv' }

async function apply() {
  if (!file.value) return
  const base = file.value.name.replace(/\.pdf$/i, '')
  const fd = new FormData()
  fd.append('file', file.value)
  if (format.value === 'csv') {
    fd.append('pages', pages.value)
    await run('/api/pdf-more/to-csv', fd, `${base}.csv`)
  } else {
    await run(`/api/pdf-more/export/${format.value}`, fd, `${base}${EXT[format.value]}`)
  }
}
</script>
