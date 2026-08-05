<template>
  <div class="space-y-5">
    <ToolHeader title="Bates-Nummerierung" description="Jede Seite mit Präfix und einer fortlaufenden Nummer eindeutig kennzeichnen." @back="$emit('back')" />

    <UiAlert tone="info">Geeignet für Akten und Beweismittel: Präfix plus laufende Nummer mit fester Stellenzahl.</UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <UiField label="Präfix" for-id="bates-prefix">
          <input id="bates-prefix" v-model="prefix" type="text" placeholder="AKTE-" class="ui-control w-full" />
        </UiField>
        <UiField label="Startnummer" for-id="bates-start">
          <input id="bates-start" v-model.number="start" type="number" min="0" class="ui-control w-full" />
        </UiField>
        <UiField label="Stellen" for-id="bates-digits">
          <input id="bates-digits" v-model.number="digits" type="number" min="1" max="12" class="ui-control w-full" />
        </UiField>
        <UiField label="Position" for-id="bates-position">
          <select id="bates-position" v-model="position" class="ui-control w-full">
            <option value="bottom-right">unten rechts</option>
            <option value="bottom-left">unten links</option>
            <option value="bottom-center">unten Mitte</option>
            <option value="top-right">oben rechts</option>
            <option value="top-left">oben links</option>
            <option value="top-center">oben Mitte</option>
          </select>
        </UiField>
      </div>
      <UiAlert tone="info">Vorschau: <strong>{{ preview }}</strong></UiAlert>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Nummeriert von {{ first }} bis {{ last }} und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Nummeriere…' : 'Bates-Nummern einfügen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
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
const prefix = ref('AKTE-')
const start = ref(1)
const digits = ref(6)
const position = ref('bottom-right')
const first = ref('')
const last = ref('')

const preview = computed(() => `${prefix.value}${String(start.value).padStart(digits.value, '0')}`)

async function apply(): Promise<void> {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('prefix', prefix.value)
  fd.append('start', String(start.value))
  fd.append('digits', String(digits.value))
  fd.append('position', position.value)
  const response = await run('/api/pdf-extras/bates', fd, file.value.name.replace(/\.pdf$/i, '_bates.pdf'))
  if (response) {
    first.value = response.headers.get('X-Bates-First') || ''
    last.value = response.headers.get('X-Bates-Last') || ''
  }
}
</script>
