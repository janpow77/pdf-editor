<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Formular-Designer</h2>
    </div>

    <div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm text-blue-800 dark:text-blue-300">
      Formularfelder direkt auf der Seite aufziehen: Feldtyp wählen, Rechteck ziehen (oder
      klicken für Standardgröße), Eigenschaften rechts bearbeiten. Das Layout wird
      <strong>nur in Ihrem Browser</strong> gespeichert und lässt sich als JSON-Datei
      sichern und wieder importieren — auf dem Server bleibt nichts.
    </div>

    <!-- Wiederhergestelltes Layout -->
    <div
      v-if="restoredHint"
      class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300 flex items-center justify-between gap-3"
    >
      <span>{{ restoredHint }}</span>
      <button class="shrink-0 text-amber-700 dark:text-amber-300 underline hover:no-underline" @click="discardRestored">
        Verwerfen
      </button>
    </div>

    <WorkSessionBar
      tool="formDesigner"
      :blob="workingBlob"
      :name="workingName"
      :state="sessionState"
      :change-count="fields.length"
      @restore="restoreSession"
    />

    <template v-if="!workingBlob">
      <FileDrop v-model="file" />
      <div class="flex items-center gap-3 justify-center text-sm text-gray-500 dark:text-gray-400">
        <span aria-hidden="true" class="h-px w-16 bg-gray-200 dark:bg-gray-700" /> oder
        <span aria-hidden="true" class="h-px w-16 bg-gray-200 dark:bg-gray-700" />
      </div>
      <div class="flex justify-center gap-2">
        <button
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-200 hover:border-primary-400 hover:text-primary-600"
          @click="startBlank('hoch')"
        >
          📄 Ohne Vorlage beginnen (A4 hoch)
        </button>
        <button
          class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm text-gray-700 dark:text-gray-200 hover:border-primary-400 hover:text-primary-600"
          @click="startBlank('quer')"
        >
          📃 A4 quer
        </button>
      </div>
    </template>

    <template v-else>
      <!-- Werkzeugleiste -->
      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="t in fieldTypes"
          :key="t.value"
          class="px-3 py-1.5 rounded-lg text-sm border-2 transition-colors"
          :class="activeType === t.value
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
            : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-gray-300'"
          :title="t.hint"
          @click="activeType = t.value"
        >
          {{ t.icon }} {{ t.label }}
        </button>
      </div>

      <!-- Seiten-Navigation + Aktionen -->
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400" @click="saveLayoutFile">
          Layout speichern
        </button>
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400" @click="layoutInput?.click()">
          Layout importieren
        </button>
        <input ref="layoutInput" type="file" accept=".json,application/json" class="hidden" @change="onLayoutFile" />
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400" :disabled="busy" @click="importFromPdf">
          Felder aus PDF übernehmen
        </button>
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400" :disabled="busy || !fields.length" @click="check">
          Prüfen
        </button>
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-red-600 hover:border-red-400" :disabled="!fields.length" @click="clearAll">
          Alle Felder löschen
        </button>
        <button class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="reset">
          Neues Dokument
        </button>
      </div>

      <div class="grid lg:grid-cols-[1fr,20rem] gap-4 items-start">
        <!-- Zeichenfläche -->
        <div>
          <PdfViewer v-model="page" :source="workingBlob" @loaded="pageCount = $event">
            <template #overlay>
              <div
                ref="canvasBox"
                class="absolute inset-0 cursor-crosshair"
                @mousedown.prevent="onDown"
                @mousemove.prevent="onMove"
                @mouseup.prevent="onUp"
                @mouseleave="onUp"
              >
            <svg class="absolute inset-0 w-full h-full">
              <g v-for="f in pageFields" :key="f.id" @mousedown.stop.prevent="selectedId = f.id">
                <rect
                  :x="px(Math.min(f.x0, f.x1))"
                  :y="py(Math.min(f.y0, f.y1))"
                  :width="pw(Math.abs(f.x1 - f.x0))"
                  :height="ph(Math.abs(f.y1 - f.y0))"
                  :fill="f.id === selectedId ? 'rgba(0,113,227,0.18)' : 'rgba(0,113,227,0.08)'"
                  :stroke="f.id === selectedId ? '#0071e3' : '#7aa7d9'"
                  :stroke-width="f.id === selectedId ? 2 : 1"
                  class="cursor-pointer"
                />
                <text
                  :x="px(Math.min(f.x0, f.x1)) + 4"
                  :y="py(Math.min(f.y0, f.y1)) + 12"
                  font-size="11"
                  fill="#0a3f75"
                  class="pointer-events-none"
                >
                  {{ typeIcon(f.type) }} {{ f.name }}{{ f.required ? ' *' : '' }}
                </text>
              </g>
              <rect
                v-if="draft"
                :x="px(Math.min(draft.x0, draft.x1))"
                :y="py(Math.min(draft.y0, draft.y1))"
                :width="pw(Math.abs(draft.x1 - draft.x0))"
                :height="ph(Math.abs(draft.y1 - draft.y0))"
                fill="none"
                stroke="#0071e3"
                stroke-dasharray="4"
                stroke-width="1.5"
              />
            </svg>
              </div>
            </template>
          </PdfViewer>
        </div>

        <!-- Eigenschaften + Feldliste -->
        <div class="space-y-4">
          <div v-if="selected" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-white">Feld-Eigenschaften</h3>
              <span class="text-xs text-gray-600 dark:text-gray-400">Seite {{ selected.page }}</span>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Feldname (technisch)</label>
              <input v-model="selected.name" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
              <p v-if="nameConflict" class="mt-1 text-xs text-amber-600">Name doppelt — beim Erzeugen wird automatisch nummeriert.</p>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Typ</label>
              <select v-model="selected.type" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white">
                <option v-for="t in fieldTypes" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Hilfetext (Tooltip)</label>
              <input v-model="selected.tooltip" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
            </div>
            <div v-if="selected.type === 'dropdown' || selected.type === 'listbox'">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Auswahlwerte (mit Komma trennen)</label>
              <input v-model="selected.options" type="text" placeholder="Frau, Herr, keine Angabe" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
            </div>
            <div v-if="selected.type === 'checkbox'">
              <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input v-model="selected.checked" type="checkbox" class="rounded" /> Vorbelegt angekreuzt
              </label>
            </div>
            <div v-else-if="selected.type !== 'signature'">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Vorbelegter Wert</label>
              <input v-model="selected.value" type="text" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
            </div>
            <div v-if="selected.type !== 'signature' && selected.type !== 'checkbox'">
              <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Schriftgröße</label>
              <input v-model.number="selected.font_size" type="number" min="4" max="72" step="0.5" class="w-24 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
            </div>
            <div class="flex flex-wrap gap-4">
              <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input v-model="selected.required" type="checkbox" class="rounded" /> Pflichtfeld
              </label>
              <label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input v-model="selected.readonly" type="checkbox" class="rounded" /> Nur lesbar
              </label>
            </div>

            <!-- Berechnung, Format, Wertebereich (nur Textfelder) -->
            <details v-if="selected.type === 'text' || selected.type === 'textarea'" class="border-t border-gray-100 dark:border-gray-700 pt-3">
              <summary class="text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
                Berechnung &amp; Format
                <span v-if="selected.calc_kind !== 'none' || selected.format_kind !== 'none'" class="ml-1 text-xs text-primary-600">aktiv</span>
              </summary>
              <div class="mt-3 space-y-3">
                <div>
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Zahlenformat</label>
                  <div class="flex gap-2">
                    <select v-model="selected.format_kind" class="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-white">
                      <option value="none">kein Format</option>
                      <option value="number">Zahl (1.234,56)</option>
                      <option value="currency">Währung</option>
                      <option value="percent">Prozent</option>
                    </select>
                    <input v-model.number="selected.format_decimals" type="number" min="0" max="6" title="Nachkommastellen" class="w-16 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-white" />
                  </div>
                  <input v-if="selected.format_kind === 'currency'" v-model="selected.format_currency" type="text" maxlength="8" placeholder="EUR" class="mt-2 w-24 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-white" />
                </div>
                <div>
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Berechnung</label>
                  <select v-model="selected.calc_kind" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-white">
                    <option value="none">keine</option>
                    <option value="sum">Summe der Felder</option>
                    <option value="product">Produkt der Felder</option>
                    <option value="average">Mittelwert der Felder</option>
                    <option value="min">Minimum</option>
                    <option value="max">Maximum</option>
                    <option value="formula">Formel</option>
                  </select>
                </div>
                <div v-if="['sum','product','average','min','max'].includes(selected.calc_kind)">
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Quellfelder (anklicken)</label>
                  <div class="flex flex-wrap gap-1">
                    <button
                      v-for="n in otherFieldNames"
                      :key="n"
                      class="px-2 py-0.5 rounded text-xs border"
                      :class="calcFieldList.includes(n)
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                        : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300'"
                      @click="toggleCalcField(n)"
                    >
                      {{ n }}
                    </button>
                  </div>
                  <p v-if="!otherFieldNames.length" class="text-xs text-gray-600 dark:text-gray-400">Erst weitere Felder anlegen.</p>
                </div>
                <div v-else-if="selected.calc_kind === 'formula'">
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Formel (nur Feldnamen und + − × ÷)</label>
                  <input v-model="selected.calc_formula" type="text" placeholder="netto * 1,19" class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-900 dark:text-white" />
                  <p class="mt-1 text-xs text-gray-600 dark:text-gray-400">Verfügbar: {{ otherFieldNames.join(', ') || '—' }}</p>
                </div>
                <label v-if="selected.calc_kind !== 'none'" class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input v-model="selected.calc_readonly" type="checkbox" class="rounded" /> Ergebnis schreibgeschützt
                </label>
                <div>
                  <label class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Zulässiger Wertebereich</label>
                  <div class="flex items-center gap-2">
                    <input v-model="selected.validate_min" type="number" placeholder="min" class="w-24 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-white" />
                    <span class="text-gray-600 dark:text-gray-400">bis</span>
                    <input v-model="selected.validate_max" type="number" placeholder="max" class="w-24 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1.5 text-sm text-gray-900 dark:text-white" />
                  </div>
                </div>
                <p class="text-xs text-gray-600 dark:text-gray-400">
                  Berechnung, Format und Wertebereich werden als PDF-Aktionen hinterlegt und
                  von Acrobat &amp; Co. ausgeführt — einfache Browser-Vorschauen zeigen sie nicht.
                </p>
              </div>
            </details>
            <div class="flex gap-2 pt-1">
              <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="duplicateSelected">Duplizieren</button>
              <button class="px-3 py-1.5 text-sm rounded-lg border border-red-300 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20" @click="removeSelected">Feld löschen</button>
            </div>
          </div>
          <p v-else class="text-sm text-gray-500 dark:text-gray-400">
            Kein Feld ausgewählt — Rechteck auf der Seite ziehen oder ein Feld anklicken.
          </p>

          <!-- Feldliste -->
          <div v-if="fields.length" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 class="text-sm font-semibold text-gray-900 dark:text-white mb-2">Felder ({{ fields.length }})</h3>
            <ul class="max-h-64 overflow-y-auto divide-y divide-gray-100 dark:divide-gray-700 text-sm">
              <li
                v-for="f in fields"
                :key="f.id"
                class="py-1.5 flex items-center justify-between gap-2 cursor-pointer"
                :class="f.id === selectedId ? 'text-primary-700 dark:text-primary-300 font-medium' : 'text-gray-700 dark:text-gray-300'"
                @click="jumpTo(f)"
              >
                <span class="truncate">{{ typeIcon(f.type) }} {{ f.name }}</span>
                <span class="shrink-0 text-xs text-gray-600 dark:text-gray-400">S. {{ f.page }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Prüfhinweise -->
      <div v-if="checkResult" class="p-3 rounded-lg text-sm border" :class="checkResult.warnings.length
        ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-700 text-amber-800 dark:text-amber-300'
        : 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-700 text-green-700 dark:text-green-300'">
        <p>{{ checkResult.created }} Feld(er) werden angelegt, {{ checkResult.skipped }} übersprungen.</p>
        <ul v-if="checkResult.warnings.length" class="list-disc list-inside mt-1 space-y-0.5">
          <li v-for="(w, i) in checkResult.warnings" :key="i">{{ w }}</li>
        </ul>
      </div>

      <div v-if="summary" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
        {{ summary }}
      </div>

      <p class="text-xs text-gray-600 dark:text-gray-400">
        Hinweis: Optionsfelder (Radio-Gruppen) werden nicht unterstützt — nutzen Sie
        stattdessen ein Auswahlfeld (Dropdown) oder mehrere Kontrollkästchen.
      </p>

      <button
        :disabled="busy || !fields.length"
        class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        @click="generate"
      >
        {{ busy ? 'Erzeuge…' : `PDF mit ${fields.length} Feld(ern) erzeugen` }}
      </button>
    </template>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
// pdf.js wiegt rund 370 kB. Als asynchrone Komponente erscheint die
// Werkzeug-Oberfläche sofort; der Viewer wird parallel nachgeladen und
// erst gebraucht, wenn tatsächlich ein Dokument geöffnet ist.
const PdfViewer = defineAsyncComponent(() => import('@/components/PdfViewer.vue'))
import WorkSessionBar from '@/components/WorkSessionBar.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

type FieldType = 'text' | 'textarea' | 'checkbox' | 'dropdown' | 'listbox' | 'signature'

interface DesignerField {
  id: number
  page: number
  type: FieldType
  name: string
  value: string
  checked: boolean
  options: string
  font_size: number
  required: boolean
  readonly: boolean
  tooltip: string
  x0: number
  y0: number
  x1: number
  y1: number
  // Berechnung / Format / Wertebereich (nur Textfelder)
  format_kind: 'none' | 'number' | 'currency' | 'percent'
  format_decimals: number
  format_currency: string
  calc_kind: 'none' | 'sum' | 'product' | 'average' | 'min' | 'max' | 'formula'
  calc_fields: string
  calc_formula: string
  calc_readonly: boolean
  validate_min: string
  validate_max: string
}

interface ApiField {
  name?: string
  page?: number
  designer_type?: string
  value?: string
  options?: string[]
  font_size?: number
  required?: boolean
  readonly?: boolean
  tooltip?: string
  x0?: number
  y0?: number
  x1?: number
  y1?: number
}

const LAYOUT_KEY = 'pdfapp_form_layout'
const MAX_FIELDS = 200

const fieldTypes: { value: FieldType; label: string; icon: string; hint: string; w: number; h: number }[] = [
  { value: 'text', label: 'Textfeld', icon: '▭', hint: 'Einzeilige Eingabe', w: 0.35, h: 0.028 },
  { value: 'textarea', label: 'Mehrzeilig', icon: '▤', hint: 'Mehrzeiliges Textfeld', w: 0.5, h: 0.09 },
  { value: 'checkbox', label: 'Kontrollkästchen', icon: '☑', hint: 'Ja/Nein-Feld', w: 0.03, h: 0.022 },
  { value: 'dropdown', label: 'Auswahl', icon: '▾', hint: 'Dropdown mit Werten', w: 0.3, h: 0.028 },
  { value: 'listbox', label: 'Liste', icon: '☰', hint: 'Listenauswahl', w: 0.3, h: 0.08 },
  { value: 'signature', label: 'Signaturfeld', icon: '✍️', hint: 'Feld für digitale Signatur', w: 0.35, h: 0.06 },
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
const draft = ref<{ x0: number; y0: number; x1: number; y1: number } | null>(null)
const boxSize = ref({ w: 1, h: 1 })
const checkResult = ref<{ created: number; skipped: number; warnings: string[] } | null>(null)

let nextId = 1

const pageFields = computed(() => fields.value.filter((f) => f.page === page.value))
const selected = computed(() => fields.value.find((f) => f.id === selectedId.value) ?? null)
const nameConflict = computed(() => {
  const s = selected.value
  if (!s) return false
  return fields.value.some((f) => f.id !== s.id && f.name.trim() === s.name.trim())
})

// Für „Bearbeitung unterbrechen": Felder + Seite mitsamt Dokument sichern.
// Ergänzt das reine Layout-JSON, das nur die Felder ohne Dokument enthält.
const sessionState = computed(() => ({ fields: fields.value, page: page.value }))

function restoreSession(payload: { name: string; blob: Blob; state: unknown }) {
  workingBlob.value = payload.blob
  workingName.value = payload.name
  const state = payload.state as { fields?: DesignerField[]; page?: number } | null
  if (state?.fields?.length) {
    loadFieldArray(state.fields as unknown[])
  } else {
    fields.value = []
    selectedId.value = null
  }
  page.value = state?.page && state.page > 0 ? state.page : 1
  restoredHint.value = ''
  error.value = null
}

function typeIcon(t: FieldType): string {
  return fieldTypes.find((x) => x.value === t)?.icon ?? '▭'
}

// Andere Felder als mögliche Rechenquellen (Textfelder mit Namen)
const otherFieldNames = computed(() =>
  fields.value
    .filter((f) => f.id !== selectedId.value && f.name.trim() && ['text', 'textarea'].includes(f.type))
    .map((f) => f.name.trim()),
)
const calcFieldList = computed(() =>
  (selected.value?.calc_fields ?? '').split(',').map((s) => s.trim()).filter(Boolean),
)

function toggleCalcField(name: string) {
  const s = selected.value
  if (!s) return
  const list = calcFieldList.value
  const next = list.includes(name) ? list.filter((n) => n !== name) : [...list, name]
  s.calc_fields = next.join(', ')
}

// ── Layout: lokal speichern (localStorage + JSON-Datei) ──────

function serializeLayout() {
  return {
    version: 1,
    app: 'pdf-editor-formular',
    document: workingName.value,
    created: new Date().toISOString(),
    fields: fields.value.map(({ id: _id, ...rest }) => rest),
  }
}

watch(
  fields,
  () => {
    if (!fields.value.length) {
      localStorage.removeItem(LAYOUT_KEY)
      return
    }
    try {
      localStorage.setItem(LAYOUT_KEY, JSON.stringify(serializeLayout()))
    } catch {
      /* Speicher voll oder blockiert — Designer läuft weiter */
    }
  },
  { deep: true },
)

function normalizeField(raw: Record<string, unknown>): DesignerField | null {
  // PDF-Import liefert designer_type ("text") neben dem PDF-internen type
  // ("Text") — der Designer-Typ hat Vorrang, Layout-Dateien haben nur `type`.
  const type = String(raw.designer_type ?? raw.type ?? 'text') as FieldType
  if (!fieldTypes.some((t) => t.value === type)) return null
  const num = (v: unknown, fallback: number) => {
    const n = Number(v)
    return Number.isFinite(n) ? n : fallback
  }
  const clamp01 = (v: number) => Math.max(0, Math.min(1, v))
  const optionsRaw = raw.options
  return {
    id: nextId++,
    page: Math.max(1, Math.trunc(num(raw.page, 1))),
    type,
    name: String(raw.name ?? `feld_${nextId}`).slice(0, 120),
    value: type === 'checkbox' ? '' : String(raw.value ?? ''),
    checked: type === 'checkbox' ? Boolean(raw.value ?? raw.checked) && String(raw.value ?? raw.checked) !== 'Off' : false,
    options: Array.isArray(optionsRaw) ? optionsRaw.map(String).join(', ') : String(optionsRaw ?? ''),
    font_size: Math.max(4, Math.min(72, num(raw.font_size, 11))),
    required: Boolean(raw.required),
    readonly: Boolean(raw.readonly),
    tooltip: String(raw.tooltip ?? ''),
    x0: clamp01(num(raw.x0, 0.1)),
    y0: clamp01(num(raw.y0, 0.1)),
    x1: clamp01(num(raw.x1, 0.4)),
    y1: clamp01(num(raw.y1, 0.14)),
    format_kind: (['number', 'currency', 'percent'].includes(String(raw.format_kind))
      ? String(raw.format_kind)
      : 'none') as DesignerField['format_kind'],
    format_decimals: Math.max(0, Math.min(6, num(raw.format_decimals, 2))),
    format_currency: String(raw.format_currency ?? 'EUR'),
    calc_kind: (['sum', 'product', 'average', 'min', 'max', 'formula'].includes(String(raw.calc_kind))
      ? String(raw.calc_kind)
      : 'none') as DesignerField['calc_kind'],
    calc_fields: Array.isArray(raw.calc_fields)
      ? (raw.calc_fields as unknown[]).map(String).join(', ')
      : String(raw.calc_fields ?? ''),
    calc_formula: String(raw.calc_formula ?? ''),
    calc_readonly: raw.calc_readonly === undefined ? true : Boolean(raw.calc_readonly),
    validate_min: raw.validate_min === undefined || raw.validate_min === null ? '' : String(raw.validate_min),
    validate_max: raw.validate_max === undefined || raw.validate_max === null ? '' : String(raw.validate_max),
  }
}

function loadFieldArray(list: unknown[], keepPageLimit = true): number {
  const loaded: DesignerField[] = []
  for (const raw of list.slice(0, MAX_FIELDS)) {
    if (typeof raw !== 'object' || raw === null) continue
    const f = normalizeField(raw as Record<string, unknown>)
    if (!f) continue
    if (keepPageLimit && f.page > pageCount.value) f.page = pageCount.value
    loaded.push(f)
  }
  fields.value = loaded
  selectedId.value = loaded.length ? loaded[0].id : null
  return loaded.length
}

function saveLayoutFile() {
  const blob = new Blob([JSON.stringify(serializeLayout(), null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = workingName.value.replace(/\.pdf$/i, '') + '_formular-layout.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  summary.value = 'Layout als JSON-Datei gespeichert (nur lokal).'
}

async function onLayoutFile(e: Event) {
  const input = e.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (!f) return
  error.value = null
  summary.value = ''
  checkResult.value = null
  try {
    const parsed = JSON.parse(await f.text()) as unknown
    const list = Array.isArray(parsed)
      ? parsed
      : ((parsed as { fields?: unknown }).fields as unknown[] | undefined)
    if (!Array.isArray(list)) throw new Error('Datei enthält keine Feldliste')
    const n = loadFieldArray(list)
    if (!n) throw new Error('Keine gültigen Felder in der Datei')
    summary.value = `${n} Feld(er) aus Layout-Datei importiert.`
    restoredHint.value = ''
  } catch (err: unknown) {
    error.value = `Layout-Import fehlgeschlagen: ${err instanceof Error ? err.message : 'unbekannt'}`
  }
}

function discardRestored() {
  fields.value = []
  selectedId.value = null
  restoredHint.value = ''
  localStorage.removeItem(LAYOUT_KEY)
}

// ── Dokument laden ───────────────────────────────────────────

watch(file, async (f) => {
  if (!f) return
  workingBlob.value = f
  workingName.value = f.name
  page.value = 1
  error.value = null
  summary.value = ''
  checkResult.value = null
  restoreLayout()
})

// ── Ohne Vorlage: leeres A4-Blatt direkt im Browser erzeugen ─
//
// Ein minimales, valides Einseiten-PDF lässt sich als Text zusammensetzen —
// die xref-Offsets werden beim Bau mitgezählt. Damit braucht der Leerstart
// weder eine Bibliothek noch einen Server-Aufruf.
function makeBlankPdf(orientation: 'hoch' | 'quer'): Blob {
  const [w, h] = orientation === 'hoch' ? [595, 842] : [842, 595]
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${w} ${h}] /Resources << >> >>`,
  ]
  let body = '%PDF-1.4\n'
  const offsets: number[] = []
  objects.forEach((obj, i) => {
    offsets.push(body.length)
    body += `${i + 1} 0 obj\n${obj}\nendobj\n`
  })
  const xrefStart = body.length
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  for (const off of offsets) body += `${String(off).padStart(10, '0')} 00000 n \n`
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF\n`
  return new Blob([body], { type: 'application/pdf' })
}

function startBlank(orientation: 'hoch' | 'quer') {
  const name = orientation === 'hoch' ? 'Leeres-Formular-A4.pdf' : 'Leeres-Formular-A4-quer.pdf'
  file.value = new File([makeBlankPdf(orientation)], name, { type: 'application/pdf' })
}

function restoreLayout() {
  const stored = localStorage.getItem(LAYOUT_KEY)
  if (!stored) return
  try {
    const parsed = JSON.parse(stored) as { fields?: unknown[]; document?: string }
    if (!Array.isArray(parsed.fields) || !parsed.fields.length) return
    const n = loadFieldArray(parsed.fields)
    if (n) {
      const doc = parsed.document && parsed.document !== workingName.value ? ` (aus „${parsed.document}")` : ''
      restoredHint.value = `Zuletzt bearbeitetes Layout wiederhergestellt: ${n} Feld(er)${doc}.`
    }
  } catch {
    localStorage.removeItem(LAYOUT_KEY)
  }
}

function jumpTo(f: DesignerField) {
  selectedId.value = f.id
  page.value = f.page  // der Viewer rendert die Seite lokal nach
}

// ── Zeichnen ─────────────────────────────────────────────────

function measure() {
  if (canvasBox.value) boxSize.value = { w: canvasBox.value.clientWidth, h: canvasBox.value.clientHeight }
}
function px(x: number) { return x * boxSize.value.w }
function py(y: number) { return y * boxSize.value.h }
function pw(w: number) { return Math.max(2, w * boxSize.value.w) }
function ph(h: number) { return Math.max(2, h * boxSize.value.h) }

function norm(e: MouseEvent) {
  const r = canvasBox.value!.getBoundingClientRect()
  return {
    x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)),
    y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)),
  }
}

