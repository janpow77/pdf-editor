<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Batch-Verarbeitung</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Eine Operation auf bis zu 50 PDFs gleichzeitig anwenden — das Ergebnis kommt
      gesammelt als ZIP. Fehler einzelner Dateien werden im ZIP als fehler.txt gelistet.
    </div>

    <!-- Mehrfach-Upload -->
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
        <li v-for="(f, i) in files" :key="i" class="py-1 flex justify-between gap-2">
          <span class="truncate text-gray-700 dark:text-gray-300">{{ f.name }}</span>
          <button class="text-red-500 hover:text-red-700" @click="files.splice(i, 1)">✕</button>
        </li>
      </ul>
    </div>

    <div v-if="files.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Operation</label>
        <select v-model="operation" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="compress">Komprimieren</option>
          <option value="rotate">Rotieren</option>
          <option value="protect">Passwortschutz</option>
          <option value="bates">Bates-Nummerierung (fortlaufend über alle Dateien)</option>
          <option value="pdfa">PDF/A</option>
          <option value="watermark">Wasserzeichen</option>
          <option value="clean">Bereinigen (Metadaten entfernen)</option>
          <option value="sign">Digital signieren (Stapelsignatur)</option>
          <option value="rename">Umbenennen</option>
        </select>
      </div>

      <div v-if="operation === 'compress'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Qualität</label>
        <select v-model="params.quality" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="low">Maximal komprimieren</option>
          <option value="medium">Ausgewogen</option>
          <option value="high">Beste Qualität</option>
        </select>
      </div>
      <div v-else-if="operation === 'rotate'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Drehung</label>
        <select v-model.number="params.rotation" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option :value="90">90° rechts</option>
          <option :value="180">180°</option>
          <option :value="270">90° links</option>
        </select>
      </div>
      <div v-else-if="operation === 'protect'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Passwort (für alle Dateien)</label>
        <input v-model="params.password" type="password" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div v-else-if="operation === 'bates'" class="grid grid-cols-3 gap-3">
        <input v-model="params.prefix" type="text" placeholder="Präfix" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model.number="params.start" type="number" min="0" placeholder="Start" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model.number="params.digits" type="number" min="1" max="12" placeholder="Stellen" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div v-else-if="operation === 'pdfa'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">PDF/A-Level</label>
        <select v-model="params.level" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white">
          <option value="1b">PDF/A-1b</option>
          <option value="2b">PDF/A-2b</option>
          <option value="3b">PDF/A-3b</option>
        </select>
      </div>
      <div v-else-if="operation === 'watermark'" class="grid grid-cols-3 gap-3">
        <input v-model="params.text" type="text" placeholder="Text" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model.number="params.opacity" type="number" min="0.05" max="1" step="0.05" placeholder="Deckkraft" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model.number="params.font_size" type="number" min="8" max="200" placeholder="Schriftgröße" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <p v-else-if="operation === 'clean'" class="text-sm text-gray-500 dark:text-gray-400">
        Entfernt Metadaten, JavaScript, eingebettete Dateien und versteckte Inhalte aus allen Dateien.
      </p>
      <div v-else-if="operation === 'sign'" class="space-y-2">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Zertifikat (.p12/.pfx)</label>
        <input ref="certInput" type="file" accept=".p12,.pfx" class="text-sm text-gray-600 dark:text-gray-300" @change="onCert" />
        <input v-model="passphrase" type="password" placeholder="Zertifikats-Passwort" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model="params.reason" type="text" placeholder="Grund (optional)" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <p class="text-xs text-gray-600 dark:text-gray-400">Zertifikat und Passwort werden nur für diesen Lauf verwendet und nicht gespeichert.</p>
      </div>
      <div v-else-if="operation === 'rename'" class="grid grid-cols-3 gap-3">
        <input v-model="params.pattern" type="text" placeholder="{name} oder AKTE-{n}_{name}" class="col-span-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model.number="params.start" type="number" min="0" placeholder="Startnummer" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model.number="params.rename_digits" type="number" min="1" max="8" placeholder="Stellen" title="Stellen der Nummer" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <p class="col-span-3 text-xs text-gray-600 dark:text-gray-400">Platzhalter: <code>{name}</code> = ursprünglicher Name, <code>{n}</code> = fortlaufende Nummer.</p>
      </div>
    </div>

    <div v-if="summary" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      {{ summary }} — ZIP heruntergeladen.
    </div>

    <button
      v-if="files.length"
      :disabled="loading || (operation === 'protect' && !params.password) || (operation === 'sign' && !certificate)"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? `Verarbeite ${files.length} Datei(en)…` : `${files.length} Datei(en) verarbeiten` }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, run } = useToolRun()
const input = ref<HTMLInputElement | null>(null)
const files = ref<File[]>([])
const operation = ref('compress')
const params = reactive<Record<string, unknown>>({
  quality: 'medium',
  rotation: 90,
  password: '',
  prefix: 'AKTE-',
  start: 1,
  digits: 6,
  level: '2b',
  text: 'ENTWURF',
  opacity: 0.3,
  font_size: 60,
  pattern: 'AKTE-{n}_{name}',
  rename_digits: 3,
  reason: '',
})
const summary = ref('')
const certInput = ref<HTMLInputElement | null>(null)
const certificate = ref<File | null>(null)
const passphrase = ref('')

function onCert(e: Event) {
  certificate.value = (e.target as HTMLInputElement).files?.[0] ?? null
}

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

async function apply() {
  if (!files.value.length) return
  summary.value = ''
  const fd = new FormData()
  for (const f of files.value) fd.append('files', f)
  fd.append('operation', operation.value)
  // Umbenennen hat eine eigene Stellenzahl (Bates nutzt "digits")
  const payload =
    operation.value === 'rename' ? { ...params, digits: params.rename_digits } : { ...params }
  fd.append('params', JSON.stringify(payload))
  if (operation.value === 'sign' && certificate.value) {
    fd.append('certificate', certificate.value)
    fd.append('passphrase', passphrase.value)
  }
  const resp = await run('/api/pdf-extras/batch', fd, 'batch_ergebnisse.zip')
  if (resp) {
    const ok = resp.headers.get('X-Batch-Ok') || '0'
    const failed = resp.headers.get('X-Batch-Failed') || '0'
    summary.value = `${ok} erfolgreich, ${failed} fehlgeschlagen`
  }
}
</script>
