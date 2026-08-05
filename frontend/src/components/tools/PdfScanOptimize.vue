<template>
  <div class="space-y-5">
    <ToolHeader title="Scan optimieren" description="Gescannte Dokumente geraderücken, drehen, entrauschen und durchsuchbar machen." @back="$emit('back')" />

    <UiAlert tone="info">Die OCR-Verarbeitung kann je nach Seitenzahl mehrere Minuten dauern.</UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField label="Sprache" for-id="scan-language">
        <select id="scan-language" v-model="language" class="ui-control w-full sm:w-auto">
          <option value="deu">Deutsch</option>
          <option value="eng">Englisch</option>
          <option value="deu+eng">Deutsch + Englisch</option>
          <option value="fra">Französisch</option>
          <option value="ita">Italienisch</option>
          <option value="spa">Spanisch</option>
          <option value="nld">Niederländisch</option>
          <option value="pol">Polnisch</option>
        </select>
      </UiField>
      <div class="grid gap-2 sm:grid-cols-2">
        <label class="ui-choice"><input v-model="deskew" type="checkbox" class="rounded" /> Seiten geraderücken</label>
        <label class="ui-choice"><input v-model="rotate" type="checkbox" class="rounded" /> Seiten automatisch drehen</label>
        <label class="ui-choice"><input v-model="forceOcr" type="checkbox" class="rounded" /> OCR erzwingen</label>
        <label class="ui-choice"><input v-model="clean" type="checkbox" class="rounded" /> Seiten entrauschen</label>
      </div>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Scan optimiert und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Optimiere…' : 'Optimieren' }}
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
import { downloadBlob } from '@/lib/api'
import { runJob } from '@/lib/jobs'
import { prefDefault } from '@/lib/auth'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, done } = useToolRun()
const file = ref<File | null>(null)
const language = ref(prefDefault('ocr_language', 'deu'))
const deskew = ref(true)
const rotate = ref(true)
const forceOcr = ref(false)
const clean = ref(false)

async function apply(): Promise<void> {
  if (!file.value) return
  loading.value = true
  error.value = null
  done.value = false
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('language', language.value)
    fd.append('deskew', String(deskew.value))
    fd.append('rotate_pages', String(rotate.value))
    fd.append('force_ocr', String(forceOcr.value))
    fd.append('clean', String(clean.value))
    // Async-Job statt Direktaufruf – Scan-Optimierung kann Minuten dauern.
    const response = await runJob('/api/pdf-extras/jobs/scan-optimize', fd)
    await downloadBlob(response, file.value.name.replace(/\.pdf$/i, '_optimiert.pdf'))
    done.value = true
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}
</script>
