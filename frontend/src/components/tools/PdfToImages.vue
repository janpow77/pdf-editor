<template>
  <div class="space-y-5">
    <ToolHeader title="PDF in Bilder umwandeln" description="Ausgewählte Seiten als PNG- oder JPEG-Dateien exportieren." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file">
      <div class="grid gap-4 sm:grid-cols-3">
        <UiField label="Seiten" for-id="images-pages" hint="Leer lassen, um alle Seiten zu exportieren.">
          <input id="images-pages" v-model="pages" type="text" class="ui-control w-full" placeholder="z. B. 1-5" />
        </UiField>
        <UiField label="Format" for-id="images-format">
          <select id="images-format" v-model="format" class="ui-control w-full">
            <option value="png">PNG (verlustfrei)</option>
            <option value="jpg">JPG (kleiner)</option>
          </select>
        </UiField>
        <UiField label="Auflösung" for-id="images-dpi">
          <select id="images-dpi" v-model.number="dpi" class="ui-control w-full">
            <option :value="72">72 DPI (Bildschirm)</option>
            <option :value="150">150 DPI (Standard)</option>
            <option :value="300">300 DPI (Druck)</option>
            <option :value="600">600 DPI (Hochqualität)</option>
          </select>
        </UiField>
      </div>
    </UiPanel>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="doConvert">
      {{ loading ? 'Konvertiere…' : 'In Bilder umwandeln' }}
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

const { loading, error, withLoading, pdfToImages } = usePdfTools()
const file = ref<File | null>(null)
const pages = ref('')
const format = ref('png')
const dpi = ref(150)

async function doConvert(): Promise<void> {
  if (!file.value) return
  await withLoading(() => pdfToImages(file.value!, pages.value || undefined, format.value, dpi.value))
}
</script>
