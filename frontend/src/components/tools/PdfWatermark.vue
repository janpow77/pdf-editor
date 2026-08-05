<template>
  <div class="space-y-5">
    <ToolHeader title="Wasserzeichen hinzufügen" description="Text oder Bild mit definierter Position und Transparenz überlagern." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-5">
      <div class="flex flex-wrap gap-2" aria-label="Wasserzeichentyp">
        <UiButton size="sm" :variant="mode === 'text' ? 'primary' : 'secondary'" :aria-pressed="mode === 'text'" @click="mode = 'text'">Text</UiButton>
        <UiButton size="sm" :variant="mode === 'image' ? 'primary' : 'secondary'" :aria-pressed="mode === 'image'" @click="mode = 'image'">Bild</UiButton>
      </div>

      <template v-if="mode === 'text'">
        <UiField label="Text" for-id="watermark-text">
          <input id="watermark-text" v-model="text" type="text" class="ui-control w-full" placeholder="z. B. ENTWURF oder VERTRAULICH" />
        </UiField>
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <UiField label="Schriftgröße" for-id="watermark-font-size">
            <input id="watermark-font-size" v-model.number="fontSize" type="number" min="10" max="200" class="ui-control w-full" />
          </UiField>
          <UiField label="Farbe" for-id="watermark-color">
            <input id="watermark-color" v-model="color" type="color" class="h-11 w-full cursor-pointer rounded-xl bg-transparent" />
          </UiField>
          <UiField label="Rotation" for-id="watermark-rotation">
            <input id="watermark-rotation" v-model.number="rotation" type="number" min="-180" max="180" class="ui-control w-full" />
          </UiField>
          <UiField :label="`Transparenz: ${Math.round(opacity * 100)} %`" for-id="watermark-opacity-text">
            <input id="watermark-opacity-text" v-model.number="opacity" type="range" min="0.05" max="1" step="0.05" class="w-full accent-primary-600" />
          </UiField>
        </div>
      </template>

      <template v-else>
        <FileDrop
          v-model="watermarkImage"
          accept=".png,.jpg,.jpeg,.gif,.bmp,.tiff,.tif,.webp"
          label="Wasserzeichen-Bild"
          :max-bytes="10 * 1024 * 1024"
        />
        <UiField :label="`Transparenz: ${Math.round(opacity * 100)} %`" for-id="watermark-opacity-image">
          <input id="watermark-opacity-image" v-model.number="opacity" type="range" min="0.05" max="1" step="0.05" class="w-full accent-primary-600" />
        </UiField>
      </template>

      <fieldset>
        <legend class="ui-label">Position</legend>
        <div class="flex flex-wrap gap-2">
          <UiButton
            v-for="positionOption in positions"
            :key="positionOption.value"
            size="sm"
            :variant="position === positionOption.value ? 'primary' : 'secondary'"
            :aria-pressed="position === positionOption.value"
            @click="position = positionOption.value"
          >{{ positionOption.label }}</UiButton>
        </div>
      </fieldset>

      <UiField label="Seiten" for-id="watermark-pages" hint="Leer lassen, um alle Seiten zu bearbeiten.">
        <input id="watermark-pages" v-model="pages" type="text" class="ui-control w-full sm:w-64" placeholder="z. B. 1-5" />
      </UiField>
    </UiPanel>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" :disabled="!canApply" @click="doWatermark">
      {{ loading ? 'Wasserzeichen wird hinzugefügt…' : 'Wasserzeichen hinzufügen' }}
    </UiButton>

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
import { usePdfTools } from '@/composables/usePdfTools'
import { prefDefault } from '@/lib/auth'

defineEmits<{ (event: 'back'): void }>()

type WatermarkMode = 'text' | 'image'

const { loading, error, withLoading, addWatermark } = usePdfTools()
const file = ref<File | null>(null)
const mode = ref<WatermarkMode>('text')
const text = ref(prefDefault('watermark_text', 'ENTWURF'))
const watermarkImage = ref<File | null>(null)
const position = ref('center')
const opacity = ref(0.3)
const rotation = ref(-45)
const fontSize = ref(60)
const color = ref('#808080')
const pages = ref('')

const positions = [
  { value: 'top-left', label: 'oben links' },
  { value: 'top-right', label: 'oben rechts' },
  { value: 'center', label: 'Mitte' },
  { value: 'bottom-left', label: 'unten links' },
  { value: 'bottom-right', label: 'unten rechts' },
]

const canApply = computed(() =>
  mode.value === 'text' ? text.value.trim().length > 0 : watermarkImage.value !== null,
)

watch(mode, () => {
  error.value = null
})

async function doWatermark(): Promise<void> {
  if (!file.value || !canApply.value) return
  await withLoading(() => addWatermark(file.value!, {
    text: mode.value === 'text' ? text.value.trim() : undefined,
    image: mode.value === 'image' ? watermarkImage.value ?? undefined : undefined,
    position: position.value,
    opacity: opacity.value,
    rotation: rotation.value,
    fontSize: fontSize.value,
    color: color.value,
    pages: pages.value.trim() || undefined,
  }))
}
</script>
