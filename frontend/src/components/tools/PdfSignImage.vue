<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Unterschrift / Stempelbild einfügen</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Fügt ein Bild (z.B. eingescannte Unterschrift, PNG mit Transparenz empfohlen) an
      einer wählbaren Position ein. Einfache Bild-Signatur — keine zertifikatsbasierte
      digitale Signatur.
    </div>

    <FileDrop v-model="file" label="PDF" />
    <FileDrop v-model="image" accept=".png,.jpg,.jpeg" label="Signaturbild (PNG/JPG)" />

    <div v-if="file && image" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Seite</label>
        <input v-model.number="page" type="number" min="1" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Position</label>
        <select v-model="preset" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="br">unten rechts</option>
          <option value="bl">unten links</option>
          <option value="bc">unten Mitte</option>
          <option value="tr">oben rechts</option>
          <option value="tl">oben links</option>
        </select>
      </div>
      <div class="col-span-2">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Breite: {{ Math.round(width * 100) }} % der Seite</label>
        <input v-model.number="width" type="range" min="0.1" max="0.6" step="0.05" class="w-full" />
      </div>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Bild eingefügt, Datei heruntergeladen.
    </div>

    <button
      v-if="file && image"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Füge ein…' : 'Einfügen' }}
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
const image = ref<File | null>(null)
const page = ref(1)
const preset = ref('br')
const width = ref(0.25)

const coords = computed(() => {
  const w = width.value
  switch (preset.value) {
    case 'bl': return { x: 0.06, y: 0.82 }
    case 'bc': return { x: (1 - w) / 2, y: 0.82 }
    case 'tr': return { x: 0.94 - w, y: 0.06 }
    case 'tl': return { x: 0.06, y: 0.06 }
    default: return { x: 0.94 - w, y: 0.82 }
  }
})

async function apply() {
  if (!file.value || !image.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('image', image.value)
  fd.append('page', String(page.value))
  fd.append('x', String(coords.value.x))
  fd.append('y', String(coords.value.y))
  fd.append('width', String(width.value))
  await run('/api/pdf-extras/sign-image', fd, file.value.name.replace(/\.pdf$/i, '_signiert.pdf'))
}
</script>
