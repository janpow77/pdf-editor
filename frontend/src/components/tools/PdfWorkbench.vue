<template>
  <div class="space-y-5">
    <ToolHeader
      title="Werkbank"
      description="Mehrere PDFs laden und alle Seiten dokumentübergreifend mischen, schneiden, drehen, duplizieren und neu zusammenstellen — das Ergebnis lässt sich direkt an jedes andere Werkzeug übergeben."
      @back="$emit('back')"
    />

    <UiDropZone
      :active="isDragging"
      :accepted="docs.length > 0"
      :invalid="Boolean(errorText)"
      @drag-active="isDragging = $event"
      @drop="onDroppedFiles"
    >
      <input ref="fileInput" type="file" accept=".pdf" multiple class="hidden" @change="onFileSelect" />
      <div>
        <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-primary-50 text-2xl text-primary-700 shadow-sm dark:bg-primary-500/15 dark:text-primary-300" aria-hidden="true">🛠️</div>
        <p class="mt-3 font-semibold text-gray-950 dark:text-white">{{ docs.length ? 'Weitere PDFs hierher ziehen' : 'PDFs hierher ziehen' }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Mehrere Dateien gleichzeitig möglich — jede Seite wird einzeln bearbeitbar.</p>
        <UiButton variant="primary" class="mt-4" :loading="loadingDocs > 0" @click="fileInput?.click()">Dateien auswählen</UiButton>
      </div>
    </UiDropZone>

    <UiPanel v-if="docs.length" padding="sm" class="flex flex-wrap items-center gap-2">
      <span class="text-sm font-semibold text-gray-800 dark:text-gray-100">Dokumente:</span>
      <span
        v-for="(doc, index) in docs"
        :key="doc.uid"
        class="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium ring-1 ring-black/5 dark:ring-white/10"
        :class="docBadgeClass(index)"
      >
        <strong>D{{ index + 1 }}</strong>
        <span class="max-w-44 truncate">{{ doc.label }}</span>
        <span class="tabular-nums">· {{ doc.pages }} S.</span>
        <button
          type="button"
          class="ml-0.5 grid h-5 w-5 place-items-center rounded-full transition hover:bg-black/10 dark:hover:bg-white/20"
          :aria-label="`Dokument D${index + 1} (${doc.label}) samt Seiten aus der Werkbank entfernen`"
          @click="removeDoc(doc.uid)"
        >×</button>
      </span>
    </UiPanel>

    <UiPanel v-if="items.length" padding="sm" class="flex flex-wrap items-center gap-2" aria-label="Aktionen für die Seitenauswahl">
      <UiButton size="sm" variant="secondary" @click="selectAll(selectedItems.length < items.length)">
        {{ selectedItems.length < items.length ? 'Alle auswählen' : 'Auswahl aufheben' }}
      </UiButton>
      <span class="text-sm font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ selectedItems.length }} ausgewählt</span>
      <span class="mx-1 h-7 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
      <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" @click="rotateSelection(-90)">↺ Links drehen</UiButton>
      <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" @click="rotateSelection(90)">↻ Rechts drehen</UiButton>
      <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" @click="duplicateSelection">⧉ Duplizieren</UiButton>
      <UiButton size="sm" variant="secondary" @click="insertBlank">➕ Leerseite</UiButton>
      <span class="mx-1 h-7 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
      <UiButton size="sm" variant="danger" :disabled="!selectedItems.length" @click="removeSelection(true)">Entfernen</UiButton>
      <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" @click="removeSelection(false)">Wiederherstellen</UiButton>
    </UiPanel>

    <div
      v-if="items.length"
      role="list"
      aria-label="Seitenfolge der Zusammenstellung. Reihenfolge per Ziehen oder mit den Verschieben-Knöpfen ändern."
      class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6"
    >
      <div
        v-for="(item, index) in items"
        :key="item.uid"
        role="listitem"
        class="flex flex-col rounded-2xl bg-white p-2 shadow-apple-sm ring-1 transition dark:bg-gray-900"
        :class="[
          item.selected ? 'ring-2 ring-primary-500' : 'ring-gray-300 dark:ring-gray-600',
          item.removed ? 'grayscale' : '',
          dragIndex === index ? 'opacity-60' : '',
        ]"
        draggable="true"
        @dragstart="dragIndex = index"
        @dragend="dragIndex = -1"
        @dragover.prevent
        @drop.prevent="reorderTo(index)"
      >
        <div class="flex items-center justify-between gap-1 px-1 pb-1.5">
          <span class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="badgeClass(item)">{{ badgeText(item) }}</span>
          <span v-if="item.rotation" class="text-xs font-semibold text-gray-600 dark:text-gray-300">{{ item.rotation }}°</span>
          <span class="text-xs font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ index + 1 }}</span>
        </div>

        <button
          type="button"
          class="relative block h-40 overflow-hidden rounded-xl bg-gray-100 outline-none transition focus-visible:ring-2 focus-visible:ring-primary-500 dark:bg-white/10"
          :aria-pressed="item.selected"
          :aria-label="cardLabel(item, index)"
          @click="item.selected = !item.selected"
        >
          <img
            v-if="thumbSrc(item)"
            :src="thumbSrc(item) ?? undefined"
            alt=""
            class="mx-auto h-full object-contain"
            :style="thumbStyle(item)"
          />
          <span v-else class="grid h-full place-items-center text-4xl" aria-hidden="true">📄</span>
          <span v-if="item.selected" class="absolute left-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-full bg-primary-600 text-xs font-bold text-white" aria-hidden="true">✓</span>
          <span v-if="item.removed" class="absolute inset-0 grid place-items-center bg-white/75 text-sm font-bold text-rose-700 dark:bg-gray-950/75 dark:text-rose-300">Entfernt</span>
        </button>

        <div class="mt-1.5 flex items-center justify-center gap-1">
          <button type="button" class="grid h-8 w-8 place-items-center rounded-lg text-sm text-gray-700 ring-1 ring-gray-300 transition hover:bg-gray-100 disabled:opacity-40 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-white/10" :disabled="index === 0" :aria-label="`Position ${index + 1} nach vorn verschieben`" @click="moveItem(index, -1)">←</button>
          <button type="button" class="grid h-8 w-8 place-items-center rounded-lg text-sm text-gray-700 ring-1 ring-gray-300 transition hover:bg-gray-100 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-white/10" :aria-label="`Position ${index + 1} um 90 Grad drehen`" @click="rotateItem(item)">⟳</button>
          <button type="button" class="grid h-8 w-8 place-items-center rounded-lg text-sm text-gray-700 ring-1 ring-gray-300 transition hover:bg-gray-100 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-white/10" :aria-label="item.removed ? `Position ${index + 1} wiederherstellen` : `Position ${index + 1} entfernen`" @click="item.removed = !item.removed">{{ item.removed ? '⤺' : '✕' }}</button>
          <button type="button" class="grid h-8 w-8 place-items-center rounded-lg text-sm text-gray-700 ring-1 ring-gray-300 transition hover:bg-gray-100 disabled:opacity-40 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-white/10" :disabled="index === items.length - 1" :aria-label="`Position ${index + 1} nach hinten verschieben`" @click="moveItem(index, 1)">→</button>
        </div>
      </div>
    </div>

    <p class="sr-only" aria-live="polite" aria-atomic="true">{{ liveSummary }}</p>

    <UiPanel v-if="items.length" padding="sm" class="flex flex-wrap items-center gap-3">
      <UiButton variant="primary" :loading="busy" :disabled="!activeItems.length" @click="composeAndDownload(activeItems, 'werkbank.pdf')">
        Ergebnis erstellen ({{ activeItems.length }} Seiten)
      </UiButton>
      <UiButton variant="secondary" :disabled="busy || !selectedActiveItems.length" @click="composeAndDownload(selectedActiveItems, 'werkbank-auswahl.pdf')">
        Auswahl als PDF exportieren ({{ selectedActiveItems.length }})
      </UiButton>
      <span class="flex-1"></span>
      <label class="flex flex-wrap items-center gap-2 text-sm font-medium text-gray-800 dark:text-gray-100">
        Weiterbearbeiten in
        <select
          v-model="targetToolId"
          class="rounded-xl bg-white px-3 py-2 text-sm font-medium text-gray-950 ring-1 ring-gray-400/70 transition focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 dark:text-white dark:ring-gray-600"
        >
          <option value="" disabled>Werkzeug wählen …</option>
          <optgroup v-for="group in handoffGroups" :key="group.title" :label="group.title">
            <option v-for="tool in group.tools" :key="tool.id" :value="tool.id">{{ tool.label }}</option>
          </optgroup>
        </select>
      </label>
      <UiButton variant="secondary" :disabled="busy || !targetToolId || !activeItems.length" @click="handOff">Übergeben →</UiButton>
    </UiPanel>

    <UiAlert v-if="errorText" tone="danger">{{ errorText }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { usePdfTools } from '@/composables/usePdfTools'
import { apiPost, downloadBlob } from '@/lib/api'
import { currentFileLimit, formatFileSize, validatePdfFile } from '@/lib/fileValidation'
import { setPendingHandoff } from '@/lib/handoff'
import { TOOL_GROUPS, type ToolId } from '@/lib/toolCatalog'

interface WorkbenchDoc {
  uid: number
  file: File
  label: string
  pages: number
  thumbs: Record<string, string>
}

/** Ein Eintrag der Zielreihenfolge; `docUid === null` steht für eine Leerseite. */
interface WorkbenchItem {
  uid: number
  docUid: number | null
  page: number
  rotation: number
  removed: boolean
  selected: boolean
}

const emit = defineEmits<{ (event: 'back'): void; (event: 'switch-tool', id: ToolId): void }>()

const MAX_DOCS = 50
const MAX_PAGES = 2000
const COMPOSE_TIMEOUT = 5 * 60 * 1000

const notifications = useNotifications()
const { getThumbnails } = usePdfTools()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const loadingDocs = ref(0)
const busy = ref(false)
const errorText = ref('')
const docs = ref<WorkbenchDoc[]>([])
const items = ref<WorkbenchItem[]>([])
const dragIndex = ref(-1)
const targetToolId = ref<ToolId | ''>('')
let uidCounter = 0

const selectedItems = computed(() => items.value.filter((item) => item.selected))
const activeItems = computed(() => items.value.filter((item) => !item.removed))
const selectedActiveItems = computed(() => items.value.filter((item) => item.selected && !item.removed))
const liveSummary = computed(() =>
  `${items.value.length} Seiten in der Werkbank, ${selectedItems.value.length} ausgewählt, ${items.value.length - activeItems.value.length} entfernt.`)

/**
 * Übergabefähig sind nur Werkzeuge mit einzelner PDF-Eingabe über die
 * gemeinsame FileDrop-Fläche — Mehrdatei- und Office-Werkzeuge könnten das
 * abgelegte Ergebnis nicht automatisch übernehmen.
 */
const HANDOFF_EXCLUDE = new Set<string>([
  'workbench', 'merge', 'split', 'pageEditor', 'pdfCompare', 'batch', 'pruefakte',
  'aiAssistant', 'imagesToPdf', 'wordToPdf', 'wordMerge', 'wordDiff', 'wordMeta',
  'excelMeta', 'officeToPdf',
])
const handoffGroups = computed(() => TOOL_GROUPS
  .map((group) => ({ title: group.title, tools: group.tools.filter((tool) => !HANDOFF_EXCLUDE.has(tool.id)) }))
  .filter((group) => group.tools.length > 0))

const DOC_BADGES = [
  'bg-blue-100 text-blue-800 dark:bg-blue-400/20 dark:text-blue-200',
  'bg-violet-100 text-violet-800 dark:bg-violet-400/20 dark:text-violet-200',
  'bg-emerald-100 text-emerald-800 dark:bg-emerald-400/20 dark:text-emerald-200',
  'bg-amber-100 text-amber-900 dark:bg-amber-400/20 dark:text-amber-200',
  'bg-rose-100 text-rose-800 dark:bg-rose-400/20 dark:text-rose-200',
  'bg-cyan-100 text-cyan-900 dark:bg-cyan-400/20 dark:text-cyan-200',
]

function docBadgeClass(index: number): string {
  return DOC_BADGES[index % DOC_BADGES.length] ?? DOC_BADGES[0]!
}

function docIndexOf(item: WorkbenchItem): number {
  return docs.value.findIndex((doc) => doc.uid === item.docUid)
}

function badgeClass(item: WorkbenchItem): string {
  if (item.docUid === null) return 'bg-gray-200 text-gray-800 dark:bg-white/15 dark:text-gray-200'
  return docBadgeClass(docIndexOf(item))
}

function badgeText(item: WorkbenchItem): string {
  if (item.docUid === null) return 'Leerseite'
  return `D${docIndexOf(item) + 1} · S${item.page}`
}

function thumbSrc(item: WorkbenchItem): string | null {
  if (item.docUid === null) return null
  const doc = docs.value.find((entry) => entry.uid === item.docUid)
  const thumb = doc?.thumbs[String(item.page)]
  return thumb ? `data:image/png;base64,${thumb}` : null
}

function thumbStyle(item: WorkbenchItem): Record<string, string> {
  if (!item.rotation) return {}
  const quer = item.rotation % 180 !== 0
  return { transform: `rotate(${item.rotation}deg)${quer ? ' scale(0.72)' : ''}` }
}

function cardLabel(item: WorkbenchItem, index: number): string {
  const source = item.docUid === null ? 'Leerseite' : `Dokument D${docIndexOf(item) + 1}, Seite ${item.page}`
  const state = `${item.rotation ? `, gedreht ${item.rotation} Grad` : ''}${item.removed ? ', entfernt' : ''}${item.selected ? ', ausgewählt' : ''}`
  return `Position ${index + 1} von ${items.value.length}: ${source}${state}. Eingabetaste wählt aus oder ab.`
}

function onFileSelect(event: Event): void {
  const element = event.target as HTMLInputElement
  const files = Array.from(element.files ?? [])
  element.value = ''
  if (files.length) void addFiles(files)
}

function onDroppedFiles(files: File[]): void {
  isDragging.value = false
  if (files.length) void addFiles(files)
}

async function addFiles(list: File[]): Promise<void> {
  errorText.value = ''
  for (const file of list) {
    if (docs.value.length >= MAX_DOCS) {
      notifications.warning('Dokumentlimit erreicht', `Maximal ${MAX_DOCS} Dokumente je Zusammenstellung.`)
      break
    }
    const validation = await validatePdfFile(file)
    if (!validation.valid) {
      notifications.error('Datei nicht angenommen', validation.message ?? `${file.name} ist keine gültige PDF-Datei.`)
      continue
    }
    if (file.size > currentFileLimit()) {
      notifications.error('Datei zu groß', `${file.name} ist ${formatFileSize(file.size)} groß. Zulässig sind maximal ${formatFileSize(currentFileLimit())}.`)
      continue
    }
    loadingDocs.value += 1
    try {
      const data = await getThumbnails(file) as { thumbnails: Record<string, string> }
      const pages = Object.keys(data.thumbnails).map(Number).sort((a, b) => a - b)
      if (!pages.length) {
        notifications.error('Keine Seiten', `${file.name} enthält keine lesbaren Seiten.`)
        continue
      }
      if (items.value.length + pages.length > MAX_PAGES) {
        notifications.warning('Seitenlimit erreicht', `Mit ${file.name} läge die Zusammenstellung über ${MAX_PAGES} Seiten.`)
        continue
      }
      const docUid = ++uidCounter
      docs.value.push({ uid: docUid, file, label: file.name, pages: pages.length, thumbs: data.thumbnails })
      items.value.push(...pages.map((page) => ({
        uid: ++uidCounter, docUid, page, rotation: 0, removed: false, selected: false,
      })))
      notifications.success('Dokument geladen', `${file.name}: ${pages.length} Seite(n) in der Werkbank.`)
    } catch (caught: unknown) {
      errorText.value = notifications.errorFromUnknown(caught, `Die Seitenvorschau für ${file.name} konnte nicht erzeugt werden.`)
    } finally {
      loadingDocs.value -= 1
    }
  }
}

function removeDoc(uid: number): void {
  docs.value = docs.value.filter((doc) => doc.uid !== uid)
  items.value = items.value.filter((item) => item.docUid !== uid)
}

function selectAll(selected: boolean): void {
  items.value.forEach((item) => { item.selected = selected })
}

function rotateSelection(delta: number): void {
  selectedItems.value.forEach((item) => { item.rotation = ((item.rotation + delta) % 360 + 360) % 360 })
}

function rotateItem(item: WorkbenchItem): void {
  item.rotation = (item.rotation + 90) % 360
}

function removeSelection(removed: boolean): void {
  selectedItems.value.forEach((item) => { item.removed = removed })
}

function duplicateSelection(): void {
  // Rückwärts, damit die Einfüge-Indizes durch frühere Duplikate nicht verrutschen.
  for (let index = items.value.length - 1; index >= 0; index -= 1) {
    const item = items.value[index]
    if (item?.selected) items.value.splice(index + 1, 0, { ...item, uid: ++uidCounter, selected: false })
  }
}

function insertBlank(): void {
  if (items.value.length >= MAX_PAGES) return
  const lastSelected = items.value.map((item) => item.selected).lastIndexOf(true)
  const at = lastSelected >= 0 ? lastSelected + 1 : items.value.length
  items.value.splice(at, 0, { uid: ++uidCounter, docUid: null, page: 0, rotation: 0, removed: false, selected: false })
}

function moveItem(index: number, direction: number): void {
  const target = index + direction
  if (target < 0 || target >= items.value.length) return
  const [moved] = items.value.splice(index, 1)
  if (moved) items.value.splice(target, 0, moved)
}

function reorderTo(targetIndex: number): void {
  if (dragIndex.value < 0 || dragIndex.value === targetIndex) return
  const [moved] = items.value.splice(dragIndex.value, 1)
  if (moved) items.value.splice(targetIndex, 0, moved)
  dragIndex.value = -1
}

/** Sendet nur die tatsächlich referenzierten Dokumente und nummeriert den Plan darauf um. */
async function requestCompose(subset: WorkbenchItem[]): Promise<Response> {
  const usedDocUids = [...new Set(subset.filter((item) => item.docUid !== null).map((item) => item.docUid as number))]
  const indexByUid = new Map<number, number>()
  const fd = new FormData()
  usedDocUids.forEach((uid, index) => {
    indexByUid.set(uid, index)
    const doc = docs.value.find((entry) => entry.uid === uid)
    if (doc) fd.append('files', doc.file)
  })
  const plan = subset.map((item) => {
    if (item.docUid === null) {
      const quer = item.rotation % 180 !== 0
      return quer ? { blank: true, width: 841.89, height: 595.28 } : { blank: true, width: 595.28, height: 841.89 }
    }
    const entry: Record<string, unknown> = { file: indexByUid.get(item.docUid), page: item.page }
    if (item.rotation) entry.rotate = item.rotation
    return entry
  })
  fd.append('plan', JSON.stringify(plan))
  return apiPost('/api/pdf-tools/compose', fd, { timeout: COMPOSE_TIMEOUT })
}

function guardSubset(subset: WorkbenchItem[]): boolean {
  if (!subset.length) return false
  if (!subset.some((item) => item.docUid !== null)) {
    errorText.value = 'Mindestens eine Dokumentseite wird benötigt — nur Leerseiten ergeben keine Zusammenstellung.'
    return false
  }
  return true
}

async function composeAndDownload(subset: WorkbenchItem[], filename: string): Promise<void> {
  if (!guardSubset(subset)) return
  busy.value = true
  errorText.value = ''
  try {
    const response = await requestCompose(subset)
    await downloadBlob(response, filename)
  } catch (caught: unknown) {
    errorText.value = notifications.errorFromUnknown(caught, 'Die Zusammenstellung ist fehlgeschlagen.')
  } finally {
    busy.value = false
  }
}

async function handOff(): Promise<void> {
  const target = targetToolId.value
  if (!target || !guardSubset(activeItems.value)) return
  busy.value = true
  errorText.value = ''
  try {
    const response = await requestCompose(activeItems.value)
    const blob = await response.blob()
    setPendingHandoff(new File([blob], 'werkbank.pdf', { type: 'application/pdf' }))
    emit('switch-tool', target)
  } catch (caught: unknown) {
    errorText.value = notifications.errorFromUnknown(caught, 'Die Übergabe ist fehlgeschlagen.')
  } finally {
    busy.value = false
  }
}
</script>
