<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Scan optimieren</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Bereitet gescannte PDFs auf: Seiten geraderücken und automatisch drehen,
      durchsuchbare OCR-Textebene einfügen (OCRmyPDF).
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sprache</label>
        <select v-model="language" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="deu">Deutsch</option>
          <option value="eng">Englisch</option>
          <option value="deu+eng">Deutsch + Englisch</option>
        </select>
      </div>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="deskew" type="checkbox" class="rounded" /> Seiten geraderücken
      </label>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="rotate" type="checkbox" class="rounded" /> Seiten automatisch drehen
      </label>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="forceOcr" type="checkbox" class="rounded" /> OCR erzwingen (auch bei vorhandenem Text)
      </label>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Scan optimiert, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Optimiere… (kann dauern)' : 'Optimieren' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'
import { prefDefault } from '@/lib/auth'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const language = ref(prefDefault('ocr_language', 'deu'))
const deskew = ref(true)
const rotate = ref(true)
const forceOcr = ref(false)

async function apply() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('language', language.value)
  fd.append('deskew', String(deskew.value))
  fd.append('rotate_pages', String(rotate.value))
  fd.append('force_ocr', String(forceOcr.value))
  await run('/api/pdf-extras/scan-optimize', fd, file.value.name.replace(/\.pdf$/i, '_optimiert.pdf'))
}
</script>
