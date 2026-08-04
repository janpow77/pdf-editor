<template>
  <UiPanel v-if="results.length" as="section" class="space-y-4" aria-labelledby="session-results-heading">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="session-results-heading" class="text-sm font-semibold text-gray-950 dark:text-white">
        Ergebnisse dieser Sitzung ({{ results.length }}, {{ formatSize(totalSize) }})
      </h2>
      <div class="flex flex-wrap gap-2">
        <UiButton variant="primary" size="sm" :loading="zipping" @click="zipAll">{{ zipping ? 'Packe…' : 'Alle als ZIP' }}</UiButton>
        <UiButton v-if="mailAvailable" size="sm" @click="showMailDialog = true">Per E-Mail senden</UiButton>
        <UiButton variant="danger" size="sm" @click="clearAll">Leeren</UiButton>
      </div>
    </div>

    <ul class="divide-y divide-gray-200/80 dark:divide-gray-700">
      <li v-for="result in results" :key="result.id" class="flex items-center justify-between gap-2 py-2 text-sm">
        <span class="truncate text-gray-700 dark:text-gray-300">{{ result.name }}</span>
        <span class="flex shrink-0 items-center gap-2">
          <span class="text-xs text-gray-600 dark:text-gray-400">{{ formatSize(result.blob.size) }}</span>
          <UiIconButton size="sm" variant="danger" :aria-label="`${result.name} entfernen`" @click="removeResult(result.id)">×</UiIconButton>
        </span>
      </li>
    </ul>

    <p class="text-xs leading-5 text-gray-600 dark:text-gray-400">
      Die Liste existiert nur im Browser-RAM, ist größenbegrenzt und wird beim Neuladen geleert.
    </p>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>

    <EmailSendDialog
      v-if="showMailDialog"
      :items="results"
      :max-attachment-bytes="maxAttachmentBytes"
      @close="showMailDialog = false"
    />
  </UiPanel>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import EmailSendDialog from '@/components/EmailSendDialog.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiGetJson } from '@/lib/api'
import { clearResults, formatSize, removeResult, results, totalSize } from '@/lib/results'
import { downloadResultsAsZip } from '@/lib/zip'

const zipping = ref(false)
const showMailDialog = ref(false)
const mailAvailable = ref(false)
const maxAttachmentBytes = ref(20 * 1024 * 1024)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const status = await apiGetJson<{ available: boolean; max_attachment_bytes?: number }>('/api/mail/status')
    mailAvailable.value = Boolean(status.available)
    if (Number.isFinite(status.max_attachment_bytes) && Number(status.max_attachment_bytes) > 0) {
      maxAttachmentBytes.value = Number(status.max_attachment_bytes)
    }
  } catch {
    mailAvailable.value = false
  }
})

async function zipAll(): Promise<void> {
  zipping.value = true
  error.value = null
  try {
    await downloadResultsAsZip(results.value)
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Die ZIP-Datei konnte nicht erzeugt werden.'
  } finally {
    zipping.value = false
  }
}

function clearAll(): void {
  showMailDialog.value = false
  error.value = null
  clearResults()
}
</script>
