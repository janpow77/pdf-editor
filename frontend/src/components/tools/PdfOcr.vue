<template>
  <div class="space-y-5">
    <ToolHeader title="OCR – Texterkennung" description="Gescannte PDFs durch eine unsichtbare Textebene durchsuchbar machen." @back="$emit('back')" />
    <UiAlert tone="info">Die Texterkennung kann bei großen Dokumenten mehrere Minuten dauern.</UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file && !result">
      <fieldset>
        <legend class="mb-3 font-semibold">Sprache der Texterkennung</legend>
        <div class="flex flex-wrap gap-3">
          <label v-for="languageOption in languages" :key="languageOption.value" class="ui-choice rounded-full bg-gray-100 px-3 py-2 dark:bg-white/10">
            <input v-model="language" type="radio" :value="languageOption.value" /> {{ languageOption.label }}
          </label>
        </div>
      </fieldset>
    </UiPanel>

    <div v-if="loading" class="space-y-3 py-8 text-center" role="status">
      <span class="mx-auto block h-10 w-10 animate-spin rounded-full border-4 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <p class="font-semibold">OCR wird durchgeführt…</p>
      <p class="text-sm text-gray-600 dark:text-gray-300">Bitte das Werkzeug währenddessen geöffnet lassen.</p>
    </div>

    <UiPanel v-if="result" tone="success" class="space-y-4">
      <UiAlert tone="success" live>{{ result.pagesProcessed }} Seiten verarbeitet, {{ result.charsRecognized.toLocaleString('de-DE') }} Zeichen erkannt.</UiAlert>
      <div class="grid grid-cols-2 gap-4 text-center">
        <div><p class="text-xs opacity-70">Seiten</p><p class="text-2xl font-bold">{{ result.pagesProcessed }}</p></div>
        <div><p class="text-xs opacity-70">Zeichen</p><p class="text-2xl font-bold">{{ result.charsRecognized.toLocaleString('de-DE') }}</p></div>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton variant="primary" @click="downloadResult">Durchsuchbare PDF herunterladen</UiButton>
        <UiButton @click="reset">Neues Dokument</UiButton>
      </div>
    </UiPanel>

    <UiButton v-if="file && !result" variant="primary" size="lg" block :loading="loading" @click="runOcr">{{ loading ? 'OCR läuft…' : 'OCR starten' }}</UiButton>
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
import { runJob } from '@/lib/jobs'

defineEmits<{ (event: 'back'): void }>()

interface OcrResult { pagesProcessed: number; charsRecognized: number; blobUrl: string; filename: string }
const OCR_TIMEOUT = 10 * 60 * 1000
const languages = [
  { value: 'deu', label: 'Deutsch' }, { value: 'eng', label: 'Englisch' }, { value: 'deu+eng', label: 'Deutsch + Englisch' },
  { value: 'fra', label: 'Französisch' }, { value: 'ita', label: 'Italienisch' }, { value: 'spa', label: 'Spanisch' },
  { value: 'nld', label: 'Niederländisch' }, { value: 'pol', label: 'Polnisch' },
]

const notifications = useNotifications()
const file = ref<File | null>(null)
const language = ref(prefDefault('ocr_language', 'deu'))
const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<OcrResult | null>(null)
let generation = 0
let controller: AbortController | null = null

function safeFilename(value: string): string {
  return value.replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_').trim() || 'dokument_ocr.pdf'
}

function releaseResult(): void {
  if (result.value?.blobUrl) URL.revokeObjectURL(result.value.blobUrl)
  result.value = null
}

watch([file, language], () => {
  generation += 1
  controller?.abort(); controller = null
  releaseResult(); error.value = null; loading.value = false
})

async function runOcr(): Promise<void> {
  const currentFile = file.value
  if (!currentFile || loading.value) return
  const currentGeneration = ++generation
  const requestController = new AbortController(); controller?.abort(); controller = requestController
  releaseResult(); loading.value = true; error.value = null

  try {
    const formData = new FormData(); formData.append('file', currentFile); formData.append('language', language.value)
    const response = await runJob('/api/pdf-extras/jobs/ocr', formData, undefined, OCR_TIMEOUT, requestController.signal)
    if (currentGeneration !== generation || file.value !== currentFile) return
    const pagesProcessed = Math.max(0, Number(response.headers.get('X-Pages-Processed') || 0))
    const charsRecognized = Math.max(0, Number(response.headers.get('X-Characters-Recognized') || 0))
    const disposition = response.headers.get('Content-Disposition')
    const headerName = disposition?.match(/filename="?([^";\n]+)"?/i)?.[1]
    const filename = safeFilename(headerName || currentFile.name.replace(/\.pdf$/i, '') + '_ocr.pdf')
    const blobUrl = URL.createObjectURL(await response.blob())
    if (currentGeneration !== generation) { URL.revokeObjectURL(blobUrl); return }
    result.value = { pagesProcessed, charsRecognized, blobUrl, filename }
    notifications.success('OCR abgeschlossen', `${pagesProcessed} Seiten wurden verarbeitet.`)
  } catch (caught: unknown) {
    if (requestController.signal.aborted || currentGeneration !== generation) return
    error.value = caught instanceof Error ? caught.message : 'OCR-Verarbeitung fehlgeschlagen.'
  } finally {
    if (controller === requestController) controller = null
    if (currentGeneration === generation) loading.value = false
  }
}

function downloadResult(): void {
  const current = result.value
  if (!current) return
  const anchor = document.createElement('a')
  try { anchor.href = current.blobUrl; anchor.download = current.filename; document.body.appendChild(anchor); anchor.click() }
  finally { anchor.remove() }
}

function reset(): void {
  generation += 1; controller?.abort(); controller = null
  releaseResult(); file.value = null; error.value = null; loading.value = false
}

onBeforeUnmount(() => { generation += 1; controller?.abort(); releaseResult() })
</script>
