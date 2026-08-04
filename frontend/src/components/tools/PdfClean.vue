<template>
  <div class="space-y-5">
    <ToolHeader title="PDF bereinigen" description="Versteckte und personenbezogene Dokumentinformationen vor der Weitergabe entfernen." @back="$emit('back')" />

    <UiAlert tone="info">
      Entfernt Metadaten, JavaScript, eingebettete Dateien und versteckte Inhalte. Der sichtbare Inhalt bleibt unverändert.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiAlert v-if="done" tone="success" live>PDF bereinigt und heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Bereinige…' : 'Bereinigen' }}
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
  await run('/api/pdf-more/clean', fd, file.value.name.replace(/\.pdf$/i, '_bereinigt.pdf'))
}
</script>
