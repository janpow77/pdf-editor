<template>
  <div class="space-y-5">
    <ToolHeader title="Formular-Designer" description="Interaktive PDF-Felder visuell oder vollständig per Tastatur anlegen und konfigurieren." @back="$emit('back')" />

    <template v-if="!workingBlob">
      <FileDrop v-model="file" />
      <div class="flex items-center justify-center gap-3 text-sm text-gray-500 dark:text-gray-400">
        <span aria-hidden="true" class="h-px w-16 bg-gray-300/70 dark:bg-gray-600/70" /> oder
        <span aria-hidden="true" class="h-px w-16 bg-gray-300/70 dark:bg-gray-600/70" />
      </div>
      <div class="flex flex-wrap justify-center gap-2">
        <UiButton variant="secondary" @click="startBlank('hoch')">📄 Leeres Formular (A4 hoch)</UiButton>
        <UiButton variant="secondary" @click="startBlank('quer')">📃 Leeres Formular (A4 quer)</UiButton>
      </div>
    </template>

    <template v-else>
      <WorkSessionBar tool="form-designer" :blob="workingBlob" :name="workingName" :state="sessionState" :change-count="fields.length" @restore="restoreSession" />

      <UiPanel padding="sm" class="flex flex-wrap items-center gap-2">
        <UiIconButton :disabled="page <= 1" aria-label="Vorherige Seite" @click="page--">←</UiIconButton>
        <span class="rounded-full bg-gray-100 px-3 py-2 text-sm font-semibold tabular-nums dark:bg-white/10">Seite {{ page }} / {{ pageCount }}</span>
        <UiIconButton :disabled="page >= pageCount" aria-label="Nächste Seite" @click="page++">→</UiIconButton>
        <span class="mx-1 h-7 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>

        <div class="flex flex-wrap gap-1" role="group" aria-label="Feldtyp wählen">
          <UiButton v-for="type in fieldTypes" :key="type.value" size="sm" :variant="activeType === type.value ? 'primary' : 'secondary'" :aria-pressed="activeType === type.value" @click="activeType = type.value">
            <span aria-hidden="true">{{ type.icon }}</span> {{ type.label }}
          </UiButton>
        </div>
        <UiButton variant="primary" size="sm" :disabled="fields.length >= MAX_FIELDS" @click="addDefaultField">Feld per Tastatur anlegen</UiButton>

        <span class="flex-1"></span>
        <UiButton size="sm" :loading="busy" @click="importFromPdf">Vorhandene Felder übernehmen</UiButton>
        <UiButton size="sm" :disabled="!fields.length" @click="saveLayoutFile">Layout speichern</UiButton>
        <UiButton size="sm" @click="layoutInput?.click()">Layout laden</UiButton>
        <input ref="layoutInput" type="file" accept=".json,application/json" class="hidden" @change="onLayoutFile" />
        <UiButton variant="danger" size="sm" :disabled="!fields.length" @click="clearAll">Alle Felder löschen</UiButton>
        <UiButton variant="danger" size="sm" @click="reset">Neues Dokument</UiButton>
      </UiPanel>

      <UiAlert v-if="restoredHint" tone="info">{{ restoredHint }}</UiAlert>

      <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr),24rem]">
        <div>
          <PdfViewer v-model="page" :source="workingBlob" @loaded="onDocumentLoaded" @rendered="measure">
            <template #overlay>
              <div
                ref="canvasBox"
                class="absolute inset-0 touch-none cursor-crosshair"
                tabindex="0"
                role="region"
                aria-label="Formularzeichenfläche. Feldtyp wählen und Enter drücken oder mit Zeiger ein Rechteck aufziehen."
                @keydown.enter.prevent="addDefaultField"
                @pointerdown="onPointerDown"
                @pointermove="onPointerMove"
                @pointerup="onPointerUp"
                @pointercancel="cancelDrawing"
              >
                <svg class="absolute inset-0 h-full w-full" aria-hidden="true">
                  <g v-for="field in pageFields" :key="field.id" @pointerdown.stop.prevent="selectField(field.id)">
                    <rect
                      :x="px(field.x0)" :y="py(field.y0)"
                      :width="pw(field.x1 - field.x0)" :height="ph(field.y1 - field.y0)"
                      :fill="field.id === selectedId ? 'rgba(0,113,227,0.20)' : 'rgba(0,113,227,0.08)'"
                      :stroke="field.id === selectedId ? '#0071e3' : '#5b8fc9'"
                      :stroke-width="field.id === selectedId ? 2 : 1"
                    />
                    <text :x="px(field.x0) + 4" :y="py(field.y0) + 13" font-size="11" fill="#0a3f75">{{ typeIcon(field.type) }} {{ field.name }}{{ field.required ? ' *' : '' }}</text>
                  </g>
                  <rect v-if="draft" :x="px(Math.min(draft.x0, draft.x1))" :y="py(Math.min(draft.y0, draft.y1))" :width="pw(Math.abs(draft.x1 - draft.x0))" :height="ph(Math.abs(draft.y1 - draft.y0))" fill="none" stroke="#0071e3" stroke-dasharray="4" stroke-width="2" />
                </svg>
              </div>
            </template>
          </PdfViewer>
        </div>

        <div class="space-y-4">
          <UiPanel v-if="selected" class="space-y-4">
            <div class="flex items-center justify-between gap-2"><h3 class="font-semibold">Feld-Eigenschaften</h3><span class="text-xs text-gray-600 dark:text-gray-400">Seite {{ selected.page }}</span></div>
            <UiField label="Feldname" :for-id="`designer-name-${selected.id}`" :error="selectedNameError">
              <input :id="`designer-name-${selected.id}`" v-model="selected.name" type="text" maxlength="120" class="ui-control w-full" />
            </UiField>
            <UiField label="Typ" :for-id="`designer-type-${selected.id}`">
              <select :id="`designer-type-${selected.id}`" v-model="selected.type" class="ui-control w-full"><option v-for="type in fieldTypes" :key="type.value" :value="type.value">{{ type.label }}</option></select>
            </UiField>
            <UiField label="Hilfetext" :for-id="`designer-tooltip-${selected.id}`"><input :id="`designer-tooltip-${selected.id}`" v-model="selected.tooltip" maxlength="500" class="ui-control w-full" /></UiField>
            <UiField v-if="selected.type === 'dropdown' || selected.type === 'listbox'" label="Auswahlwerte" :for-id="`designer-options-${selected.id}`" hint="Mit Komma trennen."><input :id="`designer-options-${selected.id}`" v-model="selected.options" class="ui-control w-full" /></UiField>
            <label v-if="selected.type === 'checkbox'" class="ui-choice"><input v-model="selected.checked" type="checkbox" class="rounded" /> Vorbelegt angekreuzt</label>
            <UiField v-else-if="selected.type !== 'signature'" label="Vorbelegter Wert" :for-id="`designer-value-${selected.id}`"><input :id="`designer-value-${selected.id}`" v-model="selected.value" class="ui-control w-full" /></UiField>
            <UiField v-if="selected.type !== 'signature' && selected.type !== 'checkbox'" label="Schriftgröße" :for-id="`designer-font-${selected.id}`"><input :id="`designer-font-${selected.id}`" v-model.number="selected.font_size" type="number" min="4" max="72" step="0.5" class="ui-control w-32" /></UiField>

            <fieldset>
              <legend class="ui-label">Position und Größe in Prozent</legend>
              <div class="grid grid-cols-2 gap-3">
                <UiField label="X" :for-id="`designer-x-${selected.id}`"><input :id="`designer-x-${selected.id}`" :value="geometryValue(selected, 'x')" type="number" min="0" max="99" step="0.5" class="ui-control w-full" @input="setGeometry(selected, 'x', $event)" /></UiField>
                <UiField label="Y" :for-id="`designer-y-${selected.id}`"><input :id="`designer-y-${selected.id}`" :value="geometryValue(selected, 'y')" type="number" min="0" max="99" step="0.5" class="ui-control w-full" @input="setGeometry(selected, 'y', $event)" /></UiField>
                <UiField label="Breite" :for-id="`designer-width-${selected.id}`"><input :id="`designer-width-${selected.id}`" :value="geometryValue(selected, 'width')" type="number" min="1" max="100" step="0.5" class="ui-control w-full" @input="setGeometry(selected, 'width', $event)" /></UiField>
                <UiField label="Höhe" :for-id="`designer-height-${selected.id}`"><input :id="`designer-height-${selected.id}`" :value="geometryValue(selected, 'height')" type="number" min="1" max="100" step="0.5" class="ui-control w-full" @input="setGeometry(selected, 'height', $event)" /></UiField>
              </div>
            </fieldset>

            <div class="flex flex-wrap gap-2"><label class="ui-choice"><input v-model="selected.required" type="checkbox" class="rounded" /> Pflichtfeld</label><label class="ui-choice"><input v-model="selected.readonly" type="checkbox" class="rounded" /> Nur lesbar</label></div>

            <details v-if="selected.type === 'text' || selected.type === 'textarea'" class="rounded-2xl bg-gray-100/70 p-3 dark:bg-white/5">
              <summary class="cursor-pointer font-semibold">Berechnung, Format und Wertebereich</summary>
              <div class="mt-4 space-y-4">
                <div class="grid grid-cols-2 gap-3">
                  <UiField label="Zahlenformat" :for-id="`designer-format-${selected.id}`"><select :id="`designer-format-${selected.id}`" v-model="selected.format_kind" class="ui-control w-full"><option value="none">kein Format</option><option value="number">Zahl</option><option value="currency">Währung</option><option value="percent">Prozent</option></select></UiField>
                  <UiField label="Nachkommastellen" :for-id="`designer-decimals-${selected.id}`"><input :id="`designer-decimals-${selected.id}`" v-model.number="selected.format_decimals" type="number" min="0" max="6" class="ui-control w-full" /></UiField>
                </div>
                <UiField v-if="selected.format_kind === 'currency'" label="Währung" :for-id="`designer-currency-${selected.id}`"><input :id="`designer-currency-${selected.id}`" v-model="selected.format_currency" maxlength="8" class="ui-control w-32" /></UiField>
                <UiField label="Berechnung" :for-id="`designer-calc-${selected.id}`"><select :id="`designer-calc-${selected.id}`" v-model="selected.calc_kind" class="ui-control w-full"><option value="none">keine</option><option value="sum">Summe</option><option value="product">Produkt</option><option value="average">Mittelwert</option><option value="min">Minimum</option><option value="max">Maximum</option><option value="formula">Formel</option></select></UiField>
                <UiField v-if="selected.calc_kind === 'formula'" label="Formel" :for-id="`designer-formula-${selected.id}`"><input :id="`designer-formula-${selected.id}`" v-model="selected.calc_formula" class="ui-control w-full" /></UiField>
                <UiField v-else-if="selected.calc_kind !== 'none'" label="Quellfelder" :for-id="`designer-sources-${selected.id}`" hint="Feldnamen mit Komma trennen."><input :id="`designer-sources-${selected.id}`" v-model="selected.calc_fields" class="ui-control w-full" /></UiField>
                <label v-if="selected.calc_kind !== 'none'" class="ui-choice"><input v-model="selected.calc_readonly" type="checkbox" class="rounded" /> Ergebnis schreibgeschützt</label>
                <div class="grid grid-cols-2 gap-3"><UiField label="Minimum" :for-id="`designer-min-${selected.id}`"><input :id="`designer-min-${selected.id}`" v-model="selected.validate_min" type="number" class="ui-control w-full" /></UiField><UiField label="Maximum" :for-id="`designer-max-${selected.id}`"><input :id="`designer-max-${selected.id}`" v-model="selected.validate_max" type="number" class="ui-control w-full" /></UiField></div>
              </div>
            </details>

            <div class="flex gap-2"><UiButton size="sm" @click="duplicateSelected">Duplizieren</UiButton><UiButton variant="danger" size="sm" @click="removeSelected">Feld löschen</UiButton></div>
          </UiPanel>

          <UiAlert v-else tone="info">Kein Feld ausgewählt. Feldtyp wählen und auf der Zeichenfläche ziehen oder „Feld per Tastatur anlegen“ verwenden.</UiAlert>

          <UiPanel v-if="fields.length" class="space-y-2">
            <h3 class="font-semibold">Felder ({{ fields.length }})</h3>
            <ul class="max-h-72 space-y-1 overflow-y-auto">
              <li v-for="field in fields" :key="field.id">
                <button type="button" class="flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-sm transition hover:bg-black/5 dark:hover:bg-white/10" :class="field.id === selectedId ? 'bg-primary-50 font-semibold text-primary-700 dark:bg-primary-500/15 dark:text-primary-300' : ''" @click="jumpTo(field)">
                  <span class="truncate">{{ typeIcon(field.type) }} {{ field.name }}</span><span class="shrink-0 text-xs opacity-70">S. {{ field.page }}</span>
                </button>
              </li>
            </ul>
          </UiPanel>
        </div>
      </div>

      <UiAlert v-if="checkResult" :tone="checkResult.warnings.length ? 'warning' : 'success'">
        {{ checkResult.created }} Feld(er) werden angelegt, {{ checkResult.skipped }} übersprungen.
        <ul v-if="checkResult.warnings.length" class="mt-2 list-disc space-y-1 pl-5"><li v-for="(warning, index) in checkResult.warnings" :key="`${index}-${warning}`">{{ warning }}</li></ul>
      </UiAlert>
      <UiAlert v-if="summary" tone="success" live>{{ summary }}</UiAlert>
      <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>

      <div class="flex flex-wrap gap-2">
        <UiButton :loading="busy" :disabled="!fields.length" @click="check">Felder prüfen</UiButton>
        <UiButton variant="primary" size="lg" :loading="busy" :disabled="!fields.length || nameConflict" @click="generate">PDF mit {{ fields.length }} Feld(ern) erzeugen</UiButton>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import WorkSessionBar from '@/components/WorkSessionBar.vue'
