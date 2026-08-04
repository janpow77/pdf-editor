<template>
  <div>
    <!--
      Der Fokusmodus umschließt jedes Werkzeug mit derselben Breadcrumb- und
      Oberflächenstruktur. Die Fachkomponenten müssen dadurch weder Kategorien
      kennen noch eigene Seitenrahmen implementieren.
    -->
    <section v-if="activeEntry" class="space-y-3">
      <nav aria-label="Brotkrümelnavigation" class="px-1">
        <ol class="flex flex-wrap items-center gap-1.5 text-sm font-medium text-gray-600 dark:text-gray-300">
          <li>
            <button
              type="button"
              class="rounded-lg px-2 py-1 transition hover:bg-black/5 hover:text-gray-950 dark:hover:bg-white/10 dark:hover:text-white"
              @click="closeTool"
            >Startseite</button>
          </li>
          <li aria-hidden="true" class="text-gray-400 dark:text-gray-500">›</li>
          <li class="px-1 text-gray-600 dark:text-gray-300">{{ activeEntry.group.title }}</li>
          <li aria-hidden="true" class="text-gray-400 dark:text-gray-500">›</li>
          <li aria-current="page" class="truncate px-1 font-semibold text-gray-950 dark:text-white">
            {{ activeEntry.tool.label }}
          </li>
        </ol>
      </nav>

      <div class="apple-workspace min-h-[70vh] p-4 sm:p-6">
        <component :is="toolComponents[activeEntry.tool.id]" @back="closeTool" />
      </div>
    </section>

    <div v-else class="space-y-8">
      <!--
        Das Raster bleibt die platzsparende Standardansicht. Der segmentierte
        Schalter erhält das Rolodex als gleichberechtigte Alternative. Ein
        blockierter Browser-Speicher beeinflusst nur die Persistenz, niemals die
        Funktionsfähigkeit der Oberfläche.
      -->
      <div v-if="!normalizedSearch" class="flex justify-end">
        <div
          class="inline-flex rounded-full bg-gray-200/80 p-1 shadow-inner ring-1 ring-black/5 dark:bg-white/10 dark:ring-white/10"
          role="group"
          aria-label="Darstellung der Werkzeuge"
        >
          <button
            type="button"
            class="rounded-full px-4 py-2 text-sm font-semibold transition duration-200"
            :class="viewMode === 'grid'
              ? 'bg-white text-gray-950 shadow-sm dark:bg-white dark:text-gray-950'
              : 'text-gray-600 hover:text-gray-950 dark:text-gray-300 dark:hover:text-white'"
            :aria-pressed="viewMode === 'grid'"
            @click="setViewMode('grid')"
          >▦ Raster</button>
          <button
            type="button"
            class="rounded-full px-4 py-2 text-sm font-semibold transition duration-200"
            :class="viewMode === 'rolodex'
              ? 'bg-white text-gray-950 shadow-sm dark:bg-white dark:text-gray-950'
              : 'text-gray-600 hover:text-gray-950 dark:text-gray-300 dark:hover:text-white'"
            :aria-pressed="viewMode === 'rolodex'"
            @click="setViewMode('rolodex')"
          >▤ Rolodex</button>
        </div>
      </div>

      <!-- Raster: effizient, responsiv und als Standard gewählt. -->
      <template v-if="effectiveViewMode === 'grid'">
        <section
          v-for="group in filteredGroups"
          :key="group.key"
          :aria-labelledby="`werkzeuggruppe-${group.key}`"
        >
          <div class="mb-4 flex flex-wrap items-end justify-between gap-2 px-1">
            <div class="flex items-center gap-3">
              <span
                class="grid h-10 w-10 place-items-center rounded-2xl text-xl shadow-sm"
                :class="groupIconClass(group.key)"
                aria-hidden="true"
              >{{ group.icon }}</span>
              <div>
                <h2
                  :id="`werkzeuggruppe-${group.key}`"
                  class="text-lg font-semibold tracking-[-0.025em] text-gray-950 dark:text-white"
                >{{ group.title }}</h2>
                <p class="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {{ group.tools.length }} {{ group.tools.length === 1 ? 'Werkzeug' : 'Werkzeuge' }}
                </p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
            <button
              v-for="tool in group.tools"
              :key="tool.id"
              type="button"
              class="group relative min-h-44 overflow-hidden rounded-[1.35rem] bg-white/82 p-5 text-left
                     shadow-apple-sm ring-1 ring-gray-300/80 backdrop-blur-xl transition duration-200
                     hover:-translate-y-1 hover:shadow-apple focus-visible:ring-2 focus-visible:ring-primary-500
                     dark:bg-white/[0.075] dark:ring-gray-600 dark:hover:bg-white/[0.105]"
              :class="isLocked(tool.id) ? 'opacity-75' : ''"
              :aria-label="`${tool.label}: ${isLocked(tool.id) ? LOCK_HINT : tool.description}`"
              @click="openTool(tool.id)"
            >
              <span
                class="mb-5 grid h-12 w-12 place-items-center rounded-2xl text-2xl shadow-sm transition duration-200 group-hover:scale-105"
                :class="groupIconClass(group.key)"
                aria-hidden="true"
              >{{ tool.icon }}</span>

              <span class="block text-base font-semibold tracking-[-0.02em] text-gray-950 dark:text-white">
                {{ tool.label }}
              </span>
              <span class="mt-1.5 block text-sm leading-5 text-gray-600 dark:text-gray-300">
                {{ tool.description }}
              </span>

              <span
                v-if="isLocked(tool.id)"
                class="mt-4 inline-flex items-center gap-1.5 rounded-full bg-primary-50 px-2.5 py-1 text-xs font-semibold text-primary-700 dark:bg-primary-500/15 dark:text-primary-300"
              ><span aria-hidden="true">🔒</span> Anmeldung erforderlich</span>
              <span
                v-else
                class="absolute bottom-5 right-5 grid h-8 w-8 place-items-center rounded-full bg-gray-950 text-white opacity-0 transition duration-200 group-hover:opacity-100 dark:bg-white dark:text-gray-950"
                aria-hidden="true"
              >→</span>
            </button>
          </div>
        </section>
      </template>

      <!--
        Das Rolodex verwendet bewusst keine nachgebildete Listbox. Die Karten
        bleiben native Buttons; der umgebende Bereich bietet zusätzlich
        Pfeiltasten, Pos1, Ende und Eingabe. Dadurch entstehen keine
        widersprüchlichen Rollen zwischen `button`, `listbox` und `option`.
      -->
      <section v-else class="space-y-5" aria-label="Rolodex-Ansicht der Werkzeuge">
        <nav class="flex flex-wrap justify-center gap-2" aria-label="Werkzeugkategorie auswählen">
          <button
            v-for="group in availableGroups"
            :key="group.key"
            type="button"
            class="rounded-full px-3.5 py-2 text-sm font-semibold shadow-sm ring-1 transition duration-200"
            :class="group.key === activeGroupKey
              ? 'bg-gray-950 text-white ring-gray-950 dark:bg-white dark:text-gray-950 dark:ring-white'
              : 'bg-white/75 text-gray-700 ring-gray-400/70 hover:bg-white hover:text-gray-950 dark:bg-white/10 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-white/15'"
            :aria-current="group.key === activeGroupKey ? 'true' : undefined"
            @click="setGroup(group.key)"
          >
            <span aria-hidden="true">{{ group.icon }}</span> {{ group.title }}
          </button>
        </nav>

        <div
          ref="rolodexEl"
          class="relative h-[22rem] overflow-hidden rounded-[1.75rem] bg-white/45 shadow-inner ring-1 ring-black/5 outline-none backdrop-blur-xl dark:bg-white/[0.035] dark:ring-white/10"
          style="perspective: 1400px"
          tabindex="0"
          role="region"
          :aria-label="`Werkzeug-Rolodex ${activeGroup?.title ?? ''}. Pfeiltasten zum Blättern, Pos1 und Ende zum Springen, Eingabetaste zum Öffnen.`"
          @keydown.left.prevent="step(-1)"
          @keydown.right.prevent="step(1)"
          @keydown.home.prevent="selectRolodexIndex(0)"
          @keydown.end.prevent="selectRolodexIndex(Math.max(0, groupTools.length - 1))"
          @keydown.enter.prevent="openActiveRolodexTool"
          @wheel.prevent="onWheel"
        >
          <button
            v-for="(tool, index) in groupTools"
            :key="tool.id"
            type="button"
            class="absolute left-1/2 top-1/2 flex h-64 w-60 flex-col rounded-[1.5rem] bg-white p-5 text-left
                   shadow-apple ring-1 ring-gray-300 transition-all duration-300 ease-out will-change-transform
                   focus-visible:ring-2 focus-visible:ring-primary-500 dark:bg-gray-900 dark:ring-gray-600"
            :class="isLocked(tool.id) ? 'grayscale' : ''"
            :style="cardStyle(index)"
            :tabindex="index === rolodexIndex ? 0 : -1"
            :aria-current="index === rolodexIndex ? 'true' : undefined"
            :aria-label="`${tool.label}: ${isLocked(tool.id) ? LOCK_HINT : tool.description}`"
            @focus="selectRolodexIndex(index)"
            @click="index === rolodexIndex ? openTool(tool.id) : selectRolodexIndex(index)"
          >
            <span
              class="grid h-14 w-14 place-items-center rounded-2xl text-3xl shadow-sm"
              :class="groupIconClass(activeGroupKey)"
              aria-hidden="true"
            >{{ tool.icon }}</span>
            <span class="mt-5 text-lg font-semibold tracking-[-0.025em] text-gray-950 dark:text-white">
              {{ tool.label }}
            </span>
            <span class="mt-2 text-sm leading-5 text-gray-600 dark:text-gray-300">{{ tool.description }}</span>
            <span v-if="isLocked(tool.id)" class="mt-auto text-xs font-semibold text-primary-700 dark:text-primary-300">
              🔒 Anmeldung erforderlich
            </span>
            <span v-else class="mt-auto text-sm font-semibold text-primary-600 dark:text-primary-400">Öffnen →</span>
          </button>

          <p class="sr-only" aria-live="polite">
            {{ activeRolodexTool ? `${activeRolodexTool.label}, ${rolodexIndex + 1} von ${groupTools.length}` : 'Keine Werkzeuge verfügbar' }}
          </p>
        </div>

        <div class="flex items-center justify-center gap-4">
          <button
            type="button"
            class="apple-icon-button"
            :disabled="rolodexIndex === 0"
            aria-label="Vorheriges Werkzeug"
            @click="step(-1)"
          >←</button>
          <span class="min-w-24 text-center text-sm font-medium tabular-nums text-gray-600 dark:text-gray-300">
            {{ groupTools.length ? rolodexIndex + 1 : 0 }} / {{ groupTools.length }}
          </span>
          <button
            type="button"
            class="apple-icon-button"
            :disabled="rolodexIndex >= groupTools.length - 1"
            aria-label="Nächstes Werkzeug"
            @click="step(1)"
          >→</button>
        </div>
      </section>

      <div
        v-if="filteredGroups.length === 0"
        class="apple-surface mx-auto max-w-xl px-6 py-12 text-center"
        role="status"
      >
        <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gray-100 text-2xl dark:bg-white/10" aria-hidden="true">⌕</div>
        <h2 class="mt-4 text-lg font-semibold text-gray-950 dark:text-white">Kein Werkzeug gefunden</h2>
        <p class="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-300">
          Prüfen Sie die Schreibweise oder verwenden Sie einen allgemeineren Begriff.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, type Component } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkspace } from '@/composables/useWorkspace'
