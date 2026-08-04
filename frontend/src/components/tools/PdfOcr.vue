<template>
  <div class="space-y-5">
    <ToolHeader title="OCR – Texterkennung" description="Gescannte PDFs mit einer unsichtbaren, durchsuchbaren Textebene versehen." @back="$emit('back')" />

    <UiAlert tone="info">Text kann anschließend gesucht und kopiert werden. Große Dokumente können mehrere Minuten benötigen.</UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file && !result" class="space-y-3">
      <fieldset>
        <legend class="ui-label">Sprache der Texterkennung</legend>
        <div class="flex flex-wrap gap-2">
          <label v-for="languageOption in languages" :key="languageOption.value" class="ui-choice">
            <input v-model="language" type="radio" :value="languageOption.value" class="text-primary-600" />
            {{ languageOption.label }}
          </label>
        </div>
      </fieldset>
    </UiPanel>

    <UiButton v-if="file && !result" variant="primary" size="lg" :loading="loading" block @click="runOcr">
      {{ loading ? 'OCR wird durchgeführt…' : 'OCR starten' }}
    </UiButton>

    <UiPanel v-if="result" tone="success" class="space-y-4">
      <div>
        <p class="font-bold">OCR erfolgreich</p>
        <p class="text-sm opacity-80">{{ result.pagesProcessed }} Seiten verarbeitet, {{ result.charsRecognized.toLocaleString('de-DE') }} Zeichen erkannt.</p>
      </div>
      <div class="grid grid-cols-2 gap-4 text-center">
        <div class="rounded-xl bg-white/70 p-3 dark:bg-black/20"><p class="text-xs opacity-70">Seiten</p><p class="text-lg font-bold">{{ result.pagesProcessed }}</p></div>
        <div class="rounded-xl bg-white/70 p-3 dark:bg-black/20"><p class="text-xs opacity-70">Zeichen</p><p class="text-lg font-bold">{{ result.charsRecognized.toLocaleString('de-DE') }}</p></div>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton variant="primary" @click="downloadResult">Durchsuchbare PDF herunterladen</UiButton>
        <UiButton @click="reset">Neues Dokument</UiButton>
      </div>
    </UiPanel>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { prefDefault } from '@/lib/auth'
import { addResult } from '@/lib/results'
import { runJob } from '@/lib/jobs'

defineEmits<{ (event: 'back'): void }>()

const OCR_TIMEOUT = 10 * 60 * 1000
const defaultLanguage = prefDefault('ocr_language', 'deu')
const languages = [
  { value: 'deu', label: 'Deutsch' },
  { value: 'eng', label: 'Englisch' },
  { value: 'deu+eng', label: 'Deutsch + Englisch' },
  { value: 'fra', label: 'Französisch' },
  { value: 'ita', label: 'Italienisch' },
  { value: 'spa', label: 'Spanisch' },
  { value: 'nld', label: 'Niederländisch' },
  { value: 'pol', label: 'Polnisch' },
]

interface OcrResult {
  pagesProcessed: number
  charsRecognized: number
  blobUrl: string
  filename: string
}

const notifications = useNotifications()
const file = ref<File | null>(null)
const language = ref(defaultLanguage)
const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<OcrResult | null>(null)

function clearResult(): void {
  if (result.value?.blobUrl) URL.revokeObjectURL(result.value.blobUrl)
  result.value = null
}

watch(file, () => {
  clearResult()
  error.value = null
})

function safeFilename(value: string, fallback: string): string {
  const cleaned = value.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').trim()
  return cleaned || fallback
}

async function runOcr(): Promise<void> {
  if (!file.value) return
  const currentFile = file.value
  loading.value = true
  error.value = null
  clearResult()

  try {
    const fd = new FormData()
    fd.append('file', currentFile)
    fd.append('language', language.value)
    const response = await runJob('/api/pdf-extras/jobs/ocr', fd, undefined, OCR_TIMEOUT)

    const pagesProcessed = Number(response.headers.get('X-Pages-Processed') || 0)
    const charsRecognized = Number(response.headers.get('X-Characters-Recognized') || 0)
    const fallbackName = currentFile.name.replace(/\.pdf$/i, '') + '_ocr.pdf'
    const disposition = response.headers.get('Content-Disposition')
    const match = disposition?.match(/filename="?([^";\n]+)"?/)
    const filename = safeFilename(match?.[1] ?? fallbackName, fallbackName)
    const blob = await response.blob()

    if (file.value !== currentFile) return
    const blobUrl = URL.createObjectURL(blob)
    addResult(filename, blob)
    result.value = { pagesProcessed, charsRecognized, blobUrl, filename }
    notifications.success('OCR abgeschlossen', `${filename} ist zum Download bereit.`)
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler bei der OCR-Verarbeitung.'
  } finally {
    loading.value = false
  }
}

function downloadResult(): void {
  const current = result.value
  if (!current) return
  const anchor = document.createElement('a')
  try {
    anchor.href = current.blobUrl
    anchor.download = current.filename
    document.body.appendChild(anchor)
    anchor.click()
  } finally {
    anchor.remove()
  }
}

function reset(): void {
  clearResult()
  file.value = null
  error.value = null
  language.value = defaultLanguage
}

onBeforeUnmount(clearResult)
</script>