import { apiPost, downloadBlob } from '@/lib/api'
import { createBlankA4Pdf } from '@/lib/pdfFactory'
import { readStoredValue, removeStoredValue, writeStoredValue } from '@/lib/safeStorage'

const PdfViewer = defineAsyncComponent(() => import('@/components/PdfViewer.vue'))
defineEmits<{ (event: 'back'): void }>()

type FieldType = 'text' | 'textarea' | 'checkbox' | 'dropdown' | 'listbox' | 'signature'
type FormatKind = 'none' | 'number' | 'currency' | 'percent'
type CalcKind = 'none' | 'sum' | 'product' | 'average' | 'min' | 'max' | 'formula'
interface DesignerField {
  id: number; page: number; type: FieldType; name: string; value: string; checked: boolean
  options: string; font_size: number; required: boolean; readonly: boolean; tooltip: string
  x0: number; y0: number; x1: number; y1: number
  format_kind: FormatKind; format_decimals: number; format_currency: string
  calc_kind: CalcKind; calc_fields: string; calc_formula: string; calc_readonly: boolean
  validate_min: string; validate_max: string
}
interface CheckResult { created: number; skipped: number; warnings: string[] }
interface Draft { x0: number; y0: number; x1: number; y1: number }

const LAYOUT_KEY = 'pdfapp_form_layout'
const MAX_FIELDS = 200
const MAX_LAYOUT_BYTES = 5 * 1024 * 1024
const DEFAULT_FIELD = { value: 'text' as const, label: 'Textfeld', icon: '▭', w: .35, h: .04 }
const fieldTypes: { value: FieldType; label: string; icon: string; w: number; h: number }[] = [
  DEFAULT_FIELD,
  { value: 'textarea', label: 'Mehrzeilig', icon: '▤', w: .5, h: .1 },
  { value: 'checkbox', label: 'Kontrollkästchen', icon: '☑', w: .04, h: .035 },
  { value: 'dropdown', label: 'Auswahl', icon: '▾', w: .3, h: .04 },
  { value: 'listbox', label: 'Liste', icon: '☰', w: .3, h: .1 },
  { value: 'signature', label: 'Signaturfeld', icon: '✍️', w: .35, h: .07 },
]