import { isAuthenticated } from '@/lib/auth'
import { getHealth } from '@/lib/health'
import { findTool, TOOL_GROUPS, type ToolDefinition } from '@/lib/toolCatalog'

const props = withDefaults(defineProps<{ searchQuery?: string }>(), { searchQuery: '' })
const router = useRouter()
const activeTool = ref<string | null>(null)
const aiAvailable = ref(false)
const lockedTools = ref<Set<string>>(new Set())
const { openWorkspace, closeWorkspace } = useWorkspace()

const LOCK_HINT = 'Dieses Werkzeug steht nur angemeldeten Nutzern zur Verfügung – ein Konto ist kostenlos.'
const VIEW_KEY = 'pdfapp_view_mode'
const GROUP_KEY = 'pdfapp_rolodex_group'
type ViewMode = 'grid' | 'rolodex'

/** Liest eine Präferenz, ohne SSR, Privatmodus oder blockierten Speicher zu gefährden. */
function readPreference(key: string): string | null {
  if (typeof window === 'undefined') return null
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

/** Persistenz ist Komfort: Fehler dürfen niemals die Werkzeugauswahl blockieren. */
function writePreference(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // Die aktuelle Sitzung funktioniert weiter; lediglich die Auswahl wird nicht gespeichert.
  }
}

