<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Prüfakte erstellen</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Führt mehrere PDFs zu einer Akte zusammen: pro Dokument ein Lesezeichen
      (Dateiname), optional durchgehende Bates-Nummerierung über alle Seiten.
      Die Reihenfolge lässt sich per Pfeiltasten ändern.
    </div>

    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="files.length ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="input" type="file" accept=".pdf" multiple class="hidden" @change="onSelect" />
      <p class="text-gray-500 dark:text-gray-400 mb-2">PDFs hierher ziehen oder</p>
      <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm" @click="input?.click()">Dateien auswählen</button>
      <ul v-if="files.length" class="mt-3 text-sm text-left max-w-md mx-auto divide-y divide-gray-100 dark:divide-gray-700">
        <li v-for="(f, i) in files" :key="i" class="py-1 flex items-center justify-between gap-2">
          <span class="truncate text-gray-700 dark:text-gray-300">{{ i + 1 }}. {{ f.name }}</span>
          <span class="flex gap-1 shrink-0">
            <button :disabled="i === 0" class="text-gray-400 hover:text-primary-600 disabled:opacity-30" @click="move(i, -1)">↑</button>
            <button :disabled="i === files.length - 1" class="text-gray-400 hover:text-primary-600 disabled:opacity-30" @click="move(i, 1)">↓</button>
            <button class="text-red-500 hover:text-red-700" @click="files.splice(i, 1)">✕</button>
          </span>
        </li>
      </ul>
    </div>

    <div v-if="files.length >= 2" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 grid grid-cols-2 gap-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Bates-Präfix (leer = keine Nummerierung)</label>
        <input v-model="batesPrefix" type="text" placeholder="AKTE-" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Stellen</label>
        <input v-model.number="batesDigits" type="number" min="1" max="12" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
    </div>

    <div v-if="summary" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      {{ summary }} — Prüfakte heruntergeladen.
    </div>

    <button
      v-if="files.length >= 2"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Erstelle Akte…' : `Prüfakte aus ${files.length} Dateien erstellen` }}
    </button>
    <p v-else-if="files.length === 1" class="text-sm text-gray-500">Mindestens zwei Dateien erforderlich.</p>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, run } = useToolRun()
const input = ref<HTMLInputElement | null>(null)
const files = ref<File[]>([])
const batesPrefix = ref('')
const batesDigits = ref(6)
const summary = ref('')

function addFiles(list: FileList | File[]) {
  for (const f of Array.from(list)) {
    if (f.name.toLowerCase().endsWith('.pdf') && files.value.length < 50) files.value.push(f)
  }
}
function onSelect(e: Event) {
  const t = e.target as HTMLInputElement
  if (t.files) addFiles(t.files)
  t.value = ''
}
function onDrop(e: DragEvent) {
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files)
}
function move(i: number, dir: number) {
  const j = i + dir
  const arr = files.value
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}

async function apply() {
  if (files.value.length < 2) return
  summary.value = ''
  const fd = new FormData()
  for (const f of files.value) fd.append('files', f)
  fd.append('bates_prefix', batesPrefix.value)
  fd.append('bates_digits', String(batesDigits.value))
  const resp = await run('/api/pdf-more/pruefakte', fd, 'pruefakte.pdf')
  if (resp) {
    const docs = resp.headers.get('X-Documents') || '?'
    const pages = resp.headers.get('X-Pages') || '?'
    summary.value = `${docs} Dokumente, ${pages} Seiten`
  }
}
</script>
