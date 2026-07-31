<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Bates-Nummerierung</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Fortlaufende, eindeutige Kennzeichnung jeder Seite (z.B. für Akten und Beweismittel):
      Präfix + laufende Nummer mit fester Stellenzahl.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Präfix</label>
        <input v-model="prefix" type="text" placeholder="AKTE-" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Startnummer</label>
        <input v-model.number="start" type="number" min="0" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Stellen</label>
        <input v-model.number="digits" type="number" min="1" max="12" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Position</label>
        <select v-model="position" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="bottom-right">unten rechts</option>
          <option value="bottom-left">unten links</option>
          <option value="bottom-center">unten Mitte</option>
          <option value="top-right">oben rechts</option>
          <option value="top-left">oben links</option>
          <option value="top-center">oben Mitte</option>
        </select>
      </div>
      <p class="col-span-2 sm:col-span-4 text-xs text-gray-600 dark:text-gray-400">Vorschau: {{ preview }}</p>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Nummeriert von {{ first }} bis {{ last }}, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Nummeriere…' : 'Bates-Nummern einfügen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const prefix = ref('AKTE-')
const start = ref(1)
const digits = ref(6)
const position = ref('bottom-right')
const first = ref('')
const last = ref('')

const preview = computed(() => `${prefix.value}${String(start.value).padStart(digits.value, '0')}`)

async function apply() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('prefix', prefix.value)
  fd.append('start', String(start.value))
  fd.append('digits', String(digits.value))
  fd.append('position', position.value)
  const resp = await run('/api/pdf-extras/bates', fd, file.value.name.replace(/\.pdf$/i, '_bates.pdf'))
  if (resp) {
    first.value = resp.headers.get('X-Bates-First') || ''
    last.value = resp.headers.get('X-Bates-Last') || ''
  }
}
</script>
