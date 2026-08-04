<template>
  <div class="space-y-5">
    <ToolHeader title="Rechteverwaltung" description="Drucken, Kopieren, Ändern und Kommentieren gezielt erlauben oder sperren." @back="$emit('back')" />

    <UiAlert tone="info">
      Das PDF bleibt ohne Passwort lesbar. Das Besitzer-Passwort wird ausschließlich für diese Verarbeitung verwendet und nicht gespeichert.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <UiField label="Besitzer-Passwort" for-id="permissions-owner-password" required>
        <input id="permissions-owner-password" v-model="ownerPassword" type="password" class="ui-control w-full" autocomplete="new-password" />
      </UiField>
      <fieldset>
        <legend class="ui-label">Erlaubte Aktionen</legend>
        <div class="grid gap-2 sm:grid-cols-2">
          <label v-for="permission in permissionOptions" :key="permission.key" class="ui-choice">
            <input v-model="perms[permission.key]" type="checkbox" class="rounded border-gray-300" />
            {{ permission.label }}
          </label>
        </div>
      </fieldset>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>Rechte gesetzt und PDF heruntergeladen.</UiAlert>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" :disabled="!ownerPassword" @click="apply">
      {{ loading ? 'Verarbeite…' : 'Rechte setzen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
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
const ownerPassword = ref('')
const perms = reactive<Record<string, boolean>>({
  allow_print: true,
  allow_copy: false,
  allow_modify: false,
  allow_annotate: true,
})

const permissionOptions = [
  { key: 'allow_print', label: 'Drucken erlauben' },
  { key: 'allow_copy', label: 'Kopieren erlauben' },
  { key: 'allow_modify', label: 'Ändern erlauben' },
  { key: 'allow_annotate', label: 'Kommentieren erlauben' },
]

async function apply(): Promise<void> {
  if (!file.value || !ownerPassword.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('owner_password', ownerPassword.value)
  for (const [key, value] of Object.entries(perms)) fd.append(key, String(value))
  await run('/api/pdf-more/permissions', fd, file.value.name.replace(/\.pdf$/i, '_rechte.pdf'))
}
</script>