let drawing = false

function onDown(e: MouseEvent) {
  if (!canvasBox.value) return
  measure()
  const p = norm(e)
  drawing = true
  draft.value = { x0: p.x, y0: p.y, x1: p.x, y1: p.y }
}

function onMove(e: MouseEvent) {
  if (!drawing || !draft.value) return
  const p = norm(e)
  draft.value = { ...draft.value, x1: p.x, y1: p.y }
}

function onUp() {
  if (!drawing) return
  drawing = false
  const d = draft.value
  draft.value = null
  if (!d) return
  if (fields.value.length >= MAX_FIELDS) {
    error.value = `Maximal ${MAX_FIELDS} Felder pro Dokument.`
    return
  }
  const preset = fieldTypes.find((t) => t.value === activeType.value)!
  const r4 = (v: number) => Math.round(v * 10000) / 10000
  // Klick ohne Ziehen → Standardgröße des Feldtyps
  const tiny = Math.abs(d.x1 - d.x0) < 0.015 || Math.abs(d.y1 - d.y0) < 0.008
  const x0 = Math.min(d.x0, d.x1)
  const y0 = Math.min(d.y0, d.y1)
  const x1 = tiny ? Math.min(1, x0 + preset.w) : Math.max(d.x0, d.x1)
  const y1 = tiny ? Math.min(1, y0 + preset.h) : Math.max(d.y0, d.y1)

  const base = activeType.value === 'signature' ? 'unterschrift' : 'feld'
  let n = fields.value.length + 1
  while (fields.value.some((f) => f.name === `${base}_${n}`)) n++
  fields.value.push({
    id: nextId++,
    page: page.value,
    type: activeType.value,
    name: `${base}_${n}`,
    value: '',
    checked: false,
    options: activeType.value === 'dropdown' || activeType.value === 'listbox' ? 'Option A, Option B' : '',
    font_size: 11,
    required: false,
    readonly: false,
    tooltip: '',
    x0: r4(x0),
    y0: r4(y0),
    x1: r4(x1),
    y1: r4(y1),
    format_kind: 'none',
    format_decimals: 2,
    format_currency: 'EUR',
    calc_kind: 'none',
    calc_fields: '',
    calc_formula: '',
    calc_readonly: true,
    validate_min: '',
    validate_max: '',
  })
  selectedId.value = fields.value[fields.value.length - 1].id
  restoredHint.value = ''
  checkResult.value = null
}

