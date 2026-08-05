<template>
  <div class="space-y-5">
    <ToolHeader title="PDF → Text" description="Den reinen Dokumenttext als TXT-Datei extrahieren." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiAlert v-if="done" tone="success" live>Text extrahiert und als TXT-Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Extrahiere…' : 'Text extrahieren' }}
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
  await run('/api/pdf-extras/to-text', fd, file.value.name.replace(/\.pdf$/i, '.txt'))
}
</script>
