<template>
  <div class="space-y-5">
    <ToolHeader title="Kopf- und Fußzeile" description="Wiederkehrende Texte und Platzhalter an sechs festen Positionen einfügen." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiAlert tone="info">Verfügbare Platzhalter: {page}, {total}, {date}, {title}.</UiAlert>
      <div class="grid gap-3 sm:grid-cols-3">
        <UiField v-for="field in textFields" :key="field.key" :label="field.label" :for-id="`header-footer-${field.key}`">
          <input :id="`header-footer-${field.key}`" v-model="fields[field.key]" type="text" class="ui-control w-full" />
        </UiField>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Schriftgröße" for-id="header-footer-font-size">
          <input id="header-footer-font-size" v-model.number="fontSize" type="number" min="6" max="18" class="ui-control w-full" />
        </UiField>
        <UiField label="Ab Seite" for-id="header-footer-start-page">
          <input id="header-footer-start-page" v-model.number="startPage" type="number" min="1" class="ui-control w-full" />
        </UiField>
      </div>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Kopf- und Fußzeilen eingefügt und Datei heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" :disabled="!hasContent" @click="apply">
      {{ loading ? 'Verarbeite…' : 'Einfügen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (event: 'back'): void }>()

type TextPosition = 'header_left' | 'header_center' | 'header_right' | 'footer_left' | 'footer_center' | 'footer_right'

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const fields = reactive<Record<TextPosition, string>>({
  header_left: '',
  header_center: '',
  header_right: '',
  footer_left: '',
  footer_center: '',
  footer_right: '',
})
const textFields: { key: TextPosition; label: string }[] = [
  { key: 'header_left', label: 'Kopf links' },
  { key: 'header_center', label: 'Kopf Mitte' },
  { key: 'header_right', label: 'Kopf rechts' },
  { key: 'footer_left', label: 'Fuß links' },
  { key: 'footer_center', label: 'Fuß Mitte' },
  { key: 'footer_right', label: 'Fuß rechts' },
]
const fontSize = ref(9)
const startPage = ref(1)
const hasContent = computed(() => Object.values(fields).some((value) => value.trim()))

async function apply(): Promise<void> {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  for (const [key, value] of Object.entries(fields)) fd.append(key, value)
  fd.append('font_size', String(fontSize.value))
  fd.append('start_page', String(startPage.value))
  await run('/api/pdf-editor/header-footer', fd, file.value.name.replace(/\.pdf$/i, '_kopf_fuss.pdf'))
}
</script>
