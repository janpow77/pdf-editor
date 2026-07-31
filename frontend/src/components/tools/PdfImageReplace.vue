<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Bild ersetzen</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Tauscht ein vorhandenes Bild im PDF gegen ein neues aus — Position und Größe im
      Layout bleiben erhalten (z.B. Logo aktualisieren). Zum Einfügen zusätzlicher Bilder
      gibt es „Unterschrift" und „Wasserzeichen".
    </div>

    <FileDrop v-model="file" />

    <div v-if="loadingList" class="text-sm text-gray-500 py-4">Suche Bilder…</div>

    <div v-if="images.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        {{ images.length }} Bild(er) gefunden — auswählen:
      </h3>
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <button
          v-for="img in images"
          :key="img.xref"
          class="p-2 rounded-lg border-2 text-left transition-colors"
          :class="selected === img.xref
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'"
          @click="selected = img.xref"
        >
          <img
            v-if="img.preview"
            :src="`data:image/png;base64,${img.preview}`"
            class="w-full h-20 object-contain bg-gray-50 dark:bg-gray-800 rounded"
            alt="Bildvorschau"
          />
          <div v-else class="w-full h-20 flex items-center justify-center bg-gray-50 dark:bg-gray-800 rounded text-xs text-gray-600 dark:text-gray-400">
            keine Vorschau
          </div>
          <p class="mt-1 text-xs text-gray-600 dark:text-gray-300">Seite {{ img.page }}</p>
          <p class="text-xs text-gray-600 dark:text-gray-400">{{ img.width }} × {{ img.height }} px</p>
        </button>
      </div>
    </div>

    <div v-if="file && !loadingList && !images.length && listLoaded" class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300">
      Dieses PDF enthält keine austauschbaren Bilder.
    </div>

    <div v-if="selected" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-2">
      <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Neues Bild (PNG/JPG)</label>
      <input type="file" accept=".png,.jpg,.jpeg" class="text-sm text-gray-600 dark:text-gray-300" @change="onImage" />
      <p class="text-xs text-gray-600 dark:text-gray-400">
        Für ein sauberes Ergebnis sollte das neue Bild dasselbe Seitenverhältnis haben.
      </p>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Bild ersetzt, PDF heruntergeladen.
    </div>

    <button
      v-if="selected && newImage"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Ersetze…' : 'Bild ersetzen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'
import { apiPost } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface PdfImage {
  xref: number
  page: number
  width: number
  height: number
  preview: string
}

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const images = ref<PdfImage[]>([])
const selected = ref<number | null>(null)
const newImage = ref<File | null>(null)
const loadingList = ref(false)
const listLoaded = ref(false)

watch(file, async (f) => {
  images.value = []
  selected.value = null
  newImage.value = null
  listLoaded.value = false
  error.value = null
  if (!f) return
  loadingList.value = true
  try {
    const fd = new FormData()
    fd.append('file', f)
    const resp = await apiPost('/api/pdf-more/images/list', fd)
    images.value = ((await resp.json()) as { images: PdfImage[] }).images
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Bilder lesen fehlgeschlagen'
  } finally {
    loadingList.value = false
    listLoaded.value = true
  }
})

function onImage(e: Event) {
  newImage.value = (e.target as HTMLInputElement).files?.[0] ?? null
}

async function apply() {
  if (!file.value || !selected.value || !newImage.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('xref', String(selected.value))
  fd.append('image', newImage.value)
  await run('/api/pdf-more/images/replace', fd, file.value.name.replace(/\.pdf$/i, '_bild.pdf'))
}
</script>
