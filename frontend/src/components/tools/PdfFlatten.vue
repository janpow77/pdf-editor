<template>
  <div class="space-y-5">
    <ToolHeader title="Anmerkungen einbrennen" description="Kommentare, Markierungen und Formularinhalte dauerhaft in den Seiteninhalt übernehmen." @back="$emit('back')" />

    <UiAlert tone="info">
      Nach dem Einbrennen sind Kommentare, Markierungen und Formularinhalte nicht mehr separat veränderbar.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiAlert v-if="done" tone="success" live>Anmerkungen eingebrannt und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Verarbeite…' : 'Einbrennen' }}
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
  await run('/api/pdf-editor/flatten', fd, file.value.name.replace(/\.pdf$/i, '_flach.pdf'))
}
</script>