const viewMode = ref<ViewMode>(readPreference(VIEW_KEY) === 'rolodex' ? 'rolodex' : 'grid')
const activeGroupKey = ref(readPreference(GROUP_KEY) ?? 'bearbeiten')
const rolodexIndex = ref(0)
const rolodexEl = ref<HTMLElement | null>(null)

const activeEntry = computed(() => findTool(activeTool.value))
const normalizedSearch = computed(() => props.searchQuery.trim().toLocaleLowerCase('de'))
const effectiveViewMode = computed<ViewMode>(() => normalizedSearch.value ? 'grid' : viewMode.value)

const availableGroups = computed(() => TOOL_GROUPS
  .map((group) => ({
    ...group,
    tools: group.tools.filter((tool) => !tool.requiresAi || aiAvailable.value),
  }))
  .filter((group) => group.tools.length > 0))

const filteredGroups = computed(() => {
  const query = normalizedSearch.value
  return availableGroups.value
    .map((group) => ({
      ...group,
      tools: group.tools.filter((tool) => {
        if (!query) return true
        return `${tool.label} ${tool.description} ${group.title}`.toLocaleLowerCase('de').includes(query)
      }),
    }))
    .filter((group) => group.tools.length > 0)
})

const activeGroup = computed(() =>
  availableGroups.value.find((group) => group.key === activeGroupKey.value)
  ?? availableGroups.value[0]
  ?? null,
)
const groupTools = computed<ToolDefinition[]>(() => activeGroup.value?.tools ?? [])
const activeRolodexTool = computed(() => groupTools.value[rolodexIndex.value] ?? null)

