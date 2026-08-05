<template>
  <div class="space-y-5">
    <ToolHeader title="Word → PDF" description="DOC- und DOCX-Dateien in ein PDF-Dokument konvertieren." @back="$emit('back')" />

    <FileDrop v-model="file" accept=".docx,.doc" label="Word-Datei" />

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="doConvert">
      {{ loading ? 'Konvertiere…' : 'In PDF umwandeln' }}
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
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, wordToPdf } = usePdfTools()
const file = ref<File | null>(null)

async function doConvert(): Promise<void> {
  if (!file.value) return
  await withLoading(() => wordToPdf(file.value!))
}
</script>