function removeSelected() {
  fields.value = fields.value.filter((f) => f.id !== selectedId.value)
  selectedId.value = null
}

function duplicateSelected() {
  const s = selected.value
  if (!s || fields.value.length >= MAX_FIELDS) return
  const offset = 0.04
  let n = fields.value.length + 1
  const base = s.name.replace(/_\d+$/, '')
  while (fields.value.some((f) => f.name === `${base}_${n}`)) n++
  const copy: DesignerField = {
    ...s,
    id: nextId++,
    name: `${base}_${n}`,
    y0: Math.min(1, s.y0 + offset),
    y1: Math.min(1, s.y1 + offset),
  }
  fields.value.push(copy)
  selectedId.value = copy.id
}

function clearAll() {
  fields.value = []
  selectedId.value = null
  checkResult.value = null
  restoredHint.value = ''
}

function reset() {
  file.value = null
  workingBlob.value = null
  fields.value = []
  selectedId.value = null
  summary.value = ''
  error.value = null
  checkResult.value = null
}

// ── Backend-Aufrufe ──────────────────────────────────────────

function payload() {
  return fields.value.map((f) => ({
    page: f.page,
    type: f.type,
    name: f.name,
    value: f.type === 'checkbox' ? f.checked : f.value,
    options:
      f.type === 'dropdown' || f.type === 'listbox'
        ? f.options.split(',').map((o) => o.trim()).filter(Boolean)
        : [],
    font_size: f.font_size,
    required: f.required,
    readonly: f.readonly,
    tooltip: f.tooltip,
    x0: f.x0,
    y0: f.y0,
    x1: f.x1,
    y1: f.y1,
    format:
      f.format_kind === 'none'
        ? {}
        : { kind: f.format_kind, decimals: f.format_decimals, currency: f.format_currency },
    calc:
      f.calc_kind === 'none'
        ? {}
        : {
            kind: f.calc_kind,
            fields: f.calc_fields.split(',').map((n) => n.trim()).filter(Boolean),
            formula: f.calc_formula,
          },
    calc_readonly: f.calc_readonly,
    validate:
      f.validate_min === '' && f.validate_max === ''
        ? {}
        : { min: f.validate_min === '' ? null : Number(f.validate_min), max: f.validate_max === '' ? null : Number(f.validate_max) },
  }))
}

