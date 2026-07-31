<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Formular ausfüllen</h2>
    </div>

    <FileDrop v-model="file" />

    <div v-if="loadingFields" class="text-sm text-gray-500">Lese Formularfelder…</div>

    <div v-if="file && fields.length === 0 && fieldsLoaded" class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300">
      Dieses PDF enthält keine ausfüllbaren Formularfelder (AcroForm).
    </div>

    <div v-if="fields.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div v-for="f in fields" :key="f.name" class="grid sm:grid-cols-3 gap-2 items-center">
        <label class="text-sm font-medium text-gray-700 dark:text-gray-300 truncate" :title="f.name">
          {{ f.name }} <span class="text-xs text-gray-600 dark:text-gray-400">(S. {{ f.page }})</span>
        </label>
        <div class="sm:col-span-2">
          <input
            v-if="f.type === 'CheckBox'"
            v-model="values[f.name]"
            type="checkbox"
            class="rounded"
          />
          <select
            v-else-if="f.options.length"
            v-model="values[f.name]"
            class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
          >
            <option v-for="o in f.options" :key="String(o)" :value="Array.isArray(o) ? o[0] : o">
              {{ Array.isArray(o) ? o[1] || o[0] : o }}
            </option>
          </select>
          <input
            v-else
            v-model="values[f.name]"
            type="text"
            class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
          />
        </div>
      </div>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 pt-2 border-t border-gray-100 dark:border-gray-700">
        <input v-model="flatten" type="checkbox" class="rounded" />
        Felder nach dem Ausfüllen einbrennen (nicht mehr änderbar)
      </label>
    </div>

    <!-- Serienbefüllung / CSV -->
    <div v-if="fields.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Daten als CSV (Serienbefüllung)</h3>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Feldwerte als CSV exportieren oder viele Formulare auf einmal aus einer CSV-Tabelle
        befüllen — eine Zeile ergibt ein PDF (Spalte <code>dateiname</code> bestimmt den Namen).
      </p>
      <div class="flex flex-wrap gap-2">
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-300 hover:border-primary-400" :disabled="csvBusy" @click="exportCsv(false)">
          Werte als CSV
        </button>
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-300 hover:border-primary-400" :disabled="csvBusy" @click="exportCsv(true)">
          Leere CSV-Vorlage
        </button>
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-600 dark:text-gray-300 hover:border-primary-400" :disabled="csvBusy" @click="csvInput?.click()">
          Aus CSV befüllen…
        </button>
        <input ref="csvInput" type="file" accept=".csv,.txt" class="hidden" @change="fillFromCsv" />
      </div>
      <p v-if="csvSummary" class="text-sm text-green-700 dark:text-green-300">{{ csvSummary }}</p>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Formular ausgefüllt, Datei heruntergeladen.
    </div>

    <button
      v-if="fields.length"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Fülle aus…' : 'Ausfüllen & herunterladen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface FormField {
  name: string
  type: string
  value: string
  options: unknown[]
  page: number
}

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const fields = ref<FormField[]>([])
const values = ref<Record<string, unknown>>({})
const flatten = ref(false)
const loadingFields = ref(false)
const fieldsLoaded = ref(false)
const csvInput = ref<HTMLInputElement | null>(null)
const csvBusy = ref(false)
const csvSummary = ref('')

watch(file, async (f) => {
  fields.value = []
  values.value = {}
  fieldsLoaded.value = false
  error.value = null
  if (!f) return
  loadingFields.value = true
  try {
    const fd = new FormData()
    fd.append('file', f)
    const resp = await apiPost('/api/pdf-extras/form/fields', fd)
    const data = await resp.json()
    fields.value = data.fields
    for (const field of data.fields) {
      values.value[field.name] = field.type === 'CheckBox' ? field.value === 'Yes' : field.value
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Felder lesen fehlgeschlagen'
  } finally {
    loadingFields.value = false
    fieldsLoaded.value = true
  }
})

async function apply() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('values', JSON.stringify(values.value))
  fd.append('flatten', String(flatten.value))
  await run('/api/pdf-extras/form/fill', fd, file.value.name.replace(/\.pdf$/i, '_ausgefuellt.pdf'))
}

async function exportCsv(template: boolean) {
  if (!file.value) return
  csvBusy.value = true
  error.value = null
  csvSummary.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('template', String(template))
    const resp = await apiPost('/api/pdf-extras/form/export-csv', fd)
    const suffix = template ? '_vorlage.csv' : '_formulardaten.csv'
    await downloadBlob(resp, file.value.name.replace(/\.pdf$/i, suffix))
    csvSummary.value = template
      ? 'CSV-Vorlage heruntergeladen — Zeilen ergänzen und wieder einlesen.'
      : `${resp.headers.get('X-Fields') || '0'} Feldwerte als CSV heruntergeladen.`
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'CSV-Export fehlgeschlagen'
  } finally {
    csvBusy.value = false
  }
}

async function fillFromCsv(e: Event) {
  const input = e.target as HTMLInputElement
  const csv = input.files?.[0]
  input.value = ''
  if (!csv || !file.value) return
  csvBusy.value = true
  error.value = null
  csvSummary.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('data', csv)
    fd.append('flatten', String(flatten.value))
    const resp = await apiPost('/api/pdf-extras/form/fill-csv', fd)
    const rows = Number(resp.headers.get('X-Rows') || '0')
    await downloadBlob(resp, rows > 1 ? 'formulare.zip' : 'formular.pdf')
    const warnings = Number(resp.headers.get('X-Warnings') || '0')
    csvSummary.value =
      `${rows} Formular(e) befüllt und heruntergeladen` +
      (warnings ? ` — ${warnings} Hinweis(e), siehe hinweise.txt im ZIP.` : '.')
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Serienbefüllung fehlgeschlagen'
  } finally {
    csvBusy.value = false
  }
}
</script>
