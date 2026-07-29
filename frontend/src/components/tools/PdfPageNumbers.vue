<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Seitenzahlen einfügen</h2>
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Format ({page}, {total}, {date})</label>
        <input v-model="format" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Position</label>
          <select v-model="position" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
            <option value="bottom-center">unten Mitte</option>
            <option value="bottom-right">unten rechts</option>
            <option value="bottom-left">unten links</option>
            <option value="top-center">oben Mitte</option>
            <option value="top-right">oben rechts</option>
            <option value="top-left">oben links</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ab Seite</label>
          <input v-model.number="startPage" type="number" min="1" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Startnummer</label>
          <input v-model.number="startNumber" type="number" min="1" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Schriftgröße</label>
          <input v-model.number="fontSize" type="number" min="6" max="24" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
      </div>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Seitenzahlen wurden eingefügt, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Verarbeite…' : 'Seitenzahlen einfügen' }}
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
const format = ref('Seite {page} von {total}')
const position = ref('bottom-center')
const startPage = ref(1)
const startNumber = ref(1)
const fontSize = ref(10)

async function apply() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('format_str', format.value)
  fd.append('position', position.value)
  fd.append('start_page', String(startPage.value))
  fd.append('start_number', String(startNumber.value))
  fd.append('font_size', String(fontSize.value))
  await run('/api/pdf-editor/page-numbers', fd, file.value.name.replace(/\.pdf$/i, '_nummeriert.pdf'))
}
</script>
