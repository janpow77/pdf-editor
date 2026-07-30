<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Schwärzen</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Echte Schwärzung: Der gefundene Text wird aus dem Dokumentinhalt <strong>entfernt</strong>
      (nicht nur überdeckt) und schwarz markiert — auch Kopieren/Durchsuchen findet ihn danach
      nicht mehr. Der Schritt ist unumkehrbar; prüfen Sie die Fundstellen vorher in der Vorschau.
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="flex gap-2">
      <button
        v-for="m in modes"
        :key="m.value"
        class="px-3 py-1.5 rounded-lg text-sm border-2 transition-colors"
        :class="mode === m.value
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
          : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300'"
        @click="mode = m.value; preview = null; done = false"
      >
        {{ m.label }}
      </button>
    </div>

    <!-- Einzelbegriff (wie bisher) -->
    <div v-if="file && mode === 'term'" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Zu schwärzender Text</label>
        <input v-model="term" type="text" placeholder="z.B. Name, Aktenzeichen" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="matchCase" type="checkbox" class="rounded" />
        Groß-/Kleinschreibung beachten
      </label>
    </div>

    <!-- Muster + Namensliste -->
    <div v-if="file && mode === 'patterns'" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
      <div>
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">Muster</h3>
        <div class="grid sm:grid-cols-2 gap-x-4 gap-y-1">
          <label
            v-for="p in patterns"
            :key="p.id"
            class="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300"
            :title="p.hint"
          >
            <input
              type="checkbox"
              class="rounded mt-0.5"
              :checked="selectedPatterns.has(p.id)"
              @change="togglePattern(p.id)"
            />
            <span>
              {{ p.label }}
              <span class="block text-xs text-gray-400">{{ p.hint }}</span>
            </span>
          </label>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Begriffe/Namen (einer pro Zeile)
        </label>
        <textarea
          v-model="terms"
          rows="4"
          placeholder="Erika Musterfrau&#10;Musterhausen&#10;Projekt Alpha"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white font-mono"
        ></textarea>
      </div>

      <div class="flex flex-wrap gap-4">
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input v-model="matchCase" type="checkbox" class="rounded" /> Groß-/Kleinschreibung beachten
        </label>
        <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
          <input v-model="wholeWord" type="checkbox" class="rounded" /> Nur ganze Wörter
        </label>
      </div>
    </div>

    <!-- Vorschau der Fundstellen -->
    <div v-if="preview" class="bg-white dark:bg-gray-900 rounded-xl border p-4 space-y-2"
      :class="preview.total ? 'border-amber-300 dark:border-amber-700' : 'border-gray-200 dark:border-gray-700'">
      <h3 class="text-sm font-semibold text-gray-900 dark:text-white">
        {{ preview.total }} Fundstelle(n) — bitte prüfen
      </h3>
      <p v-if="!preview.total" class="text-sm text-gray-500">
        Nichts gefunden. Muster oder Begriffe anpassen.
      </p>
      <template v-else>
        <ul class="text-sm text-gray-700 dark:text-gray-300 max-h-56 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700">
          <li v-for="(f, i) in preview.findings" :key="i" class="py-1 flex justify-between gap-3">
            <span class="font-mono truncate">{{ f.text }}</span>
            <span class="shrink-0 text-xs text-gray-400">{{ patternLabel(f.pattern) }} · S. {{ f.page }}</span>
          </li>
        </ul>
        <p v-if="preview.truncated" class="text-xs text-gray-400">
          Nur die ersten 500 Fundstellen werden aufgelistet — geschwärzt werden alle.
        </p>
      </template>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      {{ redactions }} Stelle(n) geschwärzt, Datei heruntergeladen.
    </div>

    <div v-if="file" class="flex flex-wrap gap-2">
      <button
        v-if="mode === 'patterns'"
        :disabled="loading || !hasSelection"
        class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-primary-400 disabled:opacity-50"
        @click="runPreview"
      >
        {{ loading ? 'Suche…' : 'Fundstellen anzeigen' }}
      </button>
      <button
        :disabled="loading || !canRedact"
        class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        @click="apply"
      >
        {{ loading ? 'Schwärze…' : 'Schwärzen' }}
      </button>
    </div>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'
import { apiGetJson, apiPost } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface PatternInfo {
  id: string
  label: string
  hint: string
}
interface Finding {
  pattern: string
  page: number
  text: string
}
interface Preview {
  total: number
  by_pattern: Record<string, number>
  findings: Finding[]
  truncated: boolean
}

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const mode = ref<'term' | 'patterns'>('term')
const term = ref('')
const terms = ref('')
const matchCase = ref(false)
const wholeWord = ref(true)
const redactions = ref(0)
const patterns = ref<PatternInfo[]>([])
const selectedPatterns = ref<Set<string>>(new Set())
const preview = ref<Preview | null>(null)

const modes = [
  { value: 'term' as const, label: 'Einzelner Begriff' },
  { value: 'patterns' as const, label: 'Muster & Namensliste' },
]

const hasSelection = computed(
  () => selectedPatterns.value.size > 0 || terms.value.trim().length > 0,
)
const canRedact = computed(() =>
  mode.value === 'term' ? term.value.trim().length > 0 : hasSelection.value,
)

function togglePattern(id: string) {
  const next = new Set(selectedPatterns.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedPatterns.value = next
  preview.value = null
}

function patternLabel(id: string): string {
  if (id.startsWith('begriff:')) return `Begriff „${id.slice(8)}"`
  return patterns.value.find((p) => p.id === id)?.label ?? id
}

function patternFormData(): FormData {
  const fd = new FormData()
  fd.append('file', file.value as File)
  fd.append('patterns', JSON.stringify([...selectedPatterns.value]))
  fd.append('terms', terms.value)
  fd.append('case_sensitive', String(matchCase.value))
  fd.append('whole_word', String(wholeWord.value))
  return fd
}

async function runPreview() {
  if (!file.value || !hasSelection.value) return
  loading.value = true
  error.value = null
  preview.value = null
  done.value = false
  try {
    const fd = patternFormData()
    fd.append('preview', 'true')
    const resp = await apiPost('/api/pdf-extras/redact-patterns', fd)
    preview.value = (await resp.json()) as Preview
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Suche fehlgeschlagen'
  } finally {
    loading.value = false
  }
}

async function apply() {
  if (!file.value || !canRedact.value) return
  const target = file.value.name.replace(/\.pdf$/i, '_geschwaerzt.pdf')
  let resp: Response | null
  if (mode.value === 'term') {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('term', term.value)
    fd.append('match_case', String(matchCase.value))
    resp = await run('/api/pdf-extras/redact', fd, target)
  } else {
    resp = await run('/api/pdf-extras/redact-patterns', patternFormData(), target)
  }
  if (resp) {
    redactions.value = Number(resp.headers.get('X-Redactions') || 0)
    preview.value = null
  }
}

onMounted(async () => {
  try {
    const body = await apiGetJson<{ patterns: PatternInfo[] }>('/api/pdf-extras/redact/patterns')
    patterns.value = body.patterns
  } catch {
    patterns.value = []
  }
})
</script>
