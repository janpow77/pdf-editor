<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">KI-Assistent</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Zusammenfassen oder Fragen zum Dokument stellen. Läuft ausschließlich auf
      <strong>eigener Infrastruktur</strong> (lokales Sprachmodell) — keine Cloud,
      Inhalte werden nur transient verarbeitet und nicht gespeichert.
      KI-Antworten können Fehler enthalten und sind kein Ersatz für die eigene Prüfung.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div class="flex gap-2">
        <button
          v-for="m in modes"
          :key="m.value"
          class="px-3 py-1.5 rounded-lg text-sm border-2 transition-colors"
          :class="mode === m.value
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
            : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300'"
          @click="mode = m.value"
        >
          {{ m.label }}
        </button>
      </div>
      <div v-if="mode === 'ask'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Frage zum Dokument</label>
        <textarea
          v-model="question"
          rows="2"
          maxlength="2000"
          placeholder="z.B. Welche Fristen werden genannt?"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
        ></textarea>
      </div>
    </div>

    <div v-if="answer" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-gray-900 dark:text-white">Antwort</span>
        <button class="text-xs text-gray-400 hover:text-primary-600" @click="copyAnswer">{{ copied ? 'Kopiert ✓' : 'Kopieren' }}</button>
      </div>
      <p class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{{ answer }}</p>
      <p class="text-xs text-gray-400">KI-generiert ({{ model }}) — bitte fachlich prüfen.</p>
    </div>

    <button
      v-if="file"
      :disabled="loading || (mode === 'ask' && question.trim().length < 3)"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'KI arbeitet…' : mode === 'summary' ? 'Zusammenfassen' : 'Frage stellen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { apiPost } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

const file = ref<File | null>(null)
const mode = ref<'summary' | 'ask'>('summary')
const question = ref('')
const answer = ref('')
const model = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const copied = ref(false)

const modes = [
  { value: 'summary' as const, label: 'Zusammenfassen' },
  { value: 'ask' as const, label: 'Frage stellen' },
]

async function apply() {
  if (!file.value) return
  loading.value = true
  error.value = null
  answer.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    let url = '/api/pdf-more/ai/summarize'
    if (mode.value === 'ask') {
      url = '/api/pdf-more/ai/ask'
      fd.append('question', question.value.trim())
    }
    const resp = await apiPost(url, fd)
    const body = (await resp.json()) as { answer: string; model: string }
    answer.value = body.answer
    model.value = body.model
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}

async function copyAnswer() {
  await navigator.clipboard.writeText(answer.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 1500)
}
</script>
