<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Office → PDF</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Konvertiert Excel-, PowerPoint-, OpenDocument-, RTF-, HTML- und Textdateien in PDF
      (LibreOffice). Für Word-Dateien gibt es die eigene Kachel „Word → PDF".
    </div>

    <FileDrop
      v-model="file"
      accept=".xlsx,.xls,.pptx,.ppt,.odt,.ods,.odp,.rtf,.txt,.html,.htm"
      label="Office-Datei"
    />

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      In PDF konvertiert, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Konvertiere…' : 'In PDF konvertieren' }}
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

async function apply() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  await run('/api/pdf-more/office-to-pdf', fd, file.value.name.replace(/\.[^.]+$/, '.pdf'))
}
</script>
