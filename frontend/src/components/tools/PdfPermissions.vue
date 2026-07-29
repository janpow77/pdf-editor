<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Rechteverwaltung</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Schränkt Nutzungsrechte ein (Drucken, Kopieren, Ändern, Kommentieren) — das PDF
      bleibt ohne Passwort lesbar. Änderungen an den Rechten erfordern das
      Besitzer-Passwort. Es wird nur für diese Verarbeitung verwendet, nicht gespeichert.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Besitzer-Passwort</label>
        <input
          v-model="ownerPassword"
          type="password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>
      <div class="grid grid-cols-2 gap-2">
        <label v-for="p in permissionOptions" :key="p.key" class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input v-model="perms[p.key]" type="checkbox" class="rounded border-gray-300" />
          {{ p.label }}
        </label>
      </div>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Rechte gesetzt, PDF heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading || !ownerPassword"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Verarbeite…' : 'Rechte setzen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

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

async function apply() {
  if (!file.value || !ownerPassword.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('owner_password', ownerPassword.value)
  for (const [k, v] of Object.entries(perms)) fd.append(k, String(v))
  await run('/api/pdf-more/permissions', fd, file.value.name.replace(/\.pdf$/i, '_rechte.pdf'))
}
</script>