async function importFromPdf() {
  if (!workingBlob.value) return
  busy.value = true
  error.value = null
  summary.value = ''
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    const resp = await apiPost('/api/pdf-extras/form/fields', fd)
    const body = (await resp.json()) as { fields: ApiField[]; count: number }
    if (!body.count) {
      summary.value = 'Dieses PDF enthält noch keine Formularfelder.'
      return
    }
    const n = loadFieldArray(body.fields as unknown as unknown[])
    summary.value = `${n} vorhandene(s) Feld(er) aus dem PDF übernommen — jetzt bearbeitbar.`
    restoredHint.value = ''
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Import fehlgeschlagen'
  } finally {
    busy.value = false
  }
}

async function check() {
  if (!workingBlob.value) return
  busy.value = true
  error.value = null
  summary.value = ''
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    fd.append('fields', JSON.stringify(payload()))
    fd.append('dry_run', 'true')
    const resp = await apiPost('/api/pdf-extras/form/create', fd)
    const body = (await resp.json()) as { created: number; skipped: number; warnings: string[] }
    checkResult.value = { created: body.created, skipped: body.skipped, warnings: body.warnings || [] }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Prüfung fehlgeschlagen'
  } finally {
    busy.value = false
  }
}

async function generate() {
  if (!workingBlob.value || !fields.value.length) return
  busy.value = true
  error.value = null
  summary.value = ''
  checkResult.value = null
  try {
    const fd = new FormData()
    fd.append('file', workingBlob.value, workingName.value)
    fd.append('fields', JSON.stringify(payload()))
    const resp = await apiPost('/api/pdf-extras/form/create', fd)
    const created = resp.headers.get('X-Fields-Created') || '0'
    const skipped = resp.headers.get('X-Fields-Skipped') || '0'
    await downloadBlob(resp, workingName.value.replace(/\.pdf$/i, '_formular.pdf'))
    summary.value = `PDF erzeugt: ${created} Feld(er) angelegt, ${skipped} übersprungen. Datei heruntergeladen.`
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Erzeugen fehlgeschlagen'
  } finally {
    busy.value = false
  }
}
</script>
