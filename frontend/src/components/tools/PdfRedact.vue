<template>
  <div class="space-y-5">
    <ToolHeader title="Schwärzen" description="Sensible Inhalte unwiderruflich aus dem PDF entfernen — erst prüfen, dann schwärzen." @back="$emit('back')" />

    <ol class="flex flex-wrap gap-2 text-xs font-semibold" aria-label="Arbeitsschritte">
      <li v-for="(label, index) in stepLabels" :key="label" class="rounded-full px-3 py-1" :class="index === stepIndex ? 'bg-primary-600 text-white' : index < stepIndex ? 'bg-primary-100 text-primary-800 dark:bg-primary-500/20 dark:text-primary-200' : 'bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-gray-300'" :aria-current="index === stepIndex ? 'step' : undefined">
        {{ index + 1 }}. {{ label }}
      </li>
    </ol>

    <!-- Dateien -->
    <section class="space-y-2" aria-label="Dateien">
      <FileDrop v-if="step === 'criteria'" v-model="incoming" multiple-handler :max-bytes="remainingBytes" :max-bytes-note="remainingNote" :reject-reason="fullReason" label="PDF (auch mehrere)" @multiple="addFiles" />
      <ul v-if="docs.length" class="space-y-1 text-sm">
        <li v-for="(doc, index) in docs" :key="doc.key" class="flex flex-wrap items-center gap-2 rounded-xl bg-gray-100/70 px-3 py-2 dark:bg-white/5">
          <span class="min-w-0 flex-1 break-all font-medium">{{ doc.file.name }}</span>
          <span v-if="doc.plan" class="text-xs tabular-nums opacity-75">{{ countSelected(doc) }} / {{ doc.plan.total }} ausgewählt<template v-if="doc.areas.length"> · {{ doc.areas.length }} Bereich(e)</template></span>
          <span v-if="doc.reviewed" class="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-200">geprüft</span>
          <span v-if="doc.error" class="text-xs text-red-700 dark:text-red-300">{{ doc.error }}</span>
          <UiButton v-if="step === 'review' && doc.plan && index !== active" size="sm" variant="secondary" @click="active = index">Ansehen</UiButton>
          <UiButton size="sm" variant="ghost" :aria-label="`${doc.file.name} entfernen`" :disabled="busy" @click="removeDoc(index)">Entfernen</UiButton>
        </li>
      </ul>
    </section>

    <!-- Suchkriterien -->
    <UiPanel v-if="docs.length && step === 'criteria'" class="space-y-5">
      <fieldset>
        <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
          <legend class="ui-label">Muster</legend>
          <UiButton size="sm" variant="secondary" @click="selectStandardPatterns">Standardmuster auswählen</UiButton>
        </div>
        <div class="grid gap-2 sm:grid-cols-2">
          <label v-for="pattern in patterns" :key="pattern.id" class="ui-choice !items-start" :class="{ 'opacity-50': pattern.ai && !nerAvailable }">
            <input type="checkbox" class="mt-1 rounded" :disabled="pattern.ai && !nerAvailable" :checked="selectedPatterns.has(pattern.id)" @change="togglePattern(pattern.id)" />
            <span>
              {{ pattern.label }}
              <span v-if="pattern.ai" class="ml-1 rounded bg-amber-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-900 dark:bg-amber-900/60 dark:text-amber-200">KI</span>
              <span class="block text-xs font-normal opacity-70">{{ pattern.hint }}<template v-if="pattern.ai && !nerAvailable"> — auf diesem Server nicht installiert.</template></span>
            </span>
          </label>
        </div>
      </fieldset>

      <UiField label="Begriffe oder Namen" for-id="redact-terms" :hint="`Ein Begriff pro Zeile, höchstens ${MAX_TERMS}. Findet auch Treffer über Zeilenumbrüche und Silbentrennung hinweg.`">
        <textarea id="redact-terms" v-model="terms" rows="4" class="ui-control w-full font-mono" placeholder="Erika Musterfrau&#10;Musterhausen&#10;Projekt Alpha"></textarea>
      </UiField>
      <p v-if="termCount > MAX_TERMS" class="text-sm text-red-700 dark:text-red-300">{{ termCount }} Begriffe — bitte auf {{ MAX_TERMS }} kürzen.</p>

      <div class="flex flex-wrap gap-2">
        <label class="ui-choice"><input v-model="matchCase" type="checkbox" class="rounded" /> Groß- und Kleinschreibung beachten</label>
        <label class="ui-choice"><input v-model="wholeWord" type="checkbox" class="rounded" /> Nur ganze Wörter</label>
        <label class="ui-choice" title="Entfernt Metadaten, XMP, Dateianhänge, JavaScript und Vorschaubilder">
          <input v-model="sanitize" type="checkbox" class="rounded" /> Dokument bereinigen (Metadaten, Anhänge, Skripte)
        </label>
      </div>

      <details class="rounded-2xl bg-gray-100/70 p-3 text-sm dark:bg-white/5">
        <summary class="cursor-pointer font-semibold">Wie wird gesucht?</summary>
        <ul class="mt-2 list-disc space-y-1 pl-5 text-gray-600 dark:text-gray-300">
          <li><strong>Begriffe und Muster</strong> sind feste Textsuche ohne KI und ohne Fuzzy-Logik. IBAN, Steuer-ID und Kartennummer zählen nur mit gültiger Prüfziffer, Datumsangaben nur als echtes Kalenderdatum.</li>
          <li><strong>Personennamen (KI)</strong> schätzt ein kleines spaCy-Modell auf unserem Server. Namen können fehlen oder falsch erkannt sein.</li>
          <li>Gesucht wird auch in <strong>Metadaten, Lesezeichen, Kommentaren, Links, Formularfeldern und Anhängen</strong>. Gescannte Seiten ohne Textebene werden gemeldet.</li>
          <li>Nach dem Schwärzen wird die Datei erneut durchsucht. Ist eine ausgewählte Fundstelle noch lesbar, wird <strong>keine Datei ausgeliefert</strong>.</li>
        </ul>
        <p class="mt-2 text-xs text-gray-500 dark:text-gray-400">
          Einzelheiten und rechtliche Einordnung (KI-Verordnung):
          <RouterLink to="/datenschutz" class="font-semibold text-primary-600 underline hover:no-underline dark:text-primary-400">Datenschutzerklärung</RouterLink>.
        </p>
      </details>

      <UiButton variant="primary" :loading="busy && step === 'criteria'" :disabled="!hasCriteria || busy || termCount > MAX_TERMS" @click="searchAll">
        {{ busy && step === 'criteria' ? `Suche … ${progress}` : docs.length > 1 ? `Fundstellen in ${docs.length} Dateien suchen` : 'Fundstellen suchen' }}
      </UiButton>
      <UiButton v-if="plansReady && !busy" variant="secondary" class="ml-2" @click="step = 'review'">Zurück zur Prüfung</UiButton>
      <p v-if="plansReady && !busy" class="text-xs opacity-70">Ihre Auswahl bleibt erhalten, solange Sie Kriterien und Dateien nicht ändern. Eine neue Suche setzt sie zurück.</p>
      <p v-if="!hasCriteria" class="text-xs opacity-70">Mindestens ein Muster oder einen Begriff angeben. Eigene Bereiche können Sie danach in der Seitenansicht ergänzen.</p>
    </UiPanel>

    <UiAlert v-if="patternLoadError" tone="warning">{{ patternLoadError }}</UiAlert>

    <!-- Prüfung -->
    <p v-if="step === 'review'" class="rounded-2xl bg-gray-100/70 px-3 py-2 text-sm dark:bg-white/5">
      <span class="font-semibold">Gesucht nach:</span> {{ criteriaSummary }}
      <button type="button" class="ml-2 font-semibold text-primary-700 underline hover:no-underline dark:text-primary-300" :disabled="busy" @click="backToCriteria">ändern</button>
    </p>
    <template v-if="step === 'review' && activeDoc && activeDoc.plan && activeDoc.blob">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-base font-semibold">
          Prüfen: {{ activeDoc.file.name }}
          <span v-if="docs.length > 1" class="font-normal opacity-70">({{ active + 1 }} von {{ docs.length }})</span>
        </h3>
        <div v-if="docs.length > 1" class="flex gap-1.5">
          <UiButton size="sm" variant="secondary" :disabled="active === 0" @click="active -= 1">← Vorherige Datei</UiButton>
          <UiButton size="sm" variant="secondary" :disabled="active === docs.length - 1" @click="active += 1">Nächste Datei →</UiButton>
        </div>
      </div>

      <RedactReview v-model:selected="activeDoc.selected" v-model:areas="activeDoc.areas" :source="activeDoc.blob" :plan="activeDoc.plan" />

      <label class="ui-choice !rounded-2xl">
        <input v-model="activeDoc.reviewed" type="checkbox" class="rounded" />
        Ich habe die Fundstellen in „{{ activeDoc.file.name }}“ geprüft.
      </label>
    </template>

    <template v-if="step === 'review'">
      <UiAlert v-if="unreviewed.length" tone="info">
        Noch nicht als geprüft markiert: {{ unreviewed.map((d) => d.file.name).join(', ') }}.
      </UiAlert>
      <UiAlert v-if="allReviewed && nothingToDo" tone="warning">Nichts ausgewählt — es gibt nichts zu schwärzen.</UiAlert>

      <label v-if="allReviewed && !nothingToDo" class="ui-choice !rounded-2xl">
        <input v-model="confirmed" type="checkbox" class="rounded" />
        Ich bestätige die unwiderrufliche Schwärzung der ausgewählten Fundstellen und Bereiche<template v-if="docs.length > 1"> in allen {{ docs.length }} Dateien</template>.
      </label>

      <div class="flex flex-wrap gap-2">
        <UiButton variant="danger" size="lg" :loading="busy" :disabled="!allReviewed || nothingToDo || !confirmed || busy" @click="applyAll">
          {{ busy ? 'Schwärze …' : 'Unwiderruflich schwärzen' }}
        </UiButton>
        <UiButton variant="ghost" :disabled="busy" @click="backToCriteria">Suchkriterien ändern</UiButton>
      </div>
    </template>

    <UiAlert v-if="result" tone="success" live>{{ result }}</UiAlert>
    <UiAlert v-if="error" tone="danger" live>{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import FileDrop from '@/components/FileDrop.vue'
import RedactReview from '@/components/tools/RedactReview.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { ApiError, apiGetJson, apiPost, downloadBlob } from '@/lib/api'
import { currentFileLimit, currentTotalLimit, formatFileSize, validatePdfFile, validateTotalFileSize } from '@/lib/fileValidation'
import { takePendingBatchHandoff } from '@/lib/handoff'
import { selectionPayload, type RedactionArea, type RedactionPlan } from '@/lib/redaction'
import type { ToolId } from '@/lib/toolCatalog'

defineEmits<{ (event: 'back'): void; (event: 'switch-tool', id: ToolId): void }>()

interface PatternInfo {
  id: string
  label: string
  hint: string
  ai: boolean
}

interface DocState {
  key: string
  file: File
  blob: Blob | null
  plan: RedactionPlan | null
  selected: Set<string>
  areas: RedactionArea[]
  reviewed: boolean
  error: string
}

const MAX_TERMS = 200
const MAX_FILES = 50
const stepLabels = ['Suchkriterien', 'Fundstellen prüfen', 'Schwärzen']

const notifications = useNotifications()
const incoming = ref<File | null>(null)
const docs = ref<DocState[]>([])
// Platz bis zur Gesamtgrenze: FileDrop lehnt größere Dateien dann selbst ab,
// statt erst „Datei geladen“ zu melden.
const remainingBytes = computed(() =>
  docs.value.length ? Math.max(0, currentTotalLimit() - docs.value.reduce((sum, d) => sum + d.file.size, 0)) : undefined,
)
const remainingNote = computed(() => `noch frei bis zur Gesamtgröße von ${formatFileSize(currentTotalLimit())}`)
const fullReason = computed(() => (docs.value.length >= MAX_FILES ? `Höchstens ${MAX_FILES} Dateien je Durchgang. Bitte zuerst eine Datei entfernen.` : undefined))
const active = ref(0)
const step = ref<'criteria' | 'review'>('criteria')
const patterns = ref<PatternInfo[]>([])
const selectedPatterns = ref<Set<string>>(new Set())
const terms = ref('')
const matchCase = ref(false)
const wholeWord = ref(true)
const sanitize = ref(true)
const confirmed = ref(false)
const busy = ref(false)
const progress = ref('')
const error = ref<string | null>(null)
const result = ref('')
const patternLoadError = ref('')
const nerAvailable = ref(false)
let generation = 0
let controller: AbortController | null = null
let docCounter = 0

const termList = computed(() => [...new Set(terms.value.split('\n').map((t) => t.trim()).filter(Boolean))])
const termCount = computed(() => termList.value.length)
const hasCriteria = computed(() => selectedPatterns.value.size > 0 || termCount.value > 0)
const activeDoc = computed(() => docs.value[active.value] ?? null)
const unreviewed = computed(() => docs.value.filter((d) => d.plan && !d.reviewed))
const allReviewed = computed(() => docs.value.length > 0 && docs.value.every((d) => d.plan && d.reviewed))
const nothingToDo = computed(() => docs.value.every((d) => countSelected(d) === 0 && d.areas.length === 0))
const criteriaSummary = computed(() => {
  const parts = patterns.value.filter((p) => selectedPatterns.value.has(p.id)).map((p) => p.label)
  if (termCount.value) parts.push(`${termCount.value} Begriff(e)`)
  const options = [matchCase.value ? 'Groß-/Kleinschreibung beachtet' : '', wholeWord.value ? 'ganze Wörter' : 'auch Wortteile', sanitize.value ? 'mit Bereinigung' : 'ohne Bereinigung'].filter(Boolean)
  return `${parts.join(', ')} (${options.join(', ')})`
})
const plansReady = computed(() => docs.value.length > 0 && docs.value.every((d) => d.plan))
const stepIndex = computed(() => (step.value === 'criteria' ? 0 : allReviewed.value ? 2 : 1))

function countSelected(doc: DocState): number {
  if (!doc.plan) return 0
  return doc.plan.candidates.reduce((n, c) => n + (doc.selected.has(c.id) ? 1 : 0), 0)
}

/** Jede Änderung an Dateien oder Kriterien macht vorhandene Pläne ungültig. */
function invalidate(): void {
  generation += 1
  controller?.abort()
  controller = null
  busy.value = false
  step.value = 'criteria'
  confirmed.value = false
  result.value = ''
  error.value = null
  for (const doc of docs.value) {
    doc.plan = null
    doc.selected = new Set()
    doc.areas = []
    doc.reviewed = false
    doc.error = ''
  }
}

watch([selectedPatterns, terms, matchCase, wholeWord], invalidate)
watch(sanitize, () => {
  confirmed.value = false
})
watch(active, () => {
  confirmed.value = false
})
// Jede Änderung an Auswahl oder Bereichen verlangt eine neue Bestätigung.
// RedactReview ersetzt Set und Liste bei jeder Änderung, das genügt als Signal.
watch(
  () => docs.value.map((d) => [d.selected, d.areas, d.reviewed]),
  () => {
    confirmed.value = false
  },
)

watch(incoming, (file) => {
  if (!file) return
  incoming.value = null
  const total = validateTotalFileSize([...docs.value.map((d) => d.file), file])
  if (!total.valid) {
    notifications.error('Datei nicht angenommen', total.message ?? 'Gesamtgröße zu hoch')
    return
  }
  pushDocs([file])
})

function pushDocs(files: File[]): void {
  const room = MAX_FILES - docs.value.length
  if (files.length > room) notifications.warning('Zu viele Dateien', `Höchstens ${MAX_FILES} Dateien je Durchgang.`)
  const accepted = files.slice(0, Math.max(0, room))
  // Nur wenn wirklich eine Datei dazukommt, verfallen die bisherigen Pläne.
  if (!accepted.length) return
  invalidate()
  for (const file of accepted) {
    docCounter += 1
    docs.value.push({ key: `${docCounter}-${file.name}`, file, blob: file, plan: null, selected: new Set(), areas: [], reviewed: false, error: '' })
  }
}

async function addFiles(files: File[]): Promise<void> {
  const limit = currentFileLimit()
  const accepted: File[] = []
  for (const file of files) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      notifications.error('Datei nicht angenommen', `${file.name} ist keine PDF-Datei.`)
      continue
    }
    if (file.size > limit) {
      notifications.error('Datei nicht angenommen', `${file.name} ist ${formatFileSize(file.size)} groß. Zulässig sind maximal ${formatFileSize(limit)}.`)
      continue
    }
    const check = await validatePdfFile(file)
    if (!check.valid) {
      notifications.error('Datei nicht angenommen', `${file.name}: ${check.message ?? 'ungültige PDF-Datei'}`)
      continue
    }
    accepted.push(file)
  }
  if (!accepted.length) return
  // Dateien in der gewählten Reihenfolge übernehmen, solange die Gesamtgröße
  // reicht; nur die übrigen ablehnen.
  const totalLimit = currentTotalLimit()
  let used = docs.value.reduce((sum, d) => sum + d.file.size, 0)
  const fitting: File[] = []
  const tooMuch: string[] = []
  for (const file of accepted) {
    if (used + file.size > totalLimit) {
      tooMuch.push(file.name)
      continue
    }
    used += file.size
    fitting.push(file)
  }
  if (tooMuch.length) {
    notifications.error(
      tooMuch.length === 1 ? 'Datei nicht angenommen' : 'Dateien nicht angenommen',
      `${tooMuch.join(', ')}: Die Gesamtgröße von ${formatFileSize(totalLimit)} wäre überschritten.`,
    )
  }
  pushDocs(fitting)
}

