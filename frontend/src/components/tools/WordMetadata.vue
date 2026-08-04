<template>
  <div class="space-y-5">
    <ToolHeader title="Word-Metadaten" description="Titel, Autor, Datumswerte und weitere Dokumenteigenschaften bearbeiten." @back="$emit('back')" />

    <FileDrop v-model="file" accept=".docx,.doc" label="Word-Datei" />

    <div v-if="loading" class="flex items-center justify-center gap-3 py-6" role="status">
      <span class="h-7 w-7 animate-spin rounded-full border-2 border-gray-300 border-t-primary-600" aria-hidden="true"></span>
      <span class="text-sm text-gray-600 dark:text-gray-300">Metadaten werden gelesen…</span>
    </div>

    <UiPanel v-if="file && meta && !loading" class="space-y-4">
      <div class="grid gap-4 md:grid-cols-2">
        <UiField v-for="field in fields" :key="field.key" :label="field.label" :for-id="`word-meta-${field.key}`">
          <input
            v-if="field.type !== 'datetime-local'"
            :id="`word-meta-${field.key}`"
            v-model="meta[field.key]"
            type="text"
            class="ui-control w-full"
          />
          <input
            v-else
            :id="`word-meta-${field.key}`"
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

interface WordMetadataValues {
  title: string
  author: string
  subject: string
  keywords: string
  category: string
  comments: string
  last_modified_by: string
  created: string
  modified: string
}

type MetadataKey = keyof WordMetadataValues

const { readWordMetadata, setWordMetadata } = usePdfTools()
const file = ref<File | null>(null)
const meta = ref<WordMetadataValues | null>(null)
const loading = ref(false)
const saving = ref(false)
const error = ref<string | null>(null)
const success = ref<string | null>(null)
let readGeneration = 0

const fields: { key: MetadataKey; label: string; type?: 'datetime-local' }[] = [
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

function emptyMetadata(): WordMetadataValues {
  return {
    title: '',
    author: '',
    subject: '',
    keywords: '',
    category: '',
    comments: '',
    last_modified_by: '',
    created: '',
    modified: '',
  }
}

function normalizeMetadata(value: unknown): WordMetadataValues {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const normalized = emptyMetadata()
  for (const key of Object.keys(normalized) as MetadataKey[]) {
    normalized[key] = source[key] == null ? '' : String(source[key])
  }
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
    const result = await readWordMetadata(currentFile)
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
    await setWordMetadata(file.value, meta.value)
    success.value = 'Datei mit neuen Metadaten heruntergeladen.'
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}
</script>
