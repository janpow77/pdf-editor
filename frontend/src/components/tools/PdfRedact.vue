<template>
  <div class="space-y-5">
    <ToolHeader title="Schwärzen" description="Sensible Textinhalte unwiderruflich aus dem PDF entfernen." @back="$emit('back')" />

    <UiAlert tone="warning">
      Echte Schwärzung entfernt Fundstellen aus dem Dokumentinhalt – sie können anschließend weder kopiert noch durchsucht werden. Der Vorgang ist nicht umkehrbar.
    </UiAlert>

    <FileDrop v-model="file" />

    <div v-if="file" class="flex flex-wrap gap-2" aria-label="Schwärzungsmethode">
      <UiButton
        v-for="modeOption in modes"
        :key="modeOption.value"
        size="sm"
        :variant="mode === modeOption.value ? 'primary' : 'secondary'"
        :aria-pressed="mode === modeOption.value"
        @click="selectMode(modeOption.value)"
      >{{ modeOption.label }}</UiButton>
    </div>

    <UiPanel v-if="file && mode === 'term'" class="space-y-4">
      <UiField label="Zu schwärzender Text" for-id="redact-term" hint="Zum Beispiel Name, Aktenzeichen oder Anschrift.">
        <input id="redact-term" v-model="term" type="text" class="ui-control w-full" />
      </UiField>
      <label class="ui-choice"><input v-model="matchCase" type="checkbox" class="rounded" /> Groß- und Kleinschreibung beachten</label>
    </UiPanel>

    <UiPanel v-if="file && mode === 'patterns'" class="space-y-5">
      <fieldset>
        <legend class="ui-label">Muster</legend>
        <div class="grid gap-2 sm:grid-cols-2">
          <label v-for="pattern in patterns" :key="pattern.id" class="ui-choice !items-start">
            <input type="checkbox" class="mt-1 rounded" :checked="selectedPatterns.has(pattern.id)" @change="togglePattern(pattern.id)" />
            <span>{{ pattern.label }}<span class="block text-xs font-normal opacity-70">{{ pattern.hint }}</span></span>
          </label>
        </div>
      </fieldset>

      <UiField label="Begriffe oder Namen" for-id="redact-terms" hint="Ein Begriff pro Zeile.">
        <textarea id="redact-terms" v-model="terms" rows="5" class="ui-control w-full font-mono" placeholder="Erika Musterfrau&#10;Musterhausen&#10;Projekt Alpha"></textarea>
      </UiField>

      <div class="flex flex-wrap gap-2">
        <label class="ui-choice"><input v-model="matchCase" type="checkbox" class="rounded" /> Groß- und Kleinschreibung beachten</label>
        <label class="ui-choice"><input v-model="wholeWord" type="checkbox" class="rounded" /> Nur ganze Wörter</label>
      </div>
    </UiPanel>

    <UiAlert v-if="patternLoadError" tone="warning">{{ patternLoadError }}</UiAlert>

    <UiPanel v-if="preview" :tone="preview.total ? 'warning' : 'default'" class="space-y-3">
      <h3 class="font-semibold">{{ preview.total }} Fundstelle(n)</h3>
      <p v-if="!preview.total" class="text-sm opacity-75">Nichts gefunden. Passe Muster oder Begriffe an.</p>
      <template v-else>
        <ul class="max-h-64 divide-y divide-gray-200 overflow-y-auto text-sm dark:divide-gray-700">
          <li v-for="(finding, index) in preview.findings" :key="`${finding.pattern}-${finding.page}-${index}`" class="flex justify-between gap-3 py-2">
            <span class="truncate font-mono">{{ finding.text }}</span>
            <span class="shrink-0 text-xs opacity-70">{{ patternLabel(finding.pattern) }} · S. {{ finding.page }}</span>
          </li>
        </ul>
        <p v-if="preview.truncated" class="text-xs opacity-70">Nur die ersten 500 Fundstellen werden aufgelistet – geschwärzt werden alle.</p>
      </template>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>{{ redactions }} Stelle(n) geschwärzt und Datei heruntergeladen.</UiAlert>

    <label v-if="file && canRedact" class="ui-choice !rounded-2xl">
      <input v-model="confirmed" type="checkbox" class="rounded" /> Ich habe die Suchkriterien beziehungsweise Fundstellen geprüft und bestätige die unwiderrufliche Schwärzung.
    </label>

    <div v-if="file" class="flex flex-wrap gap-2">
      <UiButton v-if="mode === 'patterns'" :loading="loading" :disabled="!hasSelection" @click="runPreview">
        {{ loading ? 'Suche…' : 'Fundstellen anzeigen' }}
      </UiButton>
      <UiButton variant="danger" size="lg" :loading="loading" :disabled="!canRedact || !confirmed" @click="apply">
        {{ loading ? 'Schwärze…' : 'Unwiderruflich schwärzen' }}
      </UiButton>
    </div>

    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useToolRun } from '@/composables/useToolRun'
