<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Schwärzen</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Echte Schwärzung: Der gefundene Text wird aus dem Dokumentinhalt <strong>entfernt</strong>
      (nicht nur überdeckt) und schwarz markiert — auch Kopieren/Durchsuchen findet ihn danach nicht mehr.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zu schwärzender Text</label>
        <input v-model="term" type="text" placeholder="z.B. Name, IBAN, Aktenzeichen" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="matchCase" type="checkbox" class="rounded" />
        Groß-/Kleinschreibung beachten
      </label>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      {{ redactions }} Stelle(n) geschwärzt, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading || !term.trim()"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Schwärze…' : 'Schwärzen' }}
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
const term = ref('')
const matchCase = ref(false)
const redactions = ref(0)

async function apply() {
  if (!file.value || !term.value.trim()) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('term', term.value)
  fd.append('match_case', String(matchCase.value))
  const resp = await run('/api/pdf-extras/redact', fd, file.value.name.replace(/\.pdf$/i, '_geschwaerzt.pdf'))
  if (resp) redactions.value = Number(resp.headers.get('X-Redactions') || 0)
}
</script>
