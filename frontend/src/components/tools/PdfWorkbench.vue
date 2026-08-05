<template>
  <!--
    Vollbild-Arbeitsplatz: öffnet sich sofort mit dem Werkzeug (nicht erst nach
    dem ersten Upload). Kopfleiste oben, Seitenübersicht links, große zoombare
    Seitenansicht rechts. „Zurück" verlässt den Arbeitsplatz.
  -->
  <div class="fixed inset-0 z-40 flex flex-col bg-gray-100 dark:bg-gray-950" role="dialog" aria-modal="true" aria-label="Werkbank — PDF-Arbeitsplatz">
    <!-- Kopf-/Werkzeugleiste -->
    <header class="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-white/95 px-3 py-2 backdrop-blur dark:border-gray-700 dark:bg-gray-900/95">
      <UiButton size="sm" variant="ghost" @click="$emit('back')">‹ Zurück</UiButton>
      <span class="flex items-center gap-1.5 font-semibold text-gray-950 dark:text-white"><span aria-hidden="true">🛠️</span> Werkbank</span>

      <input ref="fileInput" type="file" accept=".pdf" multiple class="hidden" @change="onFileSelect" />
      <UiButton size="sm" variant="secondary" :loading="loadingDocs > 0" @click="fileInput?.click()">+ PDF</UiButton>

      <span
        v-for="(doc, index) in docs"
        :key="doc.uid"
        class="hidden items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-black/5 md:inline-flex dark:ring-white/10"
        :class="docBadgeClass(index)"
      >
        <strong>D{{ index + 1 }}</strong>
        <span class="max-w-32 truncate">{{ doc.label }}</span>
        <button
          type="button"
          class="ml-0.5 grid h-4 w-4 place-items-center rounded-full transition hover:bg-black/10 dark:hover:bg-white/20"
          :aria-label="`Dokument D${index + 1} (${doc.label}) samt Seiten aus der Werkbank entfernen`"
          @click="removeDoc(doc.uid)"
        >×</button>
      </span>

      <span class="flex-1"></span>

      <template v-if="items.length">
        <UiButton size="sm" variant="secondary" @click="selectAll(selectedItems.length < items.length)">
          {{ selectedItems.length < items.length ? 'Alle auswählen' : 'Auswahl aufheben' }}
        </UiButton>
        <span class="text-xs font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ selectedItems.length }} ausgewählt</span>
        <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" title="Auswahl links drehen" @click="rotateSelection(-90)">↺</UiButton>
        <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" title="Auswahl rechts drehen" @click="rotateSelection(90)">↻</UiButton>
        <UiButton size="sm" variant="secondary" :disabled="!selectedItems.length" title="Auswahl duplizieren" @click="duplicateSelection">⧉</UiButton>
        <UiButton size="sm" variant="secondary" title="Leerseite einfügen" @click="insertBlank">➕</UiButton>
        <UiButton size="sm" variant="danger" :disabled="!selectedItems.length" title="Auswahl entfernen" @click="removeSelection(true)">✕</UiButton>
        <span class="mx-1 h-6 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
        <UiButton size="sm" variant="primary" :loading="busy" :disabled="!activeItems.length" @click="composeAndDownload(activeItems, 'werkbank.pdf')">
          Ergebnis ({{ activeItems.length }} S.)
        </UiButton>
        <UiButton v-if="selectedActiveItems.length" size="sm" variant="secondary" :disabled="busy" @click="composeAndDownload(selectedActiveItems, 'werkbank-auswahl.pdf')">
          Auswahl exportieren ({{ selectedActiveItems.length }})
        </UiButton>
        <label class="flex items-center gap-1.5 text-sm font-medium text-gray-800 dark:text-gray-100">
          <span class="sr-only">Ergebnis weiterbearbeiten in</span>
          <select
            v-model="targetToolId"
            class="rounded-xl bg-white px-2.5 py-1.5 text-sm font-medium text-gray-950 ring-1 ring-gray-400/70 transition focus:ring-2 focus:ring-primary-500 dark:bg-gray-900 dark:text-white dark:ring-gray-600"
          >
            <option value="" disabled>Weiterbearbeiten in …</option>
            <optgroup v-for="group in handoffGroups" :key="group.title" :label="group.title">
              <option v-for="tool in group.tools" :key="tool.id" :value="tool.id">{{ tool.label }}</option>
            </optgroup>
          </select>
        </label>
        <UiButton size="sm" variant="secondary" :disabled="busy || !targetToolId || !activeItems.length" @click="handOff">Übergeben →</UiButton>
      </template>
    </header>

    <!-- Rumpf -->
    <div class="flex min-h-0 flex-1">
      <!-- Seitenübersicht -->
      <aside
        v-if="items.length"
        class="w-44 shrink-0 space-y-2 overflow-y-auto border-r border-gray-200 bg-white/60 p-2 sm:w-56 dark:border-gray-700 dark:bg-gray-900/50"
        role="list"
        aria-label="Seitenübersicht. Klick zeigt die Seite groß, das Häkchen wählt für Mehrfach-Aktionen aus. Reihenfolge per Ziehen ändern."
      >
        <div
          v-for="(item, index) in items"
          :key="item.uid"
          role="listitem"
          class="rounded-xl bg-white p-1.5 shadow-apple-sm ring-1 transition dark:bg-gray-900"
          :class="[
            item.uid === focusedUid ? 'ring-2 ring-primary-500' : item.selected ? 'ring-2 ring-primary-300 dark:ring-primary-700' : 'ring-gray-300 dark:ring-gray-600',
            item.removed ? 'opacity-55 grayscale' : '',
            dragIndex === index ? 'opacity-60' : '',
          ]"
          draggable="true"
          @dragstart="dragIndex = index"
          @dragend="dragIndex = -1"
          @dragover.prevent
          @drop.prevent="reorderTo(index)"
        >
          <div class="flex items-center justify-between gap-1 px-0.5 pb-1">
            <span class="rounded-full px-1.5 py-0.5 text-[10px] font-semibold" :class="badgeClass(item)">{{ badgeText(item) }}</span>
            <span v-if="item.rotation" class="text-[10px] font-semibold text-gray-600 dark:text-gray-300">{{ item.rotation }}°</span>
            <span class="text-[10px] font-medium tabular-nums text-gray-600 dark:text-gray-300">{{ index + 1 }}</span>
            <button
              type="button"
              class="grid h-5 w-5 place-items-center rounded-md text-[11px] ring-1 transition"
              :class="item.selected ? 'bg-primary-600 text-white ring-primary-600' : 'text-gray-500 ring-gray-300 hover:ring-primary-400 dark:text-gray-300 dark:ring-gray-600'"
              :aria-pressed="item.selected"
              :aria-label="`Position ${index + 1} ${item.selected ? 'abwählen' : 'für Mehrfach-Aktionen auswählen'}`"
              @click.stop="item.selected = !item.selected"
            >✓</button>
          </div>
          <button
            type="button"
            class="relative block h-32 w-full overflow-hidden rounded-lg bg-gray-100 outline-none transition focus-visible:ring-2 focus-visible:ring-primary-500 dark:bg-white/10"
            :aria-label="cardLabel(item, index)"
            :aria-current="item.uid === focusedUid ? 'true' : undefined"
            @click="focusItem(item)"
          >
            <img v-if="thumbSrc(item)" :src="thumbSrc(item) ?? undefined" alt="" class="mx-auto h-full object-contain" :style="thumbStyle(item)" />
            <span v-else class="grid h-full place-items-center text-3xl" aria-hidden="true">📄</span>
            <span v-if="item.removed" class="absolute inset-0 grid place-items-center bg-white/75 text-xs font-bold text-rose-700 dark:bg-gray-950/75 dark:text-rose-300">Entfernt</span>
          </button>
        </div>
      </aside>

      <!-- Große Seitenansicht -->
      <main class="min-w-0 flex-1 overflow-auto p-3 sm:p-4">
        <!-- Leerzustand: Ablagefläche mitten im Arbeitsplatz -->
        <div v-if="!docs.length" class="mx-auto flex h-full max-w-2xl items-center">
          <UiDropZone
            class="w-full"
            :active="isDragging"
            :accepted="false"
            :invalid="Boolean(errorText)"
            @drag-active="isDragging = $event"
            @drop="onDroppedFiles"
          >
            <div>
              <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-primary-50 text-3xl text-primary-700 shadow-sm dark:bg-primary-500/15 dark:text-primary-300" aria-hidden="true">🛠️</div>
              <p class="mt-3 text-lg font-semibold text-gray-950 dark:text-white">PDFs hierher ziehen</p>
              <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Mehrere Dateien gleichzeitig möglich — jede Seite wird einzeln bearbeitbar, das Ergebnis lässt sich an jedes Werkzeug übergeben.</p>
              <UiButton variant="primary" class="mt-4" :loading="loadingDocs > 0" @click="fileInput?.click()">Dateien auswählen</UiButton>
            </div>
          </UiDropZone>
        </div>

        <template v-else>
          <div v-if="focusedItem" class="space-y-3">
            <!-- Schnellaktionen für die fokussierte Seite -->
            <div class="flex flex-wrap items-center gap-2 text-sm">
              <span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="badgeClass(focusedItem)">{{ badgeText(focusedItem) }}</span>
              <span class="text-xs font-medium tabular-nums text-gray-600 dark:text-gray-300">Position {{ focusedIndex + 1 }} / {{ items.length }}</span>
              <span class="mx-1 h-5 w-px bg-gray-300 dark:bg-gray-600" aria-hidden="true"></span>
              <UiButton size="sm" variant="secondary" title="Seite um 90 Grad drehen" @click="rotateItem(focusedItem)">⟳ Drehen{{ focusedItem.rotation ? ` (${focusedItem.rotation}°)` : '' }}</UiButton>
              <UiButton size="sm" variant="secondary" @click="duplicateFocused">⧉ Duplizieren</UiButton>
              <UiButton size="sm" :variant="focusedItem.removed ? 'secondary' : 'danger'" @click="focusedItem.removed = !focusedItem.removed">
                {{ focusedItem.removed ? '⤺ Wiederherstellen' : '✕ Entfernen' }}
              </UiButton>
              <UiButton size="sm" variant="secondary" :disabled="focusedIndex <= 0" title="Nach vorn verschieben" @click="moveItem(focusedIndex, -1)">←</UiButton>
              <UiButton size="sm" variant="secondary" :disabled="focusedIndex >= items.length - 1" title="Nach hinten verschieben" @click="moveItem(focusedIndex, 1)">→</UiButton>
            </div>

            <PdfViewer
              v-if="focusedItem.docUid !== null && focusedDocFile"
              v-model="viewerPage"
              :source="focusedDocFile"
              :rotation="focusedItem.rotation"
              @update:model-value="onViewerPageChange"
            />
            <div v-else class="grid h-[70vh] place-items-center rounded-[1.35rem] bg-white shadow-apple ring-1 ring-gray-300 dark:bg-gray-100 dark:ring-gray-600">
              <p class="text-sm font-medium text-gray-500">Leerseite ({{ focusedItem.rotation % 180 !== 0 ? 'A4 quer' : 'A4 hoch' }})</p>
            </div>
          </div>
          <p v-else class="mt-10 text-center text-sm text-gray-600 dark:text-gray-300">Links eine Seite anklicken, um sie groß anzuzeigen.</p>
        </template>

        <UiAlert v-if="errorText" tone="danger" class="mt-3">{{ errorText }}</UiAlert>
      </main>
    </div>

    <p class="sr-only" aria-live="polite" aria-atomic="true">{{ liveSummary }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import PdfViewer from '@/components/PdfViewer.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
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

// ── Fokus + Großansicht ──────────────────────────────────────
const focusedUid = ref<number | null>(null)
const viewerPage = ref(1)

const focusedItem = computed(() => items.value.find((item) => item.uid === focusedUid.value) ?? null)
const focusedIndex = computed(() => items.value.findIndex((item) => item.uid === focusedUid.value))
const focusedDocFile = computed(() => {
  const item = focusedItem.value
  if (!item || item.docUid === null) return null
  return docs.value.find((doc) => doc.uid === item.docUid)?.file ?? null
})

function focusItem(item: WorkbenchItem): void {
  focusedUid.value = item.uid
  if (item.docUid !== null) viewerPage.value = item.page
}

/** Blättern im Viewer folgt der Zusammenstellung: existiert die Seite als
 *  Eintrag desselben Dokuments, wird sie fokussiert (erste Fundstelle). */
function onViewerPageChange(page: number): void {
  const current = focusedItem.value
  if (!current || current.docUid === null) return
  const match = items.value.find((item) => item.docUid === current.docUid && item.page === page)
  if (match) focusedUid.value = match.uid
}

function duplicateFocused(): void {
  const index = focusedIndex.value
  const item = focusedItem.value
  if (index < 0 || !item) return
  items.value.splice(index + 1, 0, { ...item, uid: ++uidCounter, selected: false })
}

// Hinter dem Vollbild-Arbeitsplatz darf die Seite nicht mitscrollen.
onMounted(() => { document.body.style.overflow = 'hidden' })
onBeforeUnmount(() => { document.body.style.overflow = '' })

const selectedItems = computed(() => items.value.filter((item) => item.selected))
const activeItems = computed(() => items.value.filter((item) => !item.removed))
const selectedActiveItems = computed(() => items.value.filter((item) => item.selected && !item.removed))
const liveSummary = computed(() =>
  `${items.value.length} Seiten in der Werkbank, ${selectedItems.value.length} ausgewählt, ${items.value.length - activeItems.value.length} entfernt.`)

/**
 * Übergabefähig sind Werkzeuge, deren Eingabe die gemeinsame FileDrop-Fläche
 * mit einzelner PDF ist — nur dort holt FileDrop die Übergabe automatisch ab.
 * Der PDF-Vergleich nutzt FileDrop für Datei A und ist damit übergabefähig.
 */
const HANDOFF_EXCLUDE = new Set<string>([
  'workbench', 'merge', 'split', 'pageEditor', 'batch', 'pruefakte',
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
  return `Position ${index + 1} von ${items.value.length}: ${source}${state}. Eingabetaste zeigt die Seite groß an.`
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
      const newItems = pages.map((page) => ({
        uid: ++uidCounter, docUid, page, rotation: 0, removed: false, selected: false,
      }))
      items.value.push(...newItems)
      if (focusedUid.value === null && newItems[0]) focusItem(newItems[0])
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
  if (focusedItem.value === null) focusedUid.value = items.value[0]?.uid ?? null
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
  const blank: WorkbenchItem = { uid: ++uidCounter, docUid: null, page: 0, rotation: 0, removed: false, selected: false }
  items.value.splice(at, 0, blank)
  focusedUid.value = blank.uid
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
