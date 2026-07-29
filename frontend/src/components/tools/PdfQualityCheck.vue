<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Qualitätsprüfung</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Prüft das PDF auf leere Seiten, gescannte Seiten ohne Textebene (OCR fehlt?) und
      doppelte Seiten — z.B. nach dem Scannen von Akten.
    </div>

    <FileDrop v-model="file" />

    <div v-if="report" class="space-y-3">
      <div
        class="p-3 rounded-lg text-sm border"
        :class="report.ok
          ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700 text-green-700 dark:text-green-300'
          : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-700 text-yellow-800 dark:text-yellow-300'"
      >
        {{ report.ok ? `Keine Auffälligkeiten (${report.pages} Seiten geprüft).` : `Auffälligkeiten gefunden (${report.pages} Seiten geprüft):` }}
      </div>
      <ul v-if="!report.ok" class="text-sm text-gray-700 dark:text-gray-300 space-y-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <li v-if="report.empty_pages.length">
          <strong>Leere Seiten:</strong> {{ report.empty_pages.join(', ') }}
        </li>
        <li v-if="report.scan_pages_without_text.length">
          <strong>Scans ohne Textebene:</strong> Seiten {{ report.scan_pages_without_text.join(', ') }}
          <span class="text-gray-400">— Tipp: Werkzeug „Scan optimieren" oder „OCR"</span>
        </li>
        <li v-if="report.duplicate_page_pairs.length">
          <strong>Mögliche Duplikate:</strong>
          {{ report.duplicate_page_pairs.map((p) => `Seite ${p[0]} = Seite ${p[1]}`).join('; ') }}
        </li>
      </ul>
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Prüfe…' : 'Prüfen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { apiPost } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface Report {
  pages: number
  empty_pages: number[]
  scan_pages_without_text: number[]
  duplicate_page_pairs: [number, number][]
  ok: boolean
}

const file = ref<File | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const report = ref<Report | null>(null)

async function apply() {
  if (!file.value) return
  loading.value = true
  error.value = null
  report.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    const resp = await apiPost('/api/pdf-more/quality-check', fd)
    report.value = (await resp.json()) as Report
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}
</script>
