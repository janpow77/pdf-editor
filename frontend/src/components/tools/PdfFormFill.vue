<template>
  <div class="space-y-5">
    <ToolHeader title="Formular ausfüllen" description="Vorhandene AcroForm-Felder bearbeiten oder aus einer CSV-Tabelle serienweise befüllen." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <div v-if="loadingFields" class="flex items-center justify-center gap-3 py-6" role="status">
      <span class="h-6 w-6 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="text-sm text-gray-600 dark:text-gray-300">Formularfelder werden gelesen…</span>
    </div>

    <UiAlert v-if="file && !fields.length && fieldsLoaded" tone="warning">Dieses PDF enthält keine ausfüllbaren AcroForm-Felder.</UiAlert>

    <UiPanel v-if="fields.length" class="space-y-4">
      <div v-for="(field, index) in fields" :key="field.id" class="grid items-center gap-2 sm:grid-cols-3">
        <label :for="fieldControlId(index)" class="text-sm font-semibold text-gray-700 dark:text-gray-200">
          {{ field.name }} <span class="text-xs font-normal text-gray-600 dark:text-gray-400">(S. {{ field.page }})</span>
        </label>
        <div class="sm:col-span-2">
          <input
            v-if="field.type === 'CheckBox'"
            :id="fieldControlId(index)"
            v-model="values[field.name]"
            type="checkbox"
            class="h-5 w-5 rounded accent-primary-600"
          />
          <select
            v-else-if="field.options.length"
            :id="fieldControlId(index)"
            v-model="values[field.name]"
            class="ui-control w-full"
          >
            <option v-for="option in field.options" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
          <input v-else :id="fieldControlId(index)" v-model="values[field.name]" type="text" class="ui-control w-full" />
        </div>
      </div>
      <label class="ui-choice"><input v-model="flatten" type="checkbox" class="rounded" /> Felder nach dem Ausfüllen einbrennen</label>
    </UiPanel>

    <UiPanel v-if="fields.length" class="space-y-4">
      <div>
        <h3 class="font-semibold text-gray-950 dark:text-white">Serienbefüllung per CSV</h3>
        <p class="mt-1 text-sm leading-6 text-gray-600 dark:text-gray-300">
          Eine CSV-Zeile erzeugt ein PDF; die optionale Spalte <code>dateiname</code> legt den Ausgabename fest.
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <UiButton size="sm" :loading="csvBusy" @click="exportCsv(false)">Werte als CSV</UiButton>
        <UiButton size="sm" :loading="csvBusy" @click="exportCsv(true)">Leere CSV-Vorlage</UiButton>
        <UiButton size="sm" :disabled="csvBusy" @click="csvInput?.click()">Aus CSV befüllen…</UiButton>
        <input ref="csvInput" type="file" accept=".csv,.txt,text/csv,text/plain" class="hidden" @change="fillFromCsv" />
      </div>
      <UiAlert v-if="csvSummary" tone="success" live>{{ csvSummary }}</UiAlert>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Formular ausgefüllt und Datei heruntergeladen.</UiAlert>
    <UiButton v-if="fields.length" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Fülle aus…' : 'Ausfüllen und herunterladen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiPost, downloadBlob } from '@/lib/api'
