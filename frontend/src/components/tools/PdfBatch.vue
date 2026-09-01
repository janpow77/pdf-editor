<template>
  <div class="space-y-5">
    <ToolHeader title="Batch-Verarbeitung" description="Eine Operation auf bis zu 50 validierte PDF-Dateien anwenden." @back="$emit('back')" />

    <UiAlert tone="info">Die Ausgabe wird gesammelt als ZIP bereitgestellt. Fehler einzelner Dateien stehen darin in <code>fehler.txt</code><template v-if="operation === 'redact'">, die Fundstellen je Datei in <code>schwaerzungen.txt</code></template>.</UiAlert>

    <UiDropZone :active="dragging" :invalid="Boolean(uploadError)" :accepted="Boolean(items.length)" @drag-active="dragging = $event" @drop="enqueueFiles">
      <input ref="input" type="file" accept=".pdf,application/pdf" multiple class="hidden" @change="onSelect" />
      <p class="font-semibold text-gray-950 dark:text-white">PDF-Dateien hierher ziehen</p>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">oder lokal auswählen; die Reihenfolge bleibt erhalten.</p>
      <UiButton variant="primary" class="mt-4" :disabled="adding" @click="input?.click()">Dateien auswählen</UiButton>
    </UiDropZone>

    <UiAlert v-if="uploadError" tone="danger">{{ uploadError }}</UiAlert>

    <UiPanel v-if="items.length" class="space-y-3">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <strong>{{ items.length }} Datei(en)</strong>
        <UiButton variant="danger" size="sm" @click="clearFiles">Alle entfernen</UiButton>
      </div>
      <ol class="space-y-2">
        <li v-for="(item, index) in items" :key="item.id" class="flex items-center gap-2 rounded-2xl bg-gray-100/80 p-2 dark:bg-white/5">
          <span class="w-7 text-center text-xs font-semibold tabular-nums text-gray-600 dark:text-gray-400">{{ index + 1 }}</span>
          <span class="min-w-0 flex-1 truncate text-sm">{{ item.file.name }}</span>
          <span class="text-xs text-gray-600 dark:text-gray-400">{{ formatFileSize(item.file.size) }}</span>
          <UiIconButton size="sm" :disabled="index === 0" :aria-label="`${item.file.name} nach oben verschieben`" @click="move(index, -1)">↑</UiIconButton>
          <UiIconButton size="sm" :disabled="index === items.length - 1" :aria-label="`${item.file.name} nach unten verschieben`" @click="move(index, 1)">↓</UiIconButton>
          <UiIconButton size="sm" variant="danger" :aria-label="`${item.file.name} entfernen`" @click="remove(item.id)">×</UiIconButton>
        </li>
      </ol>
    </UiPanel>

    <UiPanel v-if="items.length" class="space-y-4">
      <UiField label="Operation" for-id="batch-operation">
        <select id="batch-operation" v-model="operation" class="ui-control w-full" @change="resetResult">
          <option value="compress">Komprimieren</option><option value="rotate">Rotieren</option>
          <option value="protect">Passwortschutz</option><option value="bates">Bates-Nummerierung</option>
          <option value="pdfa">PDF/A</option><option value="watermark">Wasserzeichen</option>
          <option value="clean">Bereinigen</option><option value="sign">Digital signieren</option>
          <option value="rename">Umbenennen</option><option value="redact">Schwärzen</option>
        </select>
      </UiField>

      <UiField v-if="operation === 'compress'" label="Qualität" for-id="batch-quality">
        <select id="batch-quality" v-model="params.quality" class="ui-control w-full sm:w-auto"><option value="low">Maximal</option><option value="medium">Ausgewogen</option><option value="high">Beste Qualität</option></select>
      </UiField>
      <UiField v-else-if="operation === 'rotate'" label="Drehung" for-id="batch-rotation">
        <select id="batch-rotation" v-model.number="params.rotation" class="ui-control w-full sm:w-auto"><option :value="90">90° rechts</option><option :value="180">180°</option><option :value="270">90° links</option></select>
      </UiField>
      <UiField v-else-if="operation === 'protect'" label="Passwort für alle Dateien" for-id="batch-password" required>
        <input id="batch-password" v-model="params.password" type="password" class="ui-control w-full" autocomplete="new-password" />
      </UiField>
      <div v-else-if="operation === 'bates'" class="grid gap-4 sm:grid-cols-3">
        <UiField label="Präfix" for-id="batch-prefix"><input id="batch-prefix" v-model="params.prefix" class="ui-control w-full" /></UiField>
        <UiField label="Startnummer" for-id="batch-start"><input id="batch-start" v-model.number="params.start" type="number" min="0" class="ui-control w-full" /></UiField>
        <UiField label="Stellen" for-id="batch-digits"><input id="batch-digits" v-model.number="params.digits" type="number" min="1" max="12" class="ui-control w-full" /></UiField>
      </div>
      <UiField v-else-if="operation === 'pdfa'" label="PDF/A-Level" for-id="batch-pdfa">
        <select id="batch-pdfa" v-model="params.level" class="ui-control w-full sm:w-auto"><option value="1b">PDF/A-1b</option><option value="2b">PDF/A-2b</option><option value="3b">PDF/A-3b</option></select>
      </UiField>
      <div v-else-if="operation === 'watermark'" class="grid gap-4 sm:grid-cols-3">
        <UiField label="Text" for-id="batch-watermark"><input id="batch-watermark" v-model="params.text" class="ui-control w-full" /></UiField>
        <UiField label="Deckkraft" for-id="batch-opacity"><input id="batch-opacity" v-model.number="params.opacity" type="number" min="0.05" max="1" step="0.05" class="ui-control w-full" /></UiField>
        <UiField label="Schriftgröße" for-id="batch-font"><input id="batch-font" v-model.number="params.font_size" type="number" min="8" max="200" class="ui-control w-full" /></UiField>
      </div>
      <UiAlert v-else-if="operation === 'clean'" tone="info">Metadaten, JavaScript, eingebettete Dateien und versteckte Inhalte werden entfernt.</UiAlert>
      <div v-else-if="operation === 'sign'" class="space-y-4">
        <FileDrop v-model="certificate" accept=".p12,.pfx" label="Zertifikat (.p12/.pfx)" />
        <UiField label="Zertifikats-Passwort" for-id="batch-passphrase"><input id="batch-passphrase" v-model="passphrase" type="password" class="ui-control w-full" autocomplete="new-password" /></UiField>
        <UiField label="Grund (optional)" for-id="batch-reason"><input id="batch-reason" v-model="params.reason" class="ui-control w-full" /></UiField>
      </div>
      <div v-else-if="operation === 'rename'" class="grid gap-4 sm:grid-cols-3">
        <UiField label="Namensmuster" for-id="batch-pattern" hint="Platzhalter: {name} und {n}."><input id="batch-pattern" v-model="params.pattern" class="ui-control w-full" /></UiField>
        <UiField label="Startnummer" for-id="batch-rename-start"><input id="batch-rename-start" v-model.number="params.start" type="number" min="0" class="ui-control w-full" /></UiField>
        <UiField label="Stellen" for-id="batch-rename-digits"><input id="batch-rename-digits" v-model.number="params.rename_digits" type="number" min="1" max="8" class="ui-control w-full" /></UiField>
      </div>
      <div v-else-if="operation === 'redact'" class="space-y-4">
        <UiAlert tone="warning">Schwärzung ist unwiderruflich und wird auf alle Dateien angewendet. Dateien ohne Fundstellen bleiben unverändert im ZIP.</UiAlert>
        <fieldset>
          <div class="mb-2 flex items-center justify-between gap-2">
            <legend class="ui-label">Muster</legend>
            <UiButton size="sm" variant="secondary" @click="selectStandardPatterns">Standardmuster auswählen</UiButton>
          </div>
          <UiAlert v-if="patternLoadError" tone="warning">{{ patternLoadError }}</UiAlert>
          <div class="grid gap-2 sm:grid-cols-2">
            <label v-for="pattern in redactPatterns" :key="pattern.id" class="ui-choice !items-start" :class="{ 'opacity-50': pattern.ai && !nerAvailable }">
              <input
                type="checkbox"
                class="mt-1 rounded"
                :disabled="pattern.ai && !nerAvailable"
                :checked="selectedPatterns.has(pattern.id)"
                @change="toggleRedactPattern(pattern.id)"
              />
              <span>
                {{ pattern.label }}
                <span v-if="pattern.ai" class="ml-1 rounded bg-amber-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900 dark:bg-amber-900/60 dark:text-amber-200">KI</span>
                <span class="block text-xs font-normal text-gray-600 dark:text-gray-300">{{ pattern.hint }}<template v-if="pattern.ai && !nerAvailable"> — auf diesem Server nicht installiert.</template></span>
              </span>
            </label>
          </div>
        </fieldset>
        <UiField label="Begriffe oder Namen" for-id="batch-redact-terms" hint="Ein Begriff pro Zeile.">
          <textarea id="batch-redact-terms" v-model="params.redact_terms" rows="4" class="ui-control w-full font-mono" placeholder="Erika Musterfrau&#10;Musterhausen"></textarea>
        </UiField>
        <div class="flex flex-wrap gap-2">
          <label class="ui-choice"><input v-model="params.case_sensitive" type="checkbox" class="rounded" /> Groß- und Kleinschreibung beachten</label>
          <label class="ui-choice"><input v-model="params.whole_word" type="checkbox" class="rounded" /> Nur ganze Wörter</label>
        </div>
        <label class="ui-choice !rounded-2xl">
          <input v-model="redactConfirmed" type="checkbox" class="rounded" /> Ich bestätige die unwiderrufliche Schwärzung aller Fundstellen in diesen Dateien.
        </label>
      </div>
    </UiPanel>

    <UiAlert v-if="summary" tone="success" live>{{ summary }} – ZIP heruntergeladen.</UiAlert>
    <UiButton v-if="items.length" variant="primary" size="lg" :loading="loading" :disabled="!canRun" @click="apply">
      {{ loading ? `Verarbeite ${items.length} Datei(en)…` : `${items.length} Datei(en) verarbeiten` }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiField from '@/components/ui/UiField.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { apiGetJson, apiPost, downloadBlob } from '@/lib/api'
import { formatFileSize, validatePdfFile, validateTotalFileSize } from '@/lib/fileValidation'

defineEmits<{ (event: 'back'): void }>()

type BatchOperation = 'compress' | 'rotate' | 'protect' | 'bates' | 'pdfa' | 'watermark' | 'clean' | 'sign' | 'rename' | 'redact'
interface BatchItem { id: string; file: File }
interface PatternInfo { id: string; label: string; hint: string; ai: boolean }
interface BatchParams {
  quality: 'low' | 'medium' | 'high'; rotation: 90 | 180 | 270; password: string
  prefix: string; start: number; digits: number; level: '1b' | '2b' | '3b'
  text: string; opacity: number; font_size: number; pattern: string
  rename_digits: number; reason: string
  redact_terms: string; case_sensitive: boolean; whole_word: boolean
}

const MAX_FILES = 50
const notifications = useNotifications()
const input = ref<HTMLInputElement | null>(null)
const items = ref<BatchItem[]>([])
const operation = ref<BatchOperation>('compress')
const params = reactive<BatchParams>({
  quality: 'medium', rotation: 90, password: '', prefix: 'AKTE-', start: 1, digits: 6, level: '2b',
  text: 'ENTWURF', opacity: 0.3, font_size: 60, pattern: 'AKTE-{n}_{name}', rename_digits: 3, reason: '',
  redact_terms: '', case_sensitive: false, whole_word: true,
})
const certificate = ref<File | null>(null)
const passphrase = ref('')
const loading = ref(false)
const adding = ref(false)
const dragging = ref(false)
const uploadError = ref('')
const error = ref<string | null>(null)
const summary = ref('')
const redactPatterns = ref<PatternInfo[]>([])
const selectedPatterns = ref<Set<string>>(new Set())
const nerAvailable = ref(false)
const patternLoadError = ref('')
const redactConfirmed = ref(false)
let nextId = 1
let runGeneration = 0
let addQueue = Promise.resolve()

const canRun = computed(() => {
  if (operation.value === 'protect') return Boolean(params.password)
  if (operation.value === 'sign') return Boolean(certificate.value)
  if (operation.value === 'watermark') return Boolean(params.text.trim())
  if (operation.value === 'rename') return Boolean(params.pattern.trim())
  if (operation.value === 'redact') {
    const hasSelection = selectedPatterns.value.size > 0 || params.redact_terms.trim().length > 0
    return hasSelection && redactConfirmed.value
  }
  return true
})

function selectStandardPatterns(): void {
  selectedPatterns.value = new Set(redactPatterns.value.filter((p) => !p.ai).map((p) => p.id))
  redactConfirmed.value = false
}

function toggleRedactPattern(id: string): void {
  const next = new Set(selectedPatterns.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedPatterns.value = next
  redactConfirmed.value = false
}

onMounted(async () => {
  try {
    const body = await apiGetJson<{ patterns: PatternInfo[]; ner_available: boolean }>('/api/pdf-extras/redact/patterns')
    redactPatterns.value = body.patterns
    nerAvailable.value = body.ner_available
  } catch {
    redactPatterns.value = []
    patternLoadError.value = 'Vordefinierte Muster konnten nicht geladen werden. Eigene Begriffe bleiben verfügbar.'
  }
})

function onSelect(event: Event): void {
  const target = event.target as HTMLInputElement
  const selected = Array.from(target.files ?? [])
  target.value = ''
  enqueueFiles(selected)
}

function enqueueFiles(selected: File[]): void {
  dragging.value = false
  if (!selected.length) return
  addQueue = addQueue.then(() => addFiles(selected))
}

async function addFiles(selected: File[]): Promise<void> {
  adding.value = true
  uploadError.value = ''
  const accepted: File[] = []
  const rejected: string[] = []
  const freeSlots = Math.max(0, MAX_FILES - items.value.length)

  for (const [index, file] of selected.entries()) {
    if (index >= freeSlots) {
      rejected.push(`${file.name}: Maximum von ${MAX_FILES} Dateien erreicht`)
      continue
    }
    const validation = await validatePdfFile(file)
    if (validation.valid) accepted.push(file)
    else rejected.push(`${file.name}: ${validation.message ?? 'ungültige PDF-Datei'}`)
  }

  const combined = [...items.value.map((item) => item.file), ...accepted]
  const total = validateTotalFileSize(combined)
  if (!total.valid) {
    accepted.length = 0
    rejected.push(total.message ?? 'Gesamtgrößenlimit überschritten')
  }

  items.value.push(...accepted.map((file) => ({ id: `batch-${Date.now()}-${nextId++}`, file })))
  if (rejected.length) {
    uploadError.value = rejected.join(' ')
    notifications.warning('Einige Dateien wurden abgelehnt', uploadError.value)
  }
  if (accepted.length) notifications.success('Dateien hinzugefügt', `${accepted.length} PDF-Datei(en) wurden übernommen.`)
  adding.value = false
  resetResult()
}

function remove(id: string): void {
  items.value = items.value.filter((item) => item.id !== id)
  resetResult()
}

function clearFiles(): void {
  items.value = []
  uploadError.value = ''
  resetResult()
}

function move(index: number, direction: -1 | 1): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [item] = items.value.splice(index, 1)
  if (item) items.value.splice(target, 0, item)
  resetResult()
}

function resetResult(): void {
  runGeneration += 1
  summary.value = ''
  error.value = null
  redactConfirmed.value = false
}

async function apply(): Promise<void> {
  if (!items.value.length || !canRun.value || loading.value) return
  const generation = ++runGeneration
  const snapshot = [...items.value]
  loading.value = true
  summary.value = ''
  error.value = null
  try {
    const formData = new FormData()
    snapshot.forEach((item) => formData.append('files', item.file))
    formData.append('operation', operation.value)
    let payload: Record<string, unknown> = { ...params }
    if (operation.value === 'rename') payload = { ...params, digits: params.rename_digits }
    else if (operation.value === 'redact') {
      payload = {
        patterns: [...selectedPatterns.value],
        terms: params.redact_terms,
        case_sensitive: params.case_sensitive,
        whole_word: params.whole_word,
      }
    }
    formData.append('params', JSON.stringify(payload))
    if (operation.value === 'sign' && certificate.value) {
      formData.append('certificate', certificate.value)
      formData.append('passphrase', passphrase.value)
    }
    const response = await apiPost('/api/pdf-extras/batch', formData)
    await downloadBlob(response, 'batch_ergebnisse.zip')
    if (generation !== runGeneration) return
    const ok = response.headers.get('X-Batch-Ok') || '0'
    const failed = response.headers.get('X-Batch-Failed') || '0'
    summary.value = `${ok} erfolgreich, ${failed} fehlgeschlagen`
  } catch (caught: unknown) {
    if (generation === runGeneration) error.value = caught instanceof Error ? caught.message : 'Batch-Verarbeitung fehlgeschlagen.'
  } finally {
    if (generation === runGeneration) loading.value = false
  }
}
</script>