const file = ref<File | null>(null)
const workingBlob = ref<Blob | null>(null)
const workingName = ref('dokument.pdf')
const page = ref(1)
const pageCount = ref(1)
const busy = ref(false)
const error = ref<string | null>(null)
const summary = ref('')
const restoredHint = ref('')
const activeType = ref<FieldType>('text')
const fields = ref<DesignerField[]>([])
const selectedId = ref<number | null>(null)
const canvasBox = ref<HTMLElement | null>(null)
const layoutInput = ref<HTMLInputElement | null>(null)
const draft = ref<Draft | null>(null)
const boxSize = ref({ w: 1, h: 1 })
const checkResult = ref<CheckResult | null>(null)
let nextId = 1
let documentGeneration = 0
let drawingPointer: number | null = null
let resizeObserver: ResizeObserver | null = null
let ignoreNextFileReset = false

const pageFields = computed(() => fields.value.filter((field) => field.page === page.value))
const selected = computed(() => fields.value.find((field) => field.id === selectedId.value) ?? null)
const nameConflict = computed(() => fields.value.some((field, index) => !field.name.trim() || fields.value.findIndex((other) => other.name.trim() === field.name.trim()) !== index))
const selectedNameError = computed(() => {
  const current = selected.value
  if (!current) return ''
  if (!current.name.trim()) return 'Der Feldname darf nicht leer sein.'
  return fields.value.some((field) => field.id !== current.id && field.name.trim() === current.name.trim()) ? 'Der Feldname wird bereits verwendet.' : ''
})
const sessionState = computed(() => ({ fields: fields.value, page: page.value }))