import { currentFileLimit, formatFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

interface FieldOption { value: string; label: string }
interface FormField {
  id: string
  name: string
  type: string
  value: string
  options: FieldOption[]
  page: number
}

const file = ref<File | null>(null)
const fields = ref<FormField[]>([])
const values = ref<Record<string, string | boolean>>({})
const flatten = ref(false)
const loadingFields = ref(false)
const fieldsLoaded = ref(false)
const loading = ref(false)
const done = ref(false)
const error = ref<string | null>(null)
const csvInput = ref<HTMLInputElement | null>(null)
const csvBusy = ref(false)
const csvSummary = ref('')
let documentGeneration = 0
let fieldController: AbortController | null = null

function fieldControlId(index: number): string {
  return `form-field-${index}`
}

function normalizeOptions(value: unknown): FieldOption[] {
  if (!Array.isArray(value)) return []
  return value.map((option) => {
    if (Array.isArray(option)) {
      return { value: String(option[0] ?? ''), label: String(option[1] ?? option[0] ?? '') }
    }
    return { value: String(option ?? ''), label: String(option ?? '') }
  })
}

function normalizeFields(value: unknown): FormField[] {
  const source = value && typeof value === 'object' && 'fields' in value
    ? (value as { fields?: unknown }).fields
    : []
  if (!Array.isArray(source)) return []
  return source.slice(0, 500).flatMap((entry, index) => {
    if (!entry || typeof entry !== 'object') return []
    const raw = entry as Record<string, unknown>
    const name = String(raw.name ?? '').trim()
    if (!name) return []
    return [{
      id: `${index}-${name}-${Number(raw.page) || 1}`,
      name,
      type: String(raw.type ?? 'Text'),
      value: String(raw.value ?? ''),
      options: normalizeOptions(raw.options),
      page: Math.max(1, Math.trunc(Number(raw.page) || 1)),
    }]
  })
}

watch(file, async (currentFile) => {
  const generation = ++documentGeneration
  fieldController?.abort()
  fieldController = null
  fields.value = []
  values.value = {}
  fieldsLoaded.value = false
  loadingFields.value = false
  done.value = false
  error.value = null
  csvSummary.value = ''
  csvBusy.value = false
  if (!currentFile) return

  const controller = new AbortController()
  fieldController = controller
  loadingFields.value = true
  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    const response = await apiPost('/api/pdf-extras/form/fields', formData, {
      signal: controller.signal,
      notifyOnError: false,
    })
    const normalized = normalizeFields(await response.json())
    if (generation !== documentGeneration || file.value !== currentFile) return
    fields.value = normalized
    values.value = Object.fromEntries(normalized.map((field) => [
      field.name,
      field.type === 'CheckBox' ? field.value === 'Yes' : field.value,
    ]))
  } catch (caught: unknown) {
    if (controller.signal.aborted || generation !== documentGeneration) return
    error.value = caught instanceof Error ? caught.message : 'Formularfelder konnten nicht gelesen werden.'
  } finally {
    if (generation === documentGeneration) {
      loadingFields.value = false
      fieldsLoaded.value = true
      if (fieldController === controller) fieldController = null
    }
  }
})

async function apply(): Promise<void> {
  const currentFile = file.value
  if (!currentFile || loading.value) return
  const generation = documentGeneration
  loading.value = true
  error.value = null
  done.value = false
  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    formData.append('values', JSON.stringify(values.value))
    formData.append('flatten', String(flatten.value))
    const response = await apiPost('/api/pdf-extras/form/fill', formData)
    await downloadBlob(response, currentFile.name.replace(/\.pdf$/i, '_ausgefuellt.pdf'))
    if (generation === documentGeneration && file.value === currentFile) done.value = true
  } catch (caught: unknown) {
    if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Ausfüllen fehlgeschlagen.'
  } finally {
    if (generation === documentGeneration) loading.value = false
  }
}

async function exportCsv(template: boolean): Promise<void> {
  const currentFile = file.value
  if (!currentFile || csvBusy.value) return
  const generation = documentGeneration
  csvBusy.value = true
  error.value = null
  csvSummary.value = ''
  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    formData.append('template', String(template))
    const response = await apiPost('/api/pdf-extras/form/export-csv', formData)
    const suffix = template ? '_vorlage.csv' : '_formulardaten.csv'
    await downloadBlob(response, currentFile.name.replace(/\.pdf$/i, suffix))
    if (generation !== documentGeneration) return
    csvSummary.value = template
      ? 'CSV-Vorlage heruntergeladen – Zeilen ergänzen und wieder einlesen.'
      : `${response.headers.get('X-Fields') || '0'} Feldwerte als CSV heruntergeladen.`
  } catch (caught: unknown) {
    if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'CSV-Export fehlgeschlagen.'
  } finally {
    if (generation === documentGeneration) csvBusy.value = false
  }
}

async function fillFromCsv(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const csv = input.files?.[0]
  input.value = ''
  const currentFile = file.value
  if (!csv || !currentFile || csvBusy.value) return
  if (!/\.(csv|txt)$/i.test(csv.name)) {
    error.value = 'Bitte wählen Sie eine CSV- oder TXT-Datei.'
    return
  }
  if (csv.size > currentFileLimit()) {
    error.value = `Die CSV-Datei ist ${formatFileSize(csv.size)} groß. Zulässig sind maximal ${formatFileSize(currentFileLimit())}.`
    return
  }

  const generation = documentGeneration
  csvBusy.value = true
  error.value = null
  csvSummary.value = ''
  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    formData.append('data', csv)
    formData.append('flatten', String(flatten.value))
    const response = await apiPost('/api/pdf-extras/form/fill-csv', formData)
    const rows = Number(response.headers.get('X-Rows') || '0')
    await downloadBlob(response, rows > 1 ? 'formulare.zip' : 'formular.pdf')
    if (generation !== documentGeneration) return
    const warnings = Number(response.headers.get('X-Warnings') || '0')
    csvSummary.value = `${rows} Formular(e) befüllt und heruntergeladen${warnings ? ` – ${warnings} Hinweis(e), siehe hinweise.txt im ZIP.` : '.'}`
  } catch (caught: unknown) {
    if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Serienbefüllung fehlgeschlagen.'
  } finally {
    if (generation === documentGeneration) csvBusy.value = false
  }
}
</script>
