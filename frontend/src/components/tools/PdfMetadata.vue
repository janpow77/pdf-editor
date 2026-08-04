<template>
  <div class="space-y-5">
    <ToolHeader title="PDF-Metadaten" description="Titel, Autor, Datumswerte und technische Dokumenteigenschaften bearbeiten." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <div v-if="loadingRead" class="flex items-center justify-center gap-3 py-6" role="status">
      <span class="h-7 w-7 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="text-sm text-gray-600 dark:text-gray-300">Metadaten werden gelesen…</span>
    </div>

    <template v-if="meta && form && !loadingRead">
      <UiPanel>
        <h3 class="mb-2 font-semibold">Datei-Informationen</h3>
        <dl class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-1 text-sm">
          <dt class="opacity-70">Seiten</dt><dd>{{ meta.page_count }}</dd>
          <dt class="opacity-70">Größe</dt><dd>{{ formatFileSize(meta.file_size) }}</dd>
        </dl>
      </UiPanel>

      <UiPanel class="space-y-4">
        <h3 class="font-semibold">Metadaten bearbeiten</h3>
        <div class="grid gap-4 md:grid-cols-2">
          <UiField v-for="field in fields" :key="field.key" :label="field.label" :for-id="`pdf-meta-${field.key}`">
            <input
              v-if="field.type !== 'datetime-local'"
              :id="`pdf-meta-${field.key}`"
              v-model="form[field.key]"
              type="text"
              class="ui-control w-full"
              :placeholder="field.placeholder"
            />
            <input
              v-else
              :id="`pdf-meta-${field.key}`"
              :value="toLocalDatetime(form[field.key])"
              type="datetime-local"
              step="1"
              class="ui-control w-full"
              @input="form[field.key] = fromLocalDatetime(($event.target as HTMLInputElement).value)"
            />
          </UiField>
        </div>
      </UiPanel>

      <UiButton variant="primary" size="lg" :loading="saving" @click="doSave">
        {{ saving ? 'Speichere…' : 'Metadaten setzen und herunterladen' }}
      </UiButton>
    </template>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
    <UiAlert v-if="success" tone="success" live>{{ success }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { usePdfTools } from '@/composables/usePdfTools'
import { formatFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

interface PdfMetadataResponse {
  title?: string
  author?: string
  subject?: string
  keywords?: string
  creator?: string
  producer?: string
  creation_date?: string
  modification_date?: string
  page_count: number
  file_size: number
}

interface PdfMetadataForm {
  title: string
  author: string
  subject: string
  keywords: string
  creator: string
  producer: string
  creation_date: string
  modification_date: string
}

type MetadataKey = keyof PdfMetadataForm

const { readMetadata, setMetadata } = usePdfTools()
const file = ref<File | null>(null)
const meta = ref<PdfMetadataResponse | null>(null)
const form = ref<PdfMetadataForm | null>(null)
const loadingRead = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
let readGeneration = 0

const fields: { key: MetadataKey; label: string; placeholder?: string; type?: 'datetime-local' }[] = [
  { key: 'title', label: 'Titel', placeholder: 'Dokumenttitel' },
  { key: 'author', label: 'Autor', placeholder: 'Verfasser' },
  { key: 'subject', label: 'Betreff', placeholder: 'Betreff oder Thema' },
  { key: 'keywords', label: 'Schlagwörter', placeholder: 'Kommagetrennt' },
  { key: 'creator', label: 'Ersteller-App', placeholder: 'z. B. Microsoft Word' },
  { key: 'producer', label: 'PDF-Erzeuger', placeholder: 'z. B. Adobe PDF Library' },
  { key: 'creation_date', label: 'Erstellt am', type: 'datetime-local' },
  { key: 'modification_date', label: 'Geändert am', type: 'datetime-local' },
]

function parsePdfDate(raw: string | undefined): string {
  if (!raw) return ''
  const match = raw.match(/D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/)
  if (match) return `${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}:${match[6]}`
  const date = new Date(raw)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function toLocalDatetime(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 19)
}

function fromLocalDatetime(local: string): string {
  if (!local) return ''
  const date = new Date(local)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

function normalizeMetadata(value: unknown): { meta: PdfMetadataResponse; form: PdfMetadataForm } {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const normalizedMeta: PdfMetadataResponse = {
    title: String(source.title ?? ''),
    author: String(source.author ?? ''),
    subject: String(source.subject ?? ''),
    keywords: String(source.keywords ?? ''),
    creator: String(source.creator ?? ''),
    producer: String(source.producer ?? ''),
    creation_date: String(source.creation_date ?? ''),
    modification_date: String(source.modification_date ?? ''),
    page_count: Number.isFinite(Number(source.page_count)) ? Number(source.page_count) : 0,
    file_size: Number.isFinite(Number(source.file_size)) ? Number(source.file_size) : 0,
  }
  return {
    meta: normalizedMeta,
    form: {
      title: normalizedMeta.title ?? '',
      author: normalizedMeta.author ?? '',
      subject: normalizedMeta.subject ?? '',
      keywords: normalizedMeta.keywords ?? '',
      creator: normalizedMeta.creator ?? '',
      producer: normalizedMeta.producer ?? '',
      creation_date: parsePdfDate(normalizedMeta.creation_date),
      modification_date: parsePdfDate(normalizedMeta.modification_date),
    },
  }
}

watch(file, async (currentFile) => {
  const generation = ++readGeneration
  meta.value = null
  form.value = null
  error.value = null
  success.value = null
  if (!currentFile) {
    loadingRead.value = false
    return
  }

  loadingRead.value = true
  try {
    const result = await readMetadata(currentFile)
    if (generation !== readGeneration || file.value !== currentFile) return
    const normalized = normalizeMetadata(result)
    meta.value = normalized.meta
    form.value = normalized.form
  } catch (caught: unknown) {
    if (generation !== readGeneration) return
    error.value = caught instanceof Error ? caught.message : 'Fehler beim Lesen der Metadaten.'
  } finally {
    if (generation === readGeneration) loadingRead.value = false
  }
})

async function doSave(): Promise<void> {
  if (!file.value || !form.value) return
  saving.value = true
  error.value = null
  success.value = null
  try {
    await setMetadata(file.value, form.value)
    success.value = 'PDF mit neuen Metadaten heruntergeladen.'
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Fehler beim Speichern.'
  } finally {
    saving.value = false
  }
}
</script>
