<template>
  <div class="space-y-5">
    <ToolHeader title="Unterschrift oder Stempelbild" description="Ein PNG- oder JPEG-Bild an einer festen Dokumentposition einfügen." @back="$emit('back')" />

    <UiAlert tone="info">Dies ist eine sichtbare Bildsignatur und keine zertifikatsbasierte digitale Signatur.</UiAlert>

    <FileDrop v-model="file" label="PDF" />
    <FileDrop v-model="image" accept=".png,.jpg,.jpeg" label="Signaturbild (PNG/JPG)" />

    <UiPanel v-if="file && image" class="space-y-4">
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Seite" for-id="sign-image-page">
          <input id="sign-image-page" v-model.number="page" type="number" min="1" class="ui-control w-full" />
        </UiField>
        <UiField label="Position" for-id="sign-image-position">
          <select id="sign-image-position" v-model="preset" class="ui-control w-full">
            <option value="br">unten rechts</option>
            <option value="bl">unten links</option>
            <option value="bc">unten Mitte</option>
            <option value="tr">oben rechts</option>
            <option value="tl">oben links</option>
          </select>
        </UiField>
      </div>
      <UiField :label="`Breite: ${Math.round(width * 100)} % der Seite`" for-id="sign-image-width">
        <input id="sign-image-width" v-model.number="width" type="range" min="0.1" max="0.6" step="0.05" class="w-full accent-primary-600" />
      </UiField>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Bild eingefügt und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file && image" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Füge ein…' : 'Einfügen' }}
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
const image = ref<File | null>(null)
const page = ref(1)
const preset = ref('br')
const width = ref(0.25)

const coords = computed(() => {
  const currentWidth = width.value
  switch (preset.value) {
    case 'bl': return { x: 0.06, y: 0.82 }
    case 'bc': return { x: (1 - currentWidth) / 2, y: 0.82 }
    case 'tr': return { x: 0.94 - currentWidth, y: 0.06 }
    case 'tl': return { x: 0.06, y: 0.06 }
    default: return { x: 0.94 - currentWidth, y: 0.82 }
  }
})

async function apply(): Promise<void> {
  if (!file.value || !image.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('image', image.value)
  fd.append('page', String(page.value))
  fd.append('x', String(coords.value.x))
  fd.append('y', String(coords.value.y))
  fd.append('width', String(width.value))
  await run('/api/pdf-extras/sign-image', fd, file.value.name.replace(/\.pdf$/i, '_signiert.pdf'))
}
</script>
