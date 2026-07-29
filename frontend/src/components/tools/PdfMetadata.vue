<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF Metadaten</h2>
    </div>

    <!-- Upload -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="file ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-primary-400'"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".pdf" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <p class="text-gray-500 dark:text-gray-400 mb-2">PDF hierher ziehen oder</p>
        <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Datei auswählen</button>
      </div>
      <div v-else class="flex items-center justify-center gap-3">
        <span class="text-2xl">📄</span>
        <div class="text-left">
          <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
          <p class="text-xs text-gray-500">{{ formatSize(file.size) }}</p>
        </div>
        <button class="ml-4 text-sm text-red-500 hover:text-red-700" @click="reset">Entfernen</button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loadingRead" class="text-center py-6">
      <div class="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto"></div>
      <p class="text-sm text-gray-500 mt-2">Metadaten werden gelesen...</p>
    </div>

    <!-- Read-only info -->
    <div v-if="meta && !loadingRead" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-1">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Datei-Info (nur lesen)</h3>
      <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <span class="text-gray-500 dark:text-gray-400">Seiten:</span>
        <span class="text-gray-900 dark:text-white">{{ meta.page_count }}</span>
        <span class="text-gray-500 dark:text-gray-400">Größe:</span>
        <span class="text-gray-900 dark:text-white">{{ formatSize(meta.file_size) }}</span>
      </div>
    </div>

    <!-- Editable fields -->
    <div v-if="meta && !loadingRead" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">Metadaten bearbeiten</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div v-for="field in fields" :key="field.key">
          <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{ field.label }}</label>
          <input
            v-if="field.type !== 'datetime-local'"
            v-model="form[field.key]"
            :type="field.type || 'text'"
            class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            :placeholder="field.placeholder"
          />
          <input
            v-else
            :value="toLocalDatetime(form[field.key])"
            type="datetime-local"
            step="1"
            class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            @input="form[field.key] = fromLocalDatetime(($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>
    </div>

    <!-- Save button -->
    <button
      v-if="meta && !loadingRead"
      :disabled="saving"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doSave"
    >
      <svg v-if="saving" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ saving ? 'Speichere...' : 'Metadaten setzen & herunterladen' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    <p v-if="success" class="text-sm text-green-600">{{ success }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { readMetadata, setMetadata } = usePdfTools()

const file = ref<File | null>(null)
const meta = ref<any>(null)
const form = ref<Record<string, string>>({})
const loadingRead = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const fields = [
  { key: 'title', label: 'Titel', placeholder: 'Dokumenttitel' },
  { key: 'author', label: 'Autor', placeholder: 'Verfasser' },
  { key: 'subject', label: 'Betreff', placeholder: 'Betreff / Thema' },
  { key: 'keywords', label: 'Schlagworte', placeholder: 'Kommagetrennt' },
  { key: 'creator', label: 'Ersteller-App', placeholder: 'z.B. Microsoft Word' },
  { key: 'producer', label: 'PDF-Erzeuger', placeholder: 'z.B. Adobe PDF Library' },
  { key: 'creation_date', label: 'Erstellt am', type: 'datetime-local' },
  { key: 'modification_date', label: 'Geändert am', type: 'datetime-local' },
]

function parsePdfDate(raw: string): string {
  if (!raw) return ''
  // PDF date format: D:20260115103000+00'00' or ISO
  const m = raw.match(/D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/)
  if (m) {
    return `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}`
  }
  try {
    return new Date(raw).toISOString()
  } catch {
    return ''
  }
}

function toLocalDatetime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    return d.toISOString().slice(0, 19)
  } catch { return '' }
}

function fromLocalDatetime(local: string): string {
  if (!local) return ''
  return new Date(local).toISOString()
}

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) setFile(input.files[0])
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) setFile(f)
}

async function setFile(f: File) {
  file.value = f
  meta.value = null
  form.value = {}
  error.value = null
  success.value = null
  loadingRead.value = true
  try {
    const data = await readMetadata(f)
    meta.value = data
    form.value = {
      title: data.title || '',
      author: data.author || '',
      subject: data.subject || '',
      keywords: data.keywords || '',
      creator: data.creator || '',
      producer: data.producer || '',
      creation_date: parsePdfDate(data.creation_date),
      modification_date: parsePdfDate(data.modification_date),
    }
  } catch (e: any) {
    error.value = e.message || 'Fehler beim Lesen der Metadaten'
  } finally {
    loadingRead.value = false
  }
}

async function doSave() {
  if (!file.value) return
  saving.value = true
  error.value = null
  success.value = null
  try {
    await setMetadata(file.value, {
      title: form.value.title || undefined,
      author: form.value.author || undefined,
      subject: form.value.subject || undefined,
      keywords: form.value.keywords || undefined,
      creator: form.value.creator || undefined,
      producer: form.value.producer || undefined,
      creation_date: form.value.creation_date || undefined,
      modification_date: form.value.modification_date || undefined,
    })
    success.value = 'PDF mit neuen Metadaten heruntergeladen.'
  } catch (e: any) {
    error.value = e.message || 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

function reset() {
  file.value = null
  meta.value = null
  form.value = {}
  error.value = null
  success.value = null
}
</script>