function typeIcon(type: FieldType): string { return fieldTypes.find((item) => item.value === type)?.icon ?? '▭' }
function round4(value: number): number { return Math.round(value * 10000) / 10000 }
function clamp(value: number, min = 0, max = 1): number { return Number.isFinite(value) ? Math.max(min, Math.min(max, value)) : min }
function uniqueName(base: string, ignoredId?: number): string { let candidate = base || 'feld'; let suffix = 2; while (fields.value.some((field) => field.id !== ignoredId && field.name === candidate)) candidate = `${base || 'feld'}_${suffix++}`; return candidate }

function createField(type: FieldType, pageNumber: number, x0: number, y0: number, x1?: number, y1?: number): DesignerField {
  const preset = fieldTypes.find((item) => item.value === type) ?? DEFAULT_FIELD
  const base = type === 'signature' ? 'unterschrift' : 'feld'
  const name = uniqueName(`${base}_${fields.value.length + 1}`)
  const endX = clamp(x1 ?? x0 + preset.w, .01, 1); const endY = clamp(y1 ?? y0 + preset.h, .01, 1)
  return { id: nextId++, page: Math.max(1, pageNumber), type, name, value: '', checked: false, options: type === 'dropdown' || type === 'listbox' ? 'Option A, Option B' : '', font_size: 11, required: false, readonly: false, tooltip: '', x0: round4(clamp(Math.min(x0, endX), 0, .99)), y0: round4(clamp(Math.min(y0, endY), 0, .99)), x1: round4(clamp(Math.max(x0, endX), .01, 1)), y1: round4(clamp(Math.max(y0, endY), .01, 1)), format_kind: 'none', format_decimals: 2, format_currency: 'EUR', calc_kind: 'none', calc_fields: '', calc_formula: '', calc_readonly: true, validate_min: '', validate_max: '' }
}