import { apiGetJson, apiPost } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

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

type RedactMode = 'term' | 'patterns'

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const mode = ref<RedactMode>('term')
const term = ref('')
const terms = ref('')
const matchCase = ref(false)
const wholeWord = ref(true)
const redactions = ref(0)
const patterns = ref<PatternInfo[]>([])
const selectedPatterns = ref<Set<string>>(new Set())
const preview = ref<Preview | null>(null)
const confirmed = ref(false)
const patternLoadError = ref('')

const modes: { value: RedactMode; label: string }[] = [
  { value: 'term', label: 'Einzelner Begriff' },
  { value: 'patterns', label: 'Muster und Namensliste' },
]

const hasSelection = computed(() => selectedPatterns.value.size > 0 || terms.value.trim().length > 0)
const canRedact = computed(() => mode.value === 'term' ? term.value.trim().length > 0 : hasSelection.value)

watch(file, () => {
  preview.value = null
  done.value = false
  redactions.value = 0
  confirmed.value = false
  error.value = null
})

watch([term, terms, matchCase, wholeWord], () => {
  preview.value = null
  confirmed.value = false
})

function selectMode(nextMode: RedactMode): void {
  mode.value = nextMode
  preview.value = null
  done.value = false
  confirmed.value = false
}

function togglePattern(id: string): void {
  const next = new Set(selectedPatterns.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedPatterns.value = next
  preview.value = null
  confirmed.value = false
}

function patternLabel(id: string): string {
  if (id.startsWith('begriff:')) return `Begriff „${id.slice(8)}“`
  return patterns.value.find((pattern) => pattern.id === id)?.label ?? id
}

function patternFormData(currentFile: File): FormData {
  const fd = new FormData()
  fd.append('file', currentFile)
  fd.append('patterns', JSON.stringify([...selectedPatterns.value]))
  fd.append('terms', terms.value)
  fd.append('case_sensitive', String(matchCase.value))
  fd.append('whole_word', String(wholeWord.value))
  return fd
}

async function runPreview(): Promise<void> {
  if (!file.value || !hasSelection.value) return
  loading.value = true
  error.value = null
  preview.value = null
  done.value = false
  confirmed.value = false
  try {
    const fd = patternFormData(file.value)
    fd.append('preview', 'true')
    const response = await apiPost('/api/pdf-extras/redact-patterns', fd)
    preview.value = await response.json() as Preview
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Suche fehlgeschlagen.'
  } finally {
    loading.value = false
  }
}

async function apply(): Promise<void> {
  if (!file.value || !canRedact.value || !confirmed.value) return
  const target = file.value.name.replace(/\.pdf$/i, '_geschwaerzt.pdf')
  let response: Response | null
  if (mode.value === 'term') {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append('term', term.value)
    fd.append('match_case', String(matchCase.value))
    response = await run('/api/pdf-extras/redact', fd, target)
  } else {
    response = await run('/api/pdf-extras/redact-patterns', patternFormData(file.value), target)
  }
  if (response) {
    redactions.value = Number(response.headers.get('X-Redactions') || 0)
    preview.value = null
    confirmed.value = false
  }
}

onMounted(async () => {
  try {
    const body = await apiGetJson<{ patterns: PatternInfo[] }>('/api/pdf-extras/redact/patterns')
    patterns.value = body.patterns
  } catch {
    patterns.value = []
    patternLoadError.value = 'Vordefinierte Muster konnten nicht geladen werden. Eigene Begriffe bleiben verfügbar.'
  }
})
</script>