function isLocked(id: string): boolean {
  return lockedTools.value.has(id) && !isAuthenticated.value
}

function scrollToTop(): void {
  if (typeof window !== 'undefined') window.scrollTo({ top: 0, behavior: 'smooth' })
}

function openTool(id: string): void {
  if (isLocked(id)) {
    void router.push({ path: '/login', query: { werkzeug: id } })
    return
  }

  const entry = findTool(id)
  if (!entry) return
  activeTool.value = id
  openWorkspace({ toolId: id, toolName: entry.tool.label, groupName: entry.group.title })
  scrollToTop()
}

function closeTool(): void {
  activeTool.value = null
  closeWorkspace()
  scrollToTop()
}

function setViewMode(mode: ViewMode): void {
  viewMode.value = mode
  writePreference(VIEW_KEY, mode)
  if (mode === 'rolodex') {
    rolodexIndex.value = Math.min(rolodexIndex.value, Math.max(0, groupTools.value.length - 1))
  }
}

function setGroup(key: string): void {
  activeGroupKey.value = key
  writePreference(GROUP_KEY, key)
  rolodexIndex.value = 0
  rolodexEl.value?.focus()
}

function selectRolodexIndex(index: number): void {
  rolodexIndex.value = Math.max(0, Math.min(index, Math.max(0, groupTools.value.length - 1)))
}

