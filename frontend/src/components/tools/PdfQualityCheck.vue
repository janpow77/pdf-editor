<template>
  <div class="space-y-5">
    <ToolHeader title="Qualitätsprüfung" description="Leere Seiten, fehlende Textebenen und mögliche Duplikate erkennen." @back="$emit('back')" />

    <UiAlert tone="info">Geeignet zur Kontrolle gescannter Akten vor OCR, Archivierung oder Weitergabe.</UiAlert>

    <FileDrop v-model="file" />

    <div v-if="report" class="space-y-3">
      <UiAlert :tone="report.ok ? 'success' : 'warning'" live>
        {{ report.ok ? `Keine Auffälligkeiten (${report.pages} Seiten geprüft).` : `Auffälligkeiten gefunden (${report.pages} Seiten geprüft).` }}
      </UiAlert>
      <UiPanel v-if="!report.ok" as="ul" class="space-y-2 text-sm">
        <li v-if="report.empty_pages.length"><strong>Leere Seiten:</strong> {{ report.empty_pages.join(', ') }}</li>
        <li v-if="report.scan_pages_without_text.length">
          <strong>Scans ohne Textebene:</strong> Seiten {{ report.scan_pages_without_text.join(', ') }}
          <span class="opacity-70"> – Tipp: „Scan optimieren“ oder „OCR“</span>
        </li>
        <li v-if="report.duplicate_page_pairs.length">
          <strong>Mögliche Duplikate:</strong>
          {{ report.duplicate_page_pairs.map((pair) => `Seite ${pair[0]} = Seite ${pair[1]}`).join('; ') }}
        </li>
      </UiPanel>
    </div>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Prüfe…' : 'Prüfen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiPost } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

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

async function apply(): Promise<void> {
  if (!file.value) return
  loading.value = true
  error.value = null
  report.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    const response = await apiPost('/api/pdf-more/quality-check', fd)
    report.value = (await response.json()) as Report
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}
</script>
