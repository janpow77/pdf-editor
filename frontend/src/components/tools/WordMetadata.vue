<template>
  <div class="space-y-4">
    <button class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 flex items-center gap-1" @click="$emit('back')">
      ← Zurück
    </button>
    <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Word Metadaten</h2>
    <p class="text-sm text-gray-500">Titel, Autor, Bearbeitungsdatum und weitere Eigenschaften einer Word-Datei lesen und ändern.</p>

    <!-- Upload -->
    <div v-if="!file" class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-8 text-center">
      <input ref="fileInput" type="file" accept=".docx,.doc" class="hidden" @change="onFileSelect" />
      <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700" @click="($refs.fileInput as HTMLInputElement).click()">
        Word-Datei auswählen
      </button>
      <p class="text-xs text-gray-400 mt-2">.docx / .doc</p>
    </div>

    <!-- Metadata Form -->
    <div v-else class="space-y-4">
      <div class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <span class="text-2xl">📝</span>
        <div>
          <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
          <p class="text-xs text-gray-500">{{ (file.size / 1024).toFixed(1) }} KB</p>
        </div>
        <button class="ml-auto text-sm text-red-500 hover:text-red-700" @click="reset">Entfernen</button>
      </div>

      <div v-if="loading" class="text-center py-6">
        <div class="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
        <p class="text-sm text-gray-500 mt-2">Metadaten werden gelesen…</p>
      </div>

      <div v-if="meta && !loading" class="space-y-3">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div v-for="field in fields" :key="field.key">
            <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{{ field.label }}</label>
            <input
              v-if="field.type !== 'datetime-local'"
              v-model="meta[field.key]"
              :type="field.type || 'text'"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            />
            <input
              v-else
              :value="toLocalDatetime(meta[field.key])"
              type="datetime-local"
              class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              @input="meta[field.key] = fromLocalDatetime(($event.target as HTMLInputElement).value)"
            />
          </div>
        </div>

        <div class="flex gap-3 pt-2">
          <button
            class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            :disabled="saving"
            @click="save"
          >
            {{ saving ? 'Speichern…' : 'Metadaten setzen & herunterladen' }}
          </button>
        </div>
      </div>

      <p v-if="error" class="text-sm text-red-500">{{ error }}</p>
      <p v-if="success" class="text-sm text-green-600">{{ success }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { readWordMetadata, setWordMetadata } = usePdfTools()

const file = ref<File | null>(null)
const meta = ref<Record<string, any>>({})
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)

const fields = [
  { key: 'title', label: 'Titel' },
  { key: 'author', label: 'Autor' },
  { key: 'subject', label: 'Betreff' },
  { key: 'keywords', label: 'Schlüsselwörter' },
  { key: 'category', label: 'Kategorie' },
  { key: 'comments', label: 'Kommentare' },
  { key: 'last_modified_by', label: 'Zuletzt geändert von' },
  { key: 'created', label: 'Erstellt am', type: 'datetime-local' },
  { key: 'modified', label: 'Geändert am', type: 'datetime-local' },
]

function toLocalDatetime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toISOString().slice(0, 16)
  } catch { return '' }
}

function fromLocalDatetime(local: string): string {
  if (!local) return ''
  return new Date(local).toISOString()
}

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) {
    file.value = input.files[0]
  }
}

watch(file, async (f) => {
  if (!f) return
  loading.value = true
  error.value = null
  success.value = null
  try {
    meta.value = await readWordMetadata(f)
  } catch (e: any) {
    error.value = e.message || 'Fehler beim Lesen'
  } finally {
    loading.value = false
  }
})

async function save() {
  if (!file.value) return
  saving.value = true
  error.value = null
  success.value = null
  try {
    await setWordMetadata(file.value, {
      title: meta.value.title,
      author: meta.value.author,
      subject: meta.value.subject,
      keywords: meta.value.keywords,
      category: meta.value.category,
      comments: meta.value.comments,
      last_modified_by: meta.value.last_modified_by,
      modified: meta.value.modified,
      created: meta.value.created,
    })
    success.value = 'Datei mit neuen Metadaten heruntergeladen.'
  } catch (e: any) {
    error.value = e.message || 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

function reset() {
  file.value = null
  meta.value = {}
  error.value = null
  success.value = null
}
</script>