function step(direction: number): void {
  selectRolodexIndex(rolodexIndex.value + direction)
}

function openActiveRolodexTool(): void {
  const tool = activeRolodexTool.value
  if (tool) openTool(tool.id)
}

let wheelLock = 0
function onWheel(event: WheelEvent): void {
  const now = Date.now()
  if (now - wheelLock < 160) return
  wheelLock = now
  const delta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY
  if (delta > 0) step(1)
  else if (delta < 0) step(-1)
}

function cardStyle(index: number): Record<string, string> {
  const offset = index - rolodexIndex.value
  const distance = Math.abs(offset)
  const rotateY = Math.max(-52, Math.min(52, offset * -31))
  const translateZ = -distance * 105
  const scale = offset === 0 ? 1 : Math.max(0.76, 1 - distance * 0.08)
  return {
    transform: `translate(-50%, -50%) translateX(${offset * 178}px) translateZ(${translateZ}px) rotateY(${rotateY}deg) scale(${scale})`,
    zIndex: String(100 - distance),
    cursor: offset === 0 ? 'pointer' : 'ew-resize',
  }
}

/** Farbflächen bleiben bewusst weich und systematisch je Kategorie. */
function groupIconClass(key: string): string {
  return {
    bearbeiten: 'bg-blue-100 text-blue-700 dark:bg-blue-400/15 dark:text-blue-300',
    seiten: 'bg-violet-100 text-violet-700 dark:bg-violet-400/15 dark:text-violet-300',
    umwandeln: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300',
    schuetzen: 'bg-rose-100 text-rose-700 dark:bg-rose-400/15 dark:text-rose-300',
    stempel: 'bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-300',
    pruefen: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-400/15 dark:text-cyan-300',
    office: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-400/15 dark:text-indigo-300',
  }[key] ?? 'bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300'
}