function removeDoc(index: number): void {
  docs.value.splice(index, 1)
  // Die angezeigte Datei bleibt dieselbe, wenn eine Datei davor entfernt wird.
  if (index < active.value) active.value -= 1
  if (active.value >= docs.value.length) active.value = Math.max(0, docs.value.length - 1)
  confirmed.value = false
  if (!docs.value.length) invalidate()
}

function selectStandardPatterns(): void {
  selectedPatterns.value = new Set(patterns.value.filter((p) => !p.ai).map((p) => p.id))
}

function togglePattern(id: string): void {
  const next = new Set(selectedPatterns.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedPatterns.value = next
}

/** Zurück zu den Kriterien. Auswahl und Bereiche bleiben, bis sich Kriterien oder Dateien ändern. */
function backToCriteria(): void {
  confirmed.value = false
  step.value = 'criteria'
}

function message(caught: unknown, fallback: string): string {
  return caught instanceof Error ? caught.message : fallback
}

/** Wartet abbrechbar; zeigt dabei die Restzeit im Fortschritt an. */
async function waitFor(seconds: number, signal: AbortSignal, label: string): Promise<void> {
  for (let left = seconds; left > 0; left -= 1) {
    if (signal.aborted) throw new DOMException('Abgebrochen', 'AbortError')
    progress.value = `${label} · Server-Limit erreicht, weiter in ${left} s`
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
}

// Wartezeiten bis hierhin überbrückt die Suche selbst; längere (Tageslimit)
// meldet sie als Fehler.
const MAX_RATE_WAIT_S = 90
const MAX_RATE_RETRIES = 5

async function requestPlan(doc: DocState, signal: AbortSignal, label: string): Promise<RedactionPlan> {
  for (let attempt = 0; ; attempt += 1) {
    const fd = new FormData()
    fd.append('file', doc.file)
    fd.append('patterns', JSON.stringify([...selectedPatterns.value]))
    fd.append('terms', termList.value.join('\n'))
    fd.append('case_sensitive', String(matchCase.value))
    fd.append('whole_word', String(wholeWord.value))
    try {
      const response = await apiPost('/api/pdf-extras/redact/plan', fd, { signal, notifyOnError: false, timeout: 600_000 })
      return (await response.json()) as RedactionPlan
    } catch (caught: unknown) {
      const wait = caught instanceof ApiError && caught.status === 429 ? caught.retryAfter ?? 20 : null
      if (wait === null || wait > MAX_RATE_WAIT_S || attempt >= MAX_RATE_RETRIES) throw caught
      await waitFor(wait, signal, label)
    }
  }
}

/** Sucht Fundstellen für alle Dateien ohne gültigen Plan. Pläne verfallen bei
 *  jeder Änderung an Dateien oder Kriterien; vorhandene bleiben daher gültig,
 *  und ein erneutes Suchen holt nur die fehlenden nach. */
async function searchAll(): Promise<void> {
  if (!hasCriteria.value || busy.value) return
  const currentGeneration = generation
  const requestController = new AbortController()
  controller = requestController
  busy.value = true
  error.value = null
  let failed = 0
  try {
    for (const [index, doc] of docs.value.entries()) {
      if (doc.plan) continue
      const label = docs.value.length > 1 ? `${index + 1}/${docs.value.length}` : ''
      progress.value = label
      doc.error = ''
      try {
        const plan = await requestPlan(doc, requestController.signal, label)
        if (currentGeneration !== generation) return
        doc.plan = plan
        doc.selected = new Set(plan.candidates.filter((c) => c.selected).map((c) => c.id))
      } catch (caught: unknown) {
        if (currentGeneration !== generation || requestController.signal.aborted) return
        failed += 1
        doc.error = message(caught, 'Suche fehlgeschlagen')
      }
    }
    if (failed) {
      error.value = `${failed} Datei(en) konnten nicht durchsucht werden. Erneutes Suchen versucht es nur für diese Dateien; bleibt der Fehler, die Datei entfernen oder ersetzen.`
      return
    }
    active.value = 0
    step.value = 'review'
  } finally {
    if (currentGeneration === generation) {
      busy.value = false
      progress.value = ''
      if (controller === requestController) controller = null
    }
  }
}

function jsonPart(value: unknown): Blob {
  return new Blob([JSON.stringify(value)], { type: 'application/json' })
}

function payloadOf(doc: DocState) {
  return selectionPayload(doc.plan as RedactionPlan, doc.selected, doc.areas, sanitize.value)
}

async function applyAll(): Promise<void> {
  if (!allReviewed.value || nothingToDo.value || !confirmed.value || busy.value) return
  const currentGeneration = generation
  const requestController = new AbortController()
  controller = requestController
  busy.value = true
  error.value = null
  result.value = ''
  try {
    let response: Response
    if (docs.value.length === 1) {
      const doc = docs.value[0]
      const fd = new FormData()
      fd.append('file', doc.file)
      // Als Datei-Teil: Formularfelder sind serverseitig auf 1 MB begrenzt.
      fd.append('plan_file', jsonPart(payloadOf(doc)), 'plan.json')
      response = await apiPost('/api/pdf-extras/redact/apply', fd, { signal: requestController.signal, notifyOnError: false, timeout: 600_000 })
      if (currentGeneration !== generation) return
      await downloadBlob(response, doc.file.name.replace(/\.pdf$/i, '') + '_geschwaerzt.pdf')
      const count = Number(response.headers.get('X-Redactions') || 0)
      const areas = Number(response.headers.get('X-Redaction-Areas') || 0)
      const hidden = Number(response.headers.get('X-Redaction-Hidden') || 0)
      result.value = `${count} Fundstelle(n)${areas ? ` und ${areas} Bereich(e)` : ''} geschwärzt${hidden ? `, davon ${hidden} außerhalb des Seitentexts` : ''}. Nachprüfung bestanden, Datei heruntergeladen.`
    } else {
      const fd = new FormData()
      for (const doc of docs.value) fd.append('files', doc.file)
      fd.append('plans_file', jsonPart(docs.value.map(payloadOf)), 'plans.json')
      response = await apiPost('/api/pdf-extras/redact/apply-batch', fd, { signal: requestController.signal, notifyOnError: false, timeout: 900_000 })
      if (currentGeneration !== generation) return
      await downloadBlob(response, 'geschwaerzt.zip')
      result.value = `${docs.value.length} Dateien verarbeitet und nachgeprüft. ZIP mit Protokoll schwaerzungen.txt heruntergeladen.`
    }
    confirmed.value = false
  } catch (caught: unknown) {
    if (currentGeneration !== generation || requestController.signal.aborted) return
    let text = message(caught, 'Schwärzung fehlgeschlagen')
    if (/neu suchen|anderen Datei/i.test(text)) {
      // Pläne verwerfen, damit das nächste Suchen alle Fundstellen neu ermittelt.
      invalidate()
      text += ' Die Fundstellen werden beim nächsten Suchen neu ermittelt.'
    }
    error.value = text
    notifications.error('Schwärzung nicht ausgeliefert', text)
  } finally {
    if (currentGeneration === generation) {
      busy.value = false
      if (controller === requestController) controller = null
    }
  }
}

onMounted(async () => {
  const handoff = takePendingBatchHandoff()
  if (handoff?.length) void addFiles(handoff)
  try {
    const body = await apiGetJson<{ patterns: PatternInfo[]; ner_available: boolean }>('/api/pdf-extras/redact/patterns')
    patterns.value = body.patterns
    nerAvailable.value = body.ner_available
  } catch {
    patterns.value = []
    patternLoadError.value = 'Vordefinierte Muster konnten nicht geladen werden. Eigene Begriffe bleiben verfügbar.'
  }
})

onBeforeUnmount(() => {
  generation += 1
  controller?.abort()
})
</script>
