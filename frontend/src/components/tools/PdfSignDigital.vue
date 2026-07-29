<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Digital signieren (Zertifikat)</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Zertifikatsbasierte Signatur (PAdES) mit Ihrem eigenen PKCS#12-Zertifikat
      (.p12/.pfx). Zertifikat und Passwort werden ausschließlich für diesen einen
      Vorgang verwendet und weder gespeichert noch protokolliert.
    </div>

    <FileDrop v-model="file" label="PDF" />
    <FileDrop v-model="cert" accept=".p12,.pfx" label="Zertifikat (.p12/.pfx)" />

    <div v-if="file && cert" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zertifikats-Passwort</label>
        <input v-model="passphrase" type="password" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div class="grid sm:grid-cols-2 gap-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Grund (optional)</label>
          <input v-model="reason" type="text" placeholder="z.B. Freigabe" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ort (optional)</label>
          <input v-model="location" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
      </div>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      PDF wurde digital signiert und heruntergeladen.
    </div>

    <button
      v-if="file && cert"
      :disabled="loading"
      class="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Signiere…' : 'Digital signieren' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const cert = ref<File | null>(null)
const passphrase = ref('')
const reason = ref('')
const location = ref('')

async function apply() {
  if (!file.value || !cert.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('certificate', cert.value)
  fd.append('passphrase', passphrase.value)
  fd.append('reason', reason.value)
  fd.append('location', location.value)
  await run('/api/pdf-extras/sign-digital', fd, file.value.name.replace(/\.pdf$/i, '_signiert.pdf'))
}
</script>
