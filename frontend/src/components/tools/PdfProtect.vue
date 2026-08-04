<template>
  <div class="space-y-5">
    <ToolHeader title="PDF schützen oder entsperren" description="AES-256-Passwortschutz setzen oder mit bekanntem Passwort entfernen." @back="$emit('back')" />

    <div class="grid gap-3 sm:grid-cols-2">
      <UiPanel
        v-for="option in modes"
        :key="option.value"
        as="button"
        type="button"
        padding="sm"
        class="text-center transition hover:-translate-y-0.5 hover:shadow-apple"
        :class="mode === option.value ? 'ring-2 ring-primary-500' : ''"
        :aria-pressed="mode === option.value"
        @click="mode = option.value; done = false"
      >
        <div class="text-xl" aria-hidden="true">{{ option.icon }}</div>
        <div class="mt-1 text-sm font-semibold">{{ option.label }}</div>
        <div class="text-xs opacity-70">{{ option.desc }}</div>
      </UiPanel>
    </div>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField :label="mode === 'protect' ? 'Passwort zum Öffnen' : 'Bekanntes PDF-Passwort'" for-id="protect-password" required>
        <input id="protect-password" v-model="password" type="password" class="ui-control w-full" autocomplete="new-password" />
      </UiField>
      <UiField v-if="mode === 'protect'" label="Besitzer-Passwort (optional)" for-id="protect-owner-password" hint="Ohne Angabe wird das Öffnen-Passwort verwendet.">
        <input id="protect-owner-password" v-model="ownerPassword" type="password" class="ui-control w-full" autocomplete="new-password" />
      </UiField>
      <UiAlert tone="info">Die Passwörter werden ausschließlich für diese Verarbeitung verwendet und nicht gespeichert.</UiAlert>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>
      {{ mode === 'protect' ? 'PDF verschlüsselt und heruntergeladen.' : 'PDF entsperrt und heruntergeladen.' }}
    </UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" :disabled="!password" @click="run">
      {{ loading ? 'Verarbeite…' : mode === 'protect' ? 'PDF schützen' : 'PDF entsperren' }}
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

const { loading, error, withLoading, protectPdf, unlockPdf } = usePdfTools()
const mode = ref<'protect' | 'unlock'>('protect')
const file = ref<File | null>(null)
const password = ref('')
const ownerPassword = ref('')
const done = ref(false)

const modes = [
  { value: 'protect' as const, label: 'Schützen', desc: 'Passwort setzen', icon: '🔒' },
  { value: 'unlock' as const, label: 'Entsperren', desc: 'Passwort aufheben', icon: '🔓' },
]

async function run(): Promise<void> {
  if (!file.value || !password.value) return
  done.value = false
  const succeeded = await withLoading(() =>
    mode.value === 'protect'
      ? protectPdf(file.value!, password.value, ownerPassword.value || undefined)
      : unlockPdf(file.value!, password.value),
  )
  if (succeeded) done.value = true
}
</script>