function addDefaultField(): void { if (fields.value.length >= MAX_FIELDS) { error.value = `Maximal ${MAX_FIELDS} Felder pro Dokument.`; return } const offset = (fields.value.filter((field) => field.page === page.value).length % 8) * .045; const field = createField(activeType.value, page.value, .08 + offset, .08 + offset); fields.value.push(field); selectedId.value = field.id; restoredHint.value = ''; checkResult.value = null }

function normalizeField(value: unknown): DesignerField | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>; const type = String(raw.designer_type ?? raw.type ?? 'text') as FieldType
  if (!fieldTypes.some((item) => item.value === type)) return null
  const number = (item: unknown, fallback: number) => Number.isFinite(Number(item)) ? Number(item) : fallback
  const x0 = clamp(number(raw.x0, .1), 0, .99); const y0 = clamp(number(raw.y0, .1), 0, .99); const x1 = clamp(number(raw.x1, .4), x0 + .005, 1); const y1 = clamp(number(raw.y1, .15), y0 + .005, 1)
  const options = Array.isArray(raw.options) ? raw.options.map(String).join(', ') : String(raw.options ?? '')
  return { ...createField(type, Math.max(1, Math.trunc(number(raw.page, 1))), x0, y0, x1, y1), name: String(raw.name ?? '').slice(0, 120) || uniqueName('feld'), value: type === 'checkbox' ? '' : String(raw.value ?? ''), checked: type === 'checkbox' && String(raw.value ?? raw.checked) !== 'Off' && Boolean(raw.value ?? raw.checked), options, font_size: clamp(number(raw.font_size, 11), 4, 72), required: Boolean(raw.required), readonly: Boolean(raw.readonly), tooltip: String(raw.tooltip ?? '').slice(0, 500), format_kind: ['number', 'currency', 'percent'].includes(String(raw.format_kind)) ? String(raw.format_kind) as FormatKind : 'none', format_decimals: clamp(Math.trunc(number(raw.format_decimals, 2)), 0, 6), format_currency: String(raw.format_currency ?? 'EUR').slice(0, 8), calc_kind: ['sum', 'product', 'average', 'min', 'max', 'formula'].includes(String(raw.calc_kind)) ? String(raw.calc_kind) as CalcKind : 'none', calc_fields: Array.isArray(raw.calc_fields) ? raw.calc_fields.map(String).join(', ') : String(raw.calc_fields ?? ''), calc_formula: String(raw.calc_formula ?? ''), calc_readonly: raw.calc_readonly === undefined ? true : Boolean(raw.calc_readonly), validate_min: raw.validate_min == null ? '' : String(raw.validate_min), validate_max: raw.validate_max == null ? '' : String(raw.validate_max) }
}

