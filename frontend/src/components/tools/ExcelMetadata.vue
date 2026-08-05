<template>
  <div class="space-y-5">
    <ToolHeader title="Excel-Metadaten" description="Titel, Ersteller, Datumswerte und weitere Arbeitsmappeneigenschaften bearbeiten." @back="$emit('back')" />

    <FileDrop v-model="file" accept=".xlsx,.xls" label="Excel-Datei" />

    <div v-if="loading" class="flex items-center justify-center gap-3 py-6" role="status">
      <span class="h-7 w-7 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="text-sm text-gray-600 dark:text-gray-300">Metadaten werden gelesen…</span>
    </div>

    <UiPanel v-if="file && meta && !loading" class="space-y-4">
      <UiAlert v-if="meta.sheet_names.length" tone="info">
        <strong>Arbeitsblätter ({{ meta.sheet_count }}):</strong>
        <span class="ml-1">{{ meta.sheet_names.join(', ') }}</span>
      </UiAlert>

      <div class="grid gap-4 md:grid-cols-2">
        <UiField v-for="field in fields" :key="field.key" :label="field.label" :for-id="`excel-meta-${field.key}`">
          <input
            v-if="field.type !== 'datetime-local'"
            :id="`excel-meta-${field.key}`"
            v-model="meta[field.key]"
            type="text"
            class="ui-control w-full"
          />
          <input
            v-else
            :id="`excel-meta-${field.key}`"
            :value="toLocalDatetime(meta[field.key])"
            type="datetime-local"
            class="ui-control w-full"
            @input="meta[field.key] = fromLocalDatetime(($event.target as HTMLInputElement).value)"
          />
        </UiField>
      </div>

      <UiButton variant="primary" :loading="saving" @click="save">
        {{ saving ? 'Speichern…' : 'Metadaten setzen und herunterladen' }}
      </UiButton>
    </UiPanel>

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

defineEmits<{ (event: 'back'): void }>()

interface ExcelMetadataValues {
  title: string
  creator: string
  subject: string
  keywords: string
  category: string
  description: string
  last_modified_by: string
  created: string
  modified: string
  sheet_count: number
  sheet_names: string[]
}

type EditableMetadataKey = Exclude<keyof ExcelMetadataValues, 'sheet_count' | 'sheet_names'>

const { readExcelMetadata, setExcelMetadata } = usePdfTools()
const file = ref<File | null>(null)
const meta = ref<ExcelMetadataValues | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
let readGeneration = 0

const fields: { key: EditableMetadataKey; label: string; type?: 'datetime-local' }[] = [
  { key: 'title', label: 'Titel' },
  { key: 'creator', label: 'Ersteller' },
  { key: 'subject', label: 'Betreff' },
  { key: 'keywords', label: 'Schlüsselwörter' },
  { key: 'category', label: 'Kategorie' },
  { key: 'description', label: 'Beschreibung' },
  { key: 'last_modified_by', label: 'Zuletzt geändert von' },
  { key: 'created', label: 'Erstellt am', type: 'datetime-local' },
  { key: 'modified', label: 'Geändert am', type: 'datetime-local' },
]

function emptyMetadata(): ExcelMetadataValues {
  return {
    title: '',
    creator: '',
    subject: '',
    keywords: '',
    category: '',
    description: '',
    last_modified_by: '',
    created: '',
    modified: '',
    sheet_count: 0,
    sheet_names: [],
  }
}

function normalizeMetadata(value: unknown): ExcelMetadataValues {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const normalized = emptyMetadata()
  for (const key of fields.map((field) => field.key)) {
    normalized[key] = source[key] == null ? '' : String(source[key])
  }
  normalized.sheet_count = Number.isFinite(Number(source.sheet_count)) ? Number(source.sheet_count) : 0
  normalized.sheet_names = Array.isArray(source.sheet_names) ? source.sheet_names.map(String) : []
  return normalized
}

function toLocalDatetime(iso: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 16)
}

function fromLocalDatetime(local: string): string {
  if (!local) return ''
  const date = new Date(local)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString()
}

watch(file, async (currentFile) => {
  const generation = ++readGeneration
  meta.value = null
  error.value = null
  success.value = null
  if (!currentFile) {
    loading.value = false
    return
  }

  loading.value = true
  try {
    const result = await readExcelMetadata(currentFile)
    if (generation !== readGeneration || file.value !== currentFile) return
    meta.value = normalizeMetadata(result)
  } catch (caught: unknown) {
    if (generation !== readGeneration) return
    error.value = caught instanceof Error ? caught.message : 'Fehler beim Lesen'
  } finally {
    if (generation === readGeneration) loading.value = false
  }
})

async function save(): Promise<void> {
  if (!file.value || !meta.value) return
  saving.value = true
  error.value = null
  success.value = null
  try {
    const { sheet_count: _sheetCount, sheet_names: _sheetNames, ...editable } = meta.value
    await setExcelMetadata(file.value, editable)
    success.value = 'Datei mit neuen Metadaten heruntergeladen.'
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}
</script>
