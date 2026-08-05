<template>
  <div class="space-y-5">
    <ToolHeader title="PDF komprimieren" description="Dateigröße mit einer kontrollierten Qualitätsstufe reduzieren." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-3">
      <fieldset>
        <legend class="ui-label">Komprimierungsstufe</legend>
        <div class="grid gap-3 sm:grid-cols-3">
          <UiPanel
            v-for="option in qualities"
            :key="option.value"
            as="button"
            type="button"
            padding="sm"
            class="text-center transition hover:-translate-y-0.5 hover:shadow-apple"
            :class="quality === option.value ? 'ring-2 ring-primary-500' : ''"
            :aria-pressed="quality === option.value"
            @click="quality = option.value"
          >
            <div class="text-xl" aria-hidden="true">{{ option.icon }}</div>
            <div class="mt-1 text-sm font-semibold">{{ option.label }}</div>
            <div class="text-xs opacity-70">{{ option.desc }}</div>
          </UiPanel>
        </div>
      </fieldset>
    </UiPanel>

    <UiPanel v-if="result" tone="success">
      <div class="grid grid-cols-3 gap-4 text-center">
        <div><p class="text-xs opacity-70">Original</p><p class="text-lg font-bold">{{ formatFileSize(result.originalSize) }}</p></div>
        <div><p class="text-xs opacity-70">Komprimiert</p><p class="text-lg font-bold">{{ formatFileSize(result.compressedSize) }}</p></div>
        <div><p class="text-xs opacity-70">Ersparnis</p><p class="text-lg font-bold">{{ result.ratio }} %</p></div>
      </div>
    </UiPanel>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="doCompress">
      {{ loading ? 'Komprimiere…' : 'PDF komprimieren' }}
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
import UiPanel from '@/components/ui/UiPanel.vue'
import { usePdfTools } from '@/composables/usePdfTools'
import { formatFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, withLoading, compressPdf } = usePdfTools()
const file = ref<File | null>(null)
const quality = ref('medium')
const result = ref<{ originalSize: number; compressedSize: number; savings: number; ratio: number } | null>(null)

const qualities = [
  { value: 'low', label: 'Maximal', desc: 'Kleinste Datei', icon: '🗜️' },
  { value: 'medium', label: 'Ausgewogen', desc: 'Gute Balance', icon: '⚖️' },
  { value: 'high', label: 'Minimal', desc: 'Beste Qualität', icon: '✨' },
]

async function doCompress(): Promise<void> {
  if (!file.value) return
  result.value = null
  const metadata = await withLoading(() => compressPdf(file.value!, quality.value))
  if (metadata) result.value = metadata
}
</script>
