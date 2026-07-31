<template>
  <div
    v-if="results.length > 0"
    class="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl space-y-3"
  >
    <div class="flex items-center justify-between flex-wrap gap-2">
      <h3 class="text-sm font-semibold text-gray-900 dark:text-white">
        Ergebnisse dieser Sitzung ({{ results.length }}, {{ formatSize(totalSize) }})
      </h3>
      <div class="flex gap-2">
        <button
          class="px-3 py-1.5 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="zipping"
          @click="zipAll"
        >
          {{ zipping ? 'Packe…' : 'Alle als ZIP' }}
        </button>
        <button
          v-if="mailAvailable"
          class="px-3 py-1.5 text-sm rounded-lg border border-primary-600 text-primary-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20"
          @click="showMailDialog = true"
        >
          Per E-Mail senden
        </button>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300
                 hover:bg-gray-50 dark:hover:bg-gray-700"
          @click="clearResults"
        >
          Leeren
        </button>
      </div>
    </div>

    <ul class="divide-y divide-gray-100 dark:divide-gray-700">
      <li v-for="r in results" :key="r.id" class="py-2 flex items-center justify-between gap-2 text-sm">
        <span class="truncate text-gray-700 dark:text-gray-300">{{ r.name }}</span>
        <span class="flex items-center gap-3 shrink-0">
          <span class="text-xs text-gray-600 dark:text-gray-400">{{ formatSize(r.blob.size) }}</span>
          <button
            class="text-gray-600 dark:text-gray-400 hover:text-red-500"
            :aria-label="`${r.name} entfernen`"
            @click="removeResult(r.id)"
          >
            ✕
          </button>
        </span>
      </li>
    </ul>

    <p class="text-xs text-gray-600 dark:text-gray-400">
      Die Liste existiert nur in Ihrem Browser und wird beim Neuladen der Seite geleert.
    </p>

    <EmailSendDialog v-if="showMailDialog" :items="results" @close="showMailDialog = false" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmailSendDialog from '@/components/EmailSendDialog.vue'
import { apiGetJson } from '@/lib/api'
import { clearResults, formatSize, removeResult, results, totalSize } from '@/lib/results'
import { downloadResultsAsZip } from '@/lib/zip'

const zipping = ref(false)
const showMailDialog = ref(false)
const mailAvailable = ref(false)

onMounted(async () => {
  try {
    const status = await apiGetJson<{ available: boolean }>('/api/mail/status')
    mailAvailable.value = status.available
  } catch {
    mailAvailable.value = false
  }
})

async function zipAll() {
  zipping.value = true
  try {
    await downloadResultsAsZip(results.value)
  } finally {
    zipping.value = false
  }
}
</script>
