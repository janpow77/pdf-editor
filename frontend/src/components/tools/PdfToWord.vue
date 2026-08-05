<template>
  <div class="space-y-5">
    <ToolHeader title="PDF → Word" description="PDF-Inhalte als bearbeitbare DOCX-Datei exportieren." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField label="Seitenbereich (optional)" for-id="word-pages" hint="Leer lassen, um alle Seiten zu konvertieren.">
        <input id="word-pages" v-model="pages" type="text" placeholder="z. B. 1-5,10" class="ui-control w-full" />
      </UiField>
      <label class="ui-choice"><input v-model="useOcr" type="checkbox" class="rounded" /> OCR für gescannte Dokumente verwenden</label>
      <UiField v-if="useOcr" label="OCR-Sprache" for-id="word-ocr-language">
        <select id="word-ocr-language" v-model="ocrLanguage" class="ui-control w-full sm:w-auto">
          <option value="deu">Deutsch</option>
          <option value="eng">Englisch</option>
          <option value="deu+eng">Deutsch + Englisch</option>
        </select>
      </UiField>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Word-Datei erstellt und heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="run">
      {{ loading ? 'Konvertiere…' : 'In Word umwandeln' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { usePdfTools } from '@/composables/usePdfTools'
import { prefDefault } from '@/lib/auth'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, pdfToWord } = usePdfTools()
const file = ref<File | null>(null)
const pages = ref('')
const useOcr = ref(false)
const ocrLanguage = ref(prefDefault('ocr_language', 'deu'))
const done = ref(false)

async function run(): Promise<void> {
  if (!file.value) return
  done.value = false
  const succeeded = await withLoading(() =>
    pdfToWord(file.value!, {
      pages: pages.value.trim() || undefined,
      useOcr: useOcr.value,
      ocrLanguage: useOcr.value ? ocrLanguage.value : undefined,
    }),
  )
  if (succeeded) done.value = true
}
</script>
