<template>
  <div class="space-y-5">
    <ToolHeader title="Leere Seiten einfügen" description="Zusätzliche Seiten an einer definierten Position ergänzen." @back="$emit('back')" />

    <FileDrop v-model="file" />

    <UiPanel v-if="file">
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Einfügen nach Seite" for-id="blank-after" hint="0 fügt die Seiten am Anfang ein.">
          <input id="blank-after" v-model.number="afterPage" type="number" min="0" class="ui-control w-full" />
        </UiField>
        <UiField label="Anzahl Seiten" for-id="blank-count">
          <input id="blank-count" v-model.number="count" type="number" min="1" max="50" class="ui-control w-full" />
        </UiField>
      </div>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Seiten eingefügt und PDF heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Verarbeite…' : 'Seiten einfügen' }}
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
const afterPage = ref(1)
const count = ref(1)

async function apply(): Promise<void> {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('after_page', String(afterPage.value))
  fd.append('count', String(count.value))
  await run('/api/pdf-more/insert-blank', fd, file.value.name.replace(/\.pdf$/i, '_ergaenzt.pdf'))
}
</script>
