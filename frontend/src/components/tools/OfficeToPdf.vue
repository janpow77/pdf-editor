<template>
  <div class="space-y-5">
    <ToolHeader title="Office → PDF" description="Office- und Textformate über LibreOffice in PDF konvertieren." @back="$emit('back')" />

    <UiAlert tone="info">
      Unterstützt Excel, PowerPoint, OpenDocument, RTF, HTML und Text. Für Word-Dateien steht ein eigenes Werkzeug bereit.
    </UiAlert>

    <FileDrop
      v-model="file"
      accept=".xlsx,.xls,.pptx,.ppt,.odt,.ods,.odp,.rtf,.txt,.html,.htm"
      label="Office-Datei"
    />

    <UiAlert v-if="done" tone="success" live>In PDF konvertiert und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Konvertiere…' : 'In PDF konvertieren' }}
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
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)

async function apply(): Promise<void> {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  await run('/api/pdf-more/office-to-pdf', fd, file.value.name.replace(/\.[^.]+$/, '.pdf'))
}
</script>
