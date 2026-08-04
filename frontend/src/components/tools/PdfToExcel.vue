<template>
  <div class="space-y-5">
    <ToolHeader title="PDF → Excel" description="Tabellen aus PDF-Seiten in eine bearbeitbare Arbeitsmappe extrahieren." @back="$emit('back')" />

    <UiAlert tone="info">Beste Ergebnisse liefern PDFs mit echten Tabellen. Ein begrenzter Seitenbereich beschleunigt die Erkennung.</UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField label="Seitenbereich (optional)" for-id="excel-pages" hint="Leer lassen, um alle Seiten zu analysieren.">
        <input id="excel-pages" v-model="pages" type="text" placeholder="z. B. 69-72" class="ui-control w-full" />
      </UiField>
      <label class="ui-choice"><input v-model="consolidate" type="checkbox" class="rounded" /> Zusammengehörige Tabellen mehrerer Seiten zusammenführen</label>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Excel-Datei erstellt und heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="run">
      {{ loading ? 'Extrahiere Tabellen…' : 'In Excel umwandeln' }}
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

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, pdfToExcel } = usePdfTools()
const file = ref<File | null>(null)
const pages = ref('')
const consolidate = ref(true)
const done = ref(false)

async function run(): Promise<void> {
  if (!file.value) return
  done.value = false
  const succeeded = await withLoading(() =>
    pdfToExcel(file.value!, {
      pages: pages.value.trim() || undefined,
      consolidate: consolidate.value,
    }),
  )
  if (succeeded) done.value = true
}
</script>
