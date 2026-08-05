<template>
  <div class="space-y-5">
    <ToolHeader title="Text suchen & ersetzen" description="Kurze Textstellen an ihrer bestehenden Position austauschen." @back="$emit('back')" />

    <UiAlert tone="warning">
      Der neue Text wird ohne automatische Zeilenumbruch-Anpassung eingesetzt. Für Absätze bitte „Text bearbeiten“ verwenden.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Suchen nach" for-id="replace-search" required>
          <input id="replace-search" v-model="search" type="text" class="ui-control w-full" />
        </UiField>
        <UiField label="Ersetzen durch" for-id="replace-value">
          <input id="replace-value" v-model="replacement" type="text" class="ui-control w-full" />
        </UiField>
      </div>
      <label class="ui-choice"><input v-model="matchCase" type="checkbox" class="rounded" /> Groß- und Kleinschreibung beachten</label>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>{{ replacements }} Ersetzung(en) durchgeführt und Datei heruntergeladen.</UiAlert>
    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" :disabled="!search.trim()" @click="apply">
      {{ loading ? 'Ersetze…' : 'Ersetzen' }}
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
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

const file = ref<File | null>(null)
const search = ref('')
const replacement = ref('')
const matchCase = ref(true)
const loading = ref(false)
const error = ref<string | null>(null)
const done = ref(false)
const replacements = ref(0)
let operationGeneration = 0

watch([file, search, replacement, matchCase], () => {
  operationGeneration += 1
  done.value = false
  replacements.value = 0
  error.value = null
})

async function apply(): Promise<void> {
  const currentFile = file.value
  const query = search.value.trim()
  if (!currentFile || !query) return
  const generation = ++operationGeneration
  loading.value = true
  error.value = null
  done.value = false

  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    formData.append('search', query)
    formData.append('replace', replacement.value)
    formData.append('match_case', String(matchCase.value))
    const response = await apiPost('/api/pdf-editor/text/replace', formData)
    await downloadBlob(response, currentFile.name.replace(/\.pdf$/i, '_ersetzt.pdf'))
    if (generation !== operationGeneration || file.value !== currentFile) return
    replacements.value = Number(response.headers.get('X-Replacements') || 0)
    done.value = true
  } catch (caught: unknown) {
    if (generation === operationGeneration) {
      error.value = caught instanceof Error ? caught.message : 'Die Ersetzung ist fehlgeschlagen.'
    }
  } finally {
    if (generation === operationGeneration) loading.value = false
  }
}
</script>