function loadFieldArray(values: unknown[], keepPageLimit = true): number { const loaded: DesignerField[] = []; for (const value of values.slice(0, MAX_FIELDS)) { const field = normalizeField(value); if (!field) continue; field.name = uniqueName(field.name, field.id); if (keepPageLimit) field.page = Math.min(Math.max(1, field.page), pageCount.value); loaded.push(field) } fields.value = loaded; selectedId.value = loaded[0]?.id ?? null; return loaded.length }
function serializedField(field: DesignerField): Omit<DesignerField, 'id'> { const { id, ...rest } = field; void id; return rest }
function serializeLayout(): object { return { version: 1, app: 'pdf-editor-formular', document: workingName.value, created: new Date().toISOString(), fields: fields.value.map(serializedField) } }

watch(fields, () => { if (!workingBlob.value || !fields.value.length) { removeStoredValue(LAYOUT_KEY); return } try { writeStoredValue(LAYOUT_KEY, JSON.stringify(serializeLayout())) } catch { /* Editor bleibt ohne Persistenz nutzbar. */ } }, { deep: true })
watch(file, (currentFile) => { if (ignoreNextFileReset) { ignoreNextFileReset = false; return } documentGeneration += 1; clearEditorState(); if (!currentFile) { workingBlob.value = null; return } workingBlob.value = currentFile; workingName.value = currentFile.name; restoreMatchingLayout() })
watch(canvasBox, (element) => { resizeObserver?.disconnect(); resizeObserver = null; if (!element || typeof ResizeObserver === 'undefined') return; resizeObserver = new ResizeObserver(measure); resizeObserver.observe(element); void nextTick(measure) })

function clearEditorState(): void { fields.value = []; selectedId.value = null; page.value = 1; pageCount.value = 1; error.value = null; summary.value = ''; restoredHint.value = ''; checkResult.value = null; draft.value = null; drawingPointer = null }
// Ohne Vorlage: das leere A4 kommt aus lib/pdfFactory (eine Quelle für alle
// Leerstarts, bytegenaue xref-Offsets). „Von Grund auf" heißt bewusst ohne
// automatisch restauriertes Alt-Layout; der watch(file)-Pfad übernimmt
// Generationszähler und Editor-Reset.
function startBlank(orientation: 'hoch' | 'quer'): void {
  removeStoredValue(LAYOUT_KEY)
  const name = orientation === 'hoch' ? 'Leeres-Formular-A4.pdf' : 'Leeres-Formular-A4-quer.pdf'
  file.value = new File([createBlankA4Pdf(orientation)], name, { type: 'application/pdf' })
}

function restoreMatchingLayout(): void { const stored = readStoredValue(LAYOUT_KEY); if (!stored || new TextEncoder().encode(stored).byteLength > MAX_LAYOUT_BYTES) return; try { const parsed = JSON.parse(stored) as { document?: string; fields?: unknown[] }; if (parsed.document !== workingName.value || !Array.isArray(parsed.fields)) return; const count = loadFieldArray(parsed.fields, false); if (count) restoredHint.value = `Zuletzt gespeichertes Layout mit ${count} Feld(ern) wiederhergestellt.` } catch { removeStoredValue(LAYOUT_KEY) } }
function restoreSession(payload: { name: string; blob: Blob; state: unknown }): void { documentGeneration += 1; if (file.value) { ignoreNextFileReset = true; file.value = null } workingBlob.value = payload.blob; workingName.value = payload.name; clearEditorState(); const state = payload.state && typeof payload.state === 'object' ? payload.state as { fields?: unknown[]; page?: number } : null; if (state?.fields) loadFieldArray(state.fields, false); page.value = Math.max(1, Math.trunc(Number(state?.page) || 1)) }

