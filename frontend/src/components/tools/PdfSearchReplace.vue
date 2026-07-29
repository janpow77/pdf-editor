<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Text suchen &amp; ersetzen</h2>
    </div>

    <div class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300">
      Der neue Text wird an derselben Stelle ohne Zeilenumbruch-Anpassung gesetzt —
      am besten für kurze Begriffe mit ähnlicher Länge. Für Absätze das Werkzeug
      „Text bearbeiten" nutzen.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div class="grid sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Suchen nach</label>
          <input v-model="search" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ersetzen durch</label>
          <input v-model="replace" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
      </div>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="matchCase" type="checkbox" class="rounded" />
        Groß-/Kleinschreibung beachten
      </label>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      {{ replacements }} Ersetzung(en) durchgeführt, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading || !search"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Ersetze…' : 'Ersetzen' }}
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
const search = ref('')
const replace = ref('')
const matchCase = ref(true)
const replacements = ref(0)

async function apply() {
  if (!file.value || !search.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('search', search.value)
  fd.append('replace', replace.value)
  fd.append('match_case', String(matchCase.value))
  const resp = await run('/api/pdf-editor/text/replace', fd, file.value.name.replace(/\.pdf$/i, '_ersetzt.pdf'))
  if (resp) replacements.value = Number(resp.headers.get('X-Replacements') || 0)
}
</script>
