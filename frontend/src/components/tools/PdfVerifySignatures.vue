<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Signatur prüfen</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Prüft digitale Signaturen im PDF: Integrität (wurde das Dokument nach der Signatur
      verändert?), Signierzeitpunkt und Unterzeichner. Die Vertrauenskette kann ohne
      hinterlegte Vertrauensanker nicht abschließend bewertet werden.
    </div>

    <FileDrop v-model="file" />

    <div v-if="report" class="space-y-3">
      <div v-if="report.count === 0" class="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg text-sm text-yellow-800 dark:text-yellow-300">
        Dieses PDF enthält keine digitalen Signaturen.
      </div>
      <div
        v-for="(sig, i) in report.signatures"
        :key="i"
        class="bg-white dark:bg-gray-900 rounded-xl border p-4 space-y-2"
        :class="sig.intact ? 'border-green-300 dark:border-green-700' : 'border-red-300 dark:border-red-700'"
      >
        <div class="flex items-center justify-between">
          <span class="font-medium text-gray-900 dark:text-white">{{ sig.field }}</span>
          <span
            class="text-xs px-2 py-0.5 rounded-full"
            :class="sig.intact
              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
              : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'"
          >
            {{ sig.error ? 'Prüfung fehlgeschlagen' : sig.intact ? 'Unverändert' : 'Verändert!' }}
          </span>
        </div>
        <template v-if="!sig.error">
          <dl class="text-sm text-gray-600 dark:text-gray-300 grid grid-cols-[auto,1fr] gap-x-4 gap-y-1">
            <dt class="text-gray-400">Unterzeichner</dt><dd>{{ sig.signer }}</dd>
            <dt class="text-gray-400">Signiert am</dt><dd>{{ sig.signing_time || 'unbekannt' }}</dd>
            <dt class="text-gray-400">CMS gültig</dt><dd>{{ sig.valid_cms ? 'ja' : 'nein' }}</dd>
            <dt class="text-gray-400">Abdeckung</dt><dd>{{ sig.coverage }}</dd>
          </dl>
          <p class="text-xs text-gray-400">{{ sig.hinweis }}</p>
        </template>
        <p v-else class="text-sm text-red-600">{{ sig.error }}</p>
      </div>
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Prüfe…' : 'Signaturen prüfen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { apiPost } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface SignatureEntry {
  field: string
  signer?: string
  intact?: boolean
  valid_cms?: boolean
  coverage?: string
  signing_time?: string
  trusted?: boolean
  hinweis?: string
  error?: string
}
interface Report {
  count: number
  signatures: SignatureEntry[]
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
    const resp = await apiPost('/api/pdf-more/verify-signatures', fd)
    report.value = (await resp.json()) as Report
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}
</script>
