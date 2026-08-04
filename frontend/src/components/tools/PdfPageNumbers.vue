<template>
  <div class="space-y-5">
    <ToolHeader title="Seitenzahlen einfügen" description="Flexible Nummerierungen mit Position, Startseite und Platzhaltern ergänzen." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField label="Format" for-id="page-number-format" hint="Verfügbare Platzhalter: {page}, {total}, {date}.">
        <input id="page-number-format" v-model="format" type="text" class="ui-control w-full" />
      </UiField>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <UiField label="Position" for-id="page-number-position">
          <select id="page-number-position" v-model="position" class="ui-control w-full">
            <option value="bottom-center">unten Mitte</option>
            <option value="bottom-right">unten rechts</option>
            <option value="bottom-left">unten links</option>
            <option value="top-center">oben Mitte</option>
            <option value="top-right">oben rechts</option>
            <option value="top-left">oben links</option>
          </select>
        </UiField>
        <UiField label="Ab Seite" for-id="page-number-start-page">
          <input id="page-number-start-page" v-model.number="startPage" type="number" min="1" class="ui-control w-full" />
        </UiField>
        <UiField label="Startnummer" for-id="page-number-start-number">
          <input id="page-number-start-number" v-model.number="startNumber" type="number" min="1" class="ui-control w-full" />
        </UiField>
        <UiField label="Schriftgröße" for-id="page-number-font-size">
          <input id="page-number-font-size" v-model.number="fontSize" type="number" min="6" max="24" class="ui-control w-full" />
        </UiField>
      </div>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Seitenzahlen eingefügt und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Verarbeite…' : 'Seitenzahlen einfügen' }}
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
const format = ref('Seite {page} von {total}')
const position = ref('bottom-center')
const startPage = ref(1)
const startNumber = ref(1)
const fontSize = ref(10)

async function apply(): Promise<void> {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('format_str', format.value)
  fd.append('position', position.value)
  fd.append('start_page', String(startPage.value))
  fd.append('start_number', String(startNumber.value))
  fd.append('font_size', String(fontSize.value))
  await run('/api/pdf-editor/page-numbers', fd, file.value.name.replace(/\.pdf$/i, '_nummeriert.pdf'))
}
</script>
