<template>
  <div class="space-y-5">
    <ToolHeader title="PDF/A (Archivformat)" description="PDF-Dokumente für die langfristige Aufbewahrung standardisieren." @back="$emit('back')" />

    <UiAlert tone="info">
      Konvertiert das Dokument mit eingebetteten Schriften und geräteunabhängigen Farben. Für viele Archive ist PDF/A-2b die passende Voreinstellung.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file">
      <UiField label="PDF/A-Level" for-id="pdfa-level">
        <select id="pdfa-level" v-model="level" class="ui-control w-full sm:w-auto">
          <option value="1b">PDF/A-1b</option>
          <option value="2b">PDF/A-2b (empfohlen)</option>
          <option value="3b">PDF/A-3b</option>
        </select>
      </UiField>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>In PDF/A konvertiert und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Konvertiere…' : 'In PDF/A konvertieren' }}
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
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const level = ref('2b')

async function apply(): Promise<void> {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('level', level.value)
  await run('/api/pdf-extras/to-pdfa', fd, file.value.name.replace(/\.pdf$/i, '_pdfa.pdf'))
}
</script>
