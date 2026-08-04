<template>
  <div class="space-y-5">
    <ToolHeader title="Unterschrift / Stempelbild einfügen" description="Ein PNG- oder JPEG-Bild an einer definierten Stelle des PDFs platzieren." @back="$emit('back')" />

    <UiAlert tone="info">Dies ist eine sichtbare Bildsignatur und keine zertifikatsbasierte digitale Signatur.</UiAlert>
    <FileDrop v-model="file" label="PDF" />
    <FileDrop v-model="image" accept=".png,.jpg,.jpeg,image/png,image/jpeg" label="Signaturbild (PNG/JPEG)" />

    <UiPanel v-if="file && image">
      <div class="grid gap-4 sm:grid-cols-3">
        <UiField label="Seite" for-id="signature-page"><input id="signature-page" v-model.number="page" type="number" min="1" class="ui-control w-full" /></UiField>
        <UiField label="Position" for-id="signature-position">
          <select id="signature-position" v-model="preset" class="ui-control w-full"><option value="br">unten rechts</option><option value="bl">unten links</option><option value="bc">unten Mitte</option><option value="tr">oben rechts</option><option value="tl">oben links</option></select>
        </UiField>
        <UiField :label="`Breite: ${Math.round(width * 100)} %`" for-id="signature-width"><input id="signature-width" v-model.number="width" type="range" min="0.1" max="0.6" step="0.05" class="w-full" /></UiField>
      </div>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Bild eingefügt und Datei heruntergeladen.</UiAlert>
    <UiButton v-if="file && image" variant="primary" size="lg" :loading="loading" @click="apply">{{ loading ? 'Füge ein…' : 'Einfügen' }}</UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, done, run, reset } = useToolRun()
const file = ref<File | null>(null)
const image = ref<File | null>(null)
const page = ref(1)
const preset = ref('br')
const width = ref(0.25)

watch([file, image, page, preset, width], reset)

const coords = computed(() => {
  const imageWidth = width.value
  switch (preset.value) {
    case 'bl': return { x: 0.06, y: 0.82 }
    case 'bc': return { x: (1 - imageWidth) / 2, y: 0.82 }
    case 'tr': return { x: 0.94 - imageWidth, y: 0.06 }
    case 'tl': return { x: 0.06, y: 0.06 }
    default: return { x: 0.94 - imageWidth, y: 0.82 }
  }
})

async function apply(): Promise<void> {
  const currentFile = file.value; const currentImage = image.value
  if (!currentFile || !currentImage) return
  const formData = new FormData()
  formData.append('file', currentFile); formData.append('image', currentImage)
  formData.append('page', String(Math.max(1, Math.trunc(page.value))))
  formData.append('x', String(coords.value.x)); formData.append('y', String(coords.value.y)); formData.append('width', String(width.value))
  await run('/api/pdf-extras/sign-image', formData, currentFile.name.replace(/\.pdf$/i, '_signiert.pdf'))
}
</script>
