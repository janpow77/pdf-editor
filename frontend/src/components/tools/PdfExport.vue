<template>
  <div class="space-y-5">
    <ToolHeader title="PDF exportieren" description="Dokumentinhalte als Markdown, HTML, JSON oder CSV ausgeben." @back="$emit('back')" />

    <UiAlert tone="info">
      Markdown erkennt Überschriften, JSON bewahrt Textpositionen und CSV extrahiert erkannte Tabellen.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField label="Zielformat" for-id="export-format">
        <select id="export-format" v-model="format" class="ui-control w-full sm:w-auto">
          <option value="markdown">Markdown (.md)</option>
          <option value="html">HTML (.html)</option>
          <option value="json">JSON (Textblöcke + Positionen)</option>
          <option value="csv">CSV (erkannte Tabellen)</option>
        </select>
      </UiField>
      <UiField v-if="format === 'csv'" label="Seitenbereich" for-id="export-pages" hint="Leer lassen, um alle Seiten zu verwenden.">
        <input id="export-pages" v-model="pages" type="text" placeholder="z. B. 1-3,5" class="ui-control w-full sm:w-72" />
      </UiField>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Export heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Exportiere…' : 'Exportieren' }}
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
const format = ref('markdown')
const pages = ref('')

const EXT: Record<string, string> = { markdown: '.md', html: '.html', json: '.json', csv: '.csv' }

async function apply(): Promise<void> {
  if (!file.value) return
  const base = file.value.name.replace(/\.pdf$/i, '')
  const fd = new FormData()
  fd.append('file', file.value)
  if (format.value === 'csv') {
    fd.append('pages', pages.value)
    await run('/api/pdf-more/to-csv', fd, `${base}.csv`)
  } else {
    await run(`/api/pdf-more/export/${format.value}`, fd, `${base}${EXT[format.value]}`)
  }
}
</script>