// Werkzeuge werden erst beim Öffnen geladen. Dadurch bleibt das große Raster
// trotz pdf.js und der vielen Fachmodule schnell und reagiert unmittelbar.
const toolComponents: Record<string, Component> = {
  merge: defineAsyncComponent(() => import('@/components/tools/PdfMerge.vue')),
  split: defineAsyncComponent(() => import('@/components/tools/PdfSplit.vue')),
  rotate: defineAsyncComponent(() => import('@/components/tools/PdfRotate.vue')),
  toImages: defineAsyncComponent(() => import('@/components/tools/PdfToImages.vue')),
  compress: defineAsyncComponent(() => import('@/components/tools/PdfCompress.vue')),
  watermark: defineAsyncComponent(() => import('@/components/tools/PdfWatermark.vue')),
  imagesToPdf: defineAsyncComponent(() => import('@/components/tools/ImagesToPdf.vue')),
  pageEditor: defineAsyncComponent(() => import('@/components/tools/PdfPageEditor.vue')),
  metadata: defineAsyncComponent(() => import('@/components/tools/PdfMetadata.vue')),
  pdfCompare: defineAsyncComponent(() => import('@/components/tools/PdfCompare.vue')),
  protect: defineAsyncComponent(() => import('@/components/tools/PdfProtect.vue')),
  pdfToWord: defineAsyncComponent(() => import('@/components/tools/PdfToWord.vue')),
  pdfToExcel: defineAsyncComponent(() => import('@/components/tools/PdfToExcel.vue')),
  textEditor: defineAsyncComponent(() => import('@/components/tools/PdfTextEditor.vue')),
  pageNumbers: defineAsyncComponent(() => import('@/components/tools/PdfPageNumbers.vue')),
  headerFooter: defineAsyncComponent(() => import('@/components/tools/PdfHeaderFooter.vue')),
  searchReplace: defineAsyncComponent(() => import('@/components/tools/PdfSearchReplace.vue')),
  redact: defineAsyncComponent(() => import('@/components/tools/PdfRedact.vue')),
  flatten: defineAsyncComponent(() => import('@/components/tools/PdfFlatten.vue')),
  toText: defineAsyncComponent(() => import('@/components/tools/PdfToText.vue')),
  bates: defineAsyncComponent(() => import('@/components/tools/PdfBates.vue')),
  formFill: defineAsyncComponent(() => import('@/components/tools/PdfFormFill.vue')),
  formDesigner: defineAsyncComponent(() => import('@/components/tools/PdfFormDesigner.vue')),
  pdfa: defineAsyncComponent(() => import('@/components/tools/PdfPdfa.vue')),
  signImage: defineAsyncComponent(() => import('@/components/tools/PdfSignImage.vue')),
  imageReplace: defineAsyncComponent(() => import('@/components/tools/PdfImageReplace.vue')),
  annotate: defineAsyncComponent(() => import('@/components/tools/PdfAnnotate.vue')),
  signDigital: defineAsyncComponent(() => import('@/components/tools/PdfSignDigital.vue')),
  scanOptimize: defineAsyncComponent(() => import('@/components/tools/PdfScanOptimize.vue')),
  batch: defineAsyncComponent(() => import('@/components/tools/PdfBatch.vue')),
  tocEditor: defineAsyncComponent(() => import('@/components/tools/PdfTocEditor.vue')),
  ocr: defineAsyncComponent(() => import('@/components/tools/PdfOcr.vue')),
  pdfExport: defineAsyncComponent(() => import('@/components/tools/PdfExport.vue')),
  clean: defineAsyncComponent(() => import('@/components/tools/PdfClean.vue')),
  permissions: defineAsyncComponent(() => import('@/components/tools/PdfPermissions.vue')),
  verifySignatures: defineAsyncComponent(() => import('@/components/tools/PdfVerifySignatures.vue')),
  insertBlank: defineAsyncComponent(() => import('@/components/tools/PdfInsertBlank.vue')),
  pruefakte: defineAsyncComponent(() => import('@/components/tools/PdfPruefakte.vue')),
  qualityCheck: defineAsyncComponent(() => import('@/components/tools/PdfQualityCheck.vue')),
  aiAssistant: defineAsyncComponent(() => import('@/components/tools/PdfAiAssistant.vue')),
  officeToPdf: defineAsyncComponent(() => import('@/components/tools/OfficeToPdf.vue')),
  wordToPdf: defineAsyncComponent(() => import('@/components/tools/WordToPdf.vue')),
  wordMerge: defineAsyncComponent(() => import('@/components/tools/WordMerge.vue')),
  wordDiff: defineAsyncComponent(() => import('@/components/tools/WordDiff.vue')),
  wordMeta: defineAsyncComponent(() => import('@/components/tools/WordMetadata.vue')),
  excelMeta: defineAsyncComponent(() => import('@/components/tools/ExcelMetadata.vue')),
}

onMounted(async () => {
  try {
    const health = await getHealth()
    aiAvailable.value = Boolean(health.features?.ai)
    lockedTools.value = new Set(health.login_required_tools ?? [])
    if (!availableGroups.value.some((group) => group.key === activeGroupKey.value)) {
      activeGroupKey.value = availableGroups.value[0]?.key ?? 'bearbeiten'
    }
  } catch {
    aiAvailable.value = false
    lockedTools.value = new Set()
  }
})

onBeforeUnmount(closeWorkspace)
</script>