function onDocumentLoaded(count: number): void { pageCount.value = Math.max(1, count); page.value = Math.min(page.value, pageCount.value); fields.value.forEach((field) => { field.page = Math.min(field.page, pageCount.value) }) }
function measure(): void { if (canvasBox.value) boxSize.value = { w: Math.max(1, canvasBox.value.clientWidth), h: Math.max(1, canvasBox.value.clientHeight) } }
function px(value: number): number { return value * boxSize.value.w }
function py(value: number): number { return value * boxSize.value.h }
function pw(value: number): number { return Math.max(2, value * boxSize.value.w) }
function ph(value: number): number { return Math.max(2, value * boxSize.value.h) }
function pointerPosition(event: PointerEvent): { x: number; y: number } { const rect = canvasBox.value!.getBoundingClientRect(); return { x: clamp((event.clientX - rect.left) / rect.width), y: clamp((event.clientY - rect.top) / rect.height) } }
function onPointerDown(event: PointerEvent): void { if (!canvasBox.value || event.button !== 0 || fields.value.length >= MAX_FIELDS) return; measure(); const point = pointerPosition(event); drawingPointer = event.pointerId; canvasBox.value.setPointerCapture(event.pointerId); draft.value = { x0: point.x, y0: point.y, x1: point.x, y1: point.y } }
function onPointerMove(event: PointerEvent): void { if (drawingPointer !== event.pointerId || !draft.value) return; const point = pointerPosition(event); draft.value = { ...draft.value, x1: point.x, y1: point.y } }
function onPointerUp(event: PointerEvent): void { if (drawingPointer !== event.pointerId || !draft.value) return; const currentDraft = draft.value; cancelDrawing(event); const tiny = Math.abs(currentDraft.x1 - currentDraft.x0) < .015 || Math.abs(currentDraft.y1 - currentDraft.y0) < .01; const field = createField(activeType.value, page.value, currentDraft.x0, currentDraft.y0, tiny ? undefined : currentDraft.x1, tiny ? undefined : currentDraft.y1); fields.value.push(field); selectedId.value = field.id; restoredHint.value = ''; checkResult.value = null }
function cancelDrawing(event?: PointerEvent): void { if (event && canvasBox.value?.hasPointerCapture(event.pointerId)) canvasBox.value.releasePointerCapture(event.pointerId); drawingPointer = null; draft.value = null }
function selectField(id: number): void { selectedId.value = id }
function jumpTo(field: DesignerField): void { selectedId.value = field.id; page.value = field.page }
function removeSelected(): void { fields.value = fields.value.filter((field) => field.id !== selectedId.value); selectedId.value = null }
function duplicateSelected(): void { if (!selected.value || fields.value.length >= MAX_FIELDS) return; const source = selected.value; const copy: DesignerField = { ...source, id: nextId++, name: uniqueName(`${source.name}_kopie`), y0: clamp(source.y0 + .04, 0, .95), y1: clamp(source.y1 + .04, .01, 1) }; fields.value.push(copy); selectedId.value = copy.id }
function clearAll(): void { fields.value = []; selectedId.value = null; checkResult.value = null; restoredHint.value = ''; removeStoredValue(LAYOUT_KEY) }
function reset(): void { documentGeneration += 1; resizeObserver?.disconnect(); resizeObserver = null; file.value = null; workingBlob.value = null; clearEditorState() }

function geometryValue(field: DesignerField, key: 'x' | 'y' | 'width' | 'height'): number { const value = key === 'x' ? field.x0 : key === 'y' ? field.y0 : key === 'width' ? field.x1 - field.x0 : field.y1 - field.y0; return Math.round(value * 1000) / 10 }
function setGeometry(field: DesignerField, key: 'x' | 'y' | 'width' | 'height', event: Event): void { const parsed = Number((event.target as HTMLInputElement).value) / 100; if (!Number.isFinite(parsed)) return; const value = clamp(parsed); const width = field.x1 - field.x0; const height = field.y1 - field.y0; if (key === 'x') { field.x0 = clamp(value, 0, 1 - width); field.x1 = field.x0 + width } else if (key === 'y') { field.y0 = clamp(value, 0, 1 - height); field.y1 = field.y0 + height } else if (key === 'width') field.x1 = clamp(field.x0 + Math.max(.01, value), field.x0 + .01, 1); else field.y1 = clamp(field.y0 + Math.max(.01, value), field.y0 + .01, 1) }

function saveLayoutFile(): void { try { const blob = new Blob([JSON.stringify(serializeLayout(), null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); try { anchor.href = url; anchor.download = workingName.value.replace(/\.pdf$/i, '') + '_formular-layout.json'; document.body.appendChild(anchor); anchor.click() } finally { anchor.remove(); URL.revokeObjectURL(url) } summary.value = 'Layout als JSON-Datei gespeichert.' } catch { error.value = 'Das Layout konnte nicht serialisiert werden.' } }
async function onLayoutFile(event: Event): Promise<void> { const input = event.target as HTMLInputElement; const selectedFile = input.files?.[0]; input.value = ''; if (!selectedFile) return; if (selectedFile.size > MAX_LAYOUT_BYTES) { error.value = 'Die Layoutdatei ist ungewöhnlich groß.'; return } try { const parsed = JSON.parse(await selectedFile.text()) as unknown; const list = Array.isArray(parsed) ? parsed : parsed && typeof parsed === 'object' && 'fields' in parsed ? (parsed as { fields?: unknown }).fields : null; if (!Array.isArray(list)) throw new Error('Keine Feldliste gefunden.'); const count = loadFieldArray(list); if (!count) throw new Error('Keine gültigen Felder gefunden.'); summary.value = `${count} Feld(er) aus Layoutdatei importiert.` } catch (caught: unknown) { error.value = caught instanceof Error ? caught.message : 'Layout-Import fehlgeschlagen.' } }

function payload(): object[] { return fields.value.map((field) => ({ page: field.page, type: field.type, name: field.name.trim(), value: field.type === 'checkbox' ? field.checked : field.value, options: field.type === 'dropdown' || field.type === 'listbox' ? field.options.split(',').map((item) => item.trim()).filter(Boolean) : [], font_size: field.font_size, required: field.required, readonly: field.readonly, tooltip: field.tooltip, x0: field.x0, y0: field.y0, x1: field.x1, y1: field.y1, format: field.format_kind === 'none' ? {} : { kind: field.format_kind, decimals: field.format_decimals, currency: field.format_currency }, calc: field.calc_kind === 'none' ? {} : { kind: field.calc_kind, fields: field.calc_fields.split(',').map((item) => item.trim()).filter(Boolean), formula: field.calc_formula }, calc_readonly: field.calc_readonly, validate: field.validate_min === '' && field.validate_max === '' ? {} : { min: field.validate_min === '' ? null : Number(field.validate_min), max: field.validate_max === '' ? null : Number(field.validate_max) } })) }
async function importFromPdf(): Promise<void> { const blob = workingBlob.value; if (!blob || busy.value) return; const generation = documentGeneration; busy.value = true; error.value = null; summary.value = ''; try { const data = new FormData(); data.append('file', blob, workingName.value); const response = await apiPost('/api/pdf-extras/form/fields', data); const body = await response.json() as { fields?: unknown[] }; if (generation !== documentGeneration) return; const count = loadFieldArray(body.fields ?? []); summary.value = count ? `${count} vorhandene(s) Feld(er) übernommen.` : 'Dieses PDF enthält noch keine Formularfelder.' } catch (caught: unknown) { if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Import fehlgeschlagen.' } finally { if (generation === documentGeneration) busy.value = false } }
async function check(): Promise<void> { const blob = workingBlob.value; if (!blob || busy.value) return; const generation = documentGeneration; busy.value = true; error.value = null; summary.value = ''; try { const data = new FormData(); data.append('file', blob, workingName.value); data.append('fields', JSON.stringify(payload())); data.append('dry_run', 'true'); const response = await apiPost('/api/pdf-extras/form/create', data); const body = await response.json() as { created?: number; skipped?: number; warnings?: unknown[] }; if (generation !== documentGeneration) return; checkResult.value = { created: Number(body.created) || 0, skipped: Number(body.skipped) || 0, warnings: Array.isArray(body.warnings) ? body.warnings.map(String) : [] } } catch (caught: unknown) { if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Prüfung fehlgeschlagen.' } finally { if (generation === documentGeneration) busy.value = false } }
async function generate(): Promise<void> { const blob = workingBlob.value; if (!blob || !fields.value.length || busy.value || nameConflict.value) return; const generation = documentGeneration; busy.value = true; error.value = null; summary.value = ''; checkResult.value = null; try { const data = new FormData(); data.append('file', blob, workingName.value); data.append('fields', JSON.stringify(payload())); const response = await apiPost('/api/pdf-extras/form/create', data); const created = response.headers.get('X-Fields-Created') || '0'; const skipped = response.headers.get('X-Fields-Skipped') || '0'; await downloadBlob(response, workingName.value.replace(/\.pdf$/i, '_formular.pdf')); if (generation === documentGeneration) summary.value = `PDF erzeugt: ${created} Feld(er) angelegt, ${skipped} übersprungen.` } catch (caught: unknown) { if (generation === documentGeneration) error.value = caught instanceof Error ? caught.message : 'Erzeugen fehlgeschlagen.' } finally { if (generation === documentGeneration) busy.value = false } }

onBeforeUnmount(() => { documentGeneration += 1; resizeObserver?.disconnect(); cancelDrawing() })
</script>
