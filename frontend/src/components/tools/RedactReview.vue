<template>
  <div class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
    <section aria-label="Seitenansicht mit Fundstellen" class="min-w-0 space-y-2">
      <p class="text-xs text-gray-600 dark:text-gray-300">
        Schwarze Felder werden geschwärzt. Ein Klick wählt eine Fundstelle ab (gestrichelt) oder wieder aus.
        Mit gedrückter Maustaste ziehen Sie einen eigenen Bereich auf, etwa für Unterschriften oder Bilder.
      </p>
      <PdfViewer v-model="page" :source="source" @loaded="pageCount = $event">
        <template #overlay>
          <div
            ref="overlay"
            class="absolute inset-0 cursor-crosshair touch-none"
            data-testid="redact-overlay"
            @pointerdown="startDraw"
            @pointermove="moveDraw"
            @pointerup="endDraw"
            @pointercancel="cancelDraw"
          >
            <button
              v-for="box in pageBoxes"
              :key="box.key"
              type="button"
              class="absolute rounded-[2px] outline-none transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-500"
              :class="selected.has(box.id)
                ? 'bg-black/80 ring-1 ring-black hover:bg-black/60'
                : 'border-2 border-dashed border-amber-500 bg-amber-200/25 hover:bg-amber-200/45'"
              :style="boxStyle(box.rect)"
              :aria-pressed="selected.has(box.id)"
              :aria-label="`${box.label}: ${box.text} — ${selected.has(box.id) ? 'wird geschwärzt' : 'bleibt lesbar'}`"
              :title="`${box.label}: ${box.text}`"
              @pointerdown.stop
              @click="toggleOne(box.id)"
            ></button>

            <div
              v-for="area in pageAreas"
              :key="area.id"
              class="group absolute bg-black/80 ring-2 ring-primary-500"
              :style="boxStyle(area.rect)"
              @pointerdown.stop
            >
              <button
                type="button"
                class="absolute -right-3 -top-3 grid h-6 w-6 place-items-center rounded-full bg-white text-sm font-bold text-gray-900 shadow ring-1 ring-gray-400 before:absolute before:-inset-2.5 before:content-[''] sm:-right-2 sm:-top-2 sm:h-5 sm:w-5 sm:text-xs sm:before:-inset-1"
                :aria-label="`Eigenen Bereich auf Seite ${area.page} entfernen`"
                @click="removeArea(area.id)"
              >×</button>
              <button
                type="button"
                class="absolute -bottom-2.5 -right-2.5 h-5 w-5 cursor-se-resize touch-none rounded-sm bg-primary-500 before:absolute before:-inset-3 before:content-[''] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 sm:-bottom-1.5 sm:-right-1.5 sm:h-3 sm:w-3 sm:before:-inset-1.5"
                :aria-label="`Größe des Bereichs ändern (Pfeiltasten, mit Umschalt in größeren Schritten)`"
                @pointerdown.stop="startResize(area.id, $event)"
                @keydown="resizeByKey(area.id, $event)"
              ></button>
            </div>

            <div v-if="draft" class="pointer-events-none absolute border-2 border-primary-500 bg-black/40" :style="boxStyle(draft)"></div>
          </div>
        </template>
      </PdfViewer>
      <p v-if="areaLimitHit" class="text-xs font-semibold text-red-700 dark:text-red-300" role="status">
        Höchstens {{ MAX_AREAS_PER_PAGE }} eigene Bereiche je Seite und {{ MAX_AREAS }} insgesamt.
      </p>
      <p v-if="pagesWithFindings.length" class="flex flex-wrap items-center gap-1 text-xs text-gray-600 dark:text-gray-300">
        Seiten mit Fundstellen:
        <button
          v-for="p in pagesWithFindings.slice(0, 60)"
          :key="p"
          type="button"
          class="rounded px-1.5 py-0.5 font-medium tabular-nums hover:bg-gray-200 dark:hover:bg-white/10"
          :class="p === page ? 'bg-primary-100 text-primary-800 dark:bg-primary-500/20 dark:text-primary-200' : ''"
          @click="page = p"
        >{{ p }}</button>
        <span v-if="pagesWithFindings.length > 60">…</span>
      </p>
    </section>

    <aside class="min-w-0 space-y-3" aria-label="Fundstellen">
      <div class="rounded-2xl bg-gray-100/70 p-3 text-sm dark:bg-white/5">
        <p class="font-semibold tabular-nums">
          {{ selectedCount }} von {{ plan.candidates.length }} Fundstelle(n) ausgewählt<template v-if="areas.length">, {{ areas.length }} eigene(r) Bereich(e)</template>
        </p>
        <div class="mt-2 flex flex-wrap gap-1.5">
          <UiButton size="sm" variant="secondary" :disabled="!plan.candidates.length" @click="setAll(true)">Alle auswählen</UiButton>
          <UiButton size="sm" variant="secondary" :disabled="!plan.candidates.length" @click="setAll(false)">Alle abwählen</UiButton>
        </div>
        <div v-if="sources.length > 1" class="mt-2 flex flex-wrap gap-1.5" aria-label="Nach Quelle umschalten">
          <button
            v-for="src in sources"
            :key="src.source"
            type="button"
            class="rounded-full px-2.5 py-1 text-xs font-medium ring-1 transition"
            :class="src.selected === src.total
              ? 'bg-gray-900 text-white ring-gray-900 dark:bg-white dark:text-gray-900'
              : src.selected === 0 ? 'bg-transparent ring-gray-400 line-through opacity-70' : 'bg-gray-200 ring-gray-400 dark:bg-white/10'"
            :aria-pressed="src.selected === src.total"
            :title="`${src.label}: ${src.selected} von ${src.total} ausgewählt — klicken zum Umschalten`"
            @click="toggleSource(src.source, src.selected !== src.total)"
          >{{ src.label }} · {{ src.total }}</button>
        </div>
      </div>

      <UiAlert v-if="plan.pages_without_text.length" tone="warning">
        Seite {{ formatPages(plan.pages_without_text) }} ohne Textebene (z.&nbsp;B. Scan): Dort kann nichts automatisch gefunden werden.
        Bereiche bitte von Hand markieren oder die Datei vorher mit Texterkennung (OCR) verarbeiten.
      </UiAlert>
      <UiAlert v-if="outsideCount" tone="info">
        {{ outsideCount }} Fundstelle(n) liegen außerhalb des sichtbaren Seitenbereichs. Sie werden mitgeschwärzt, sind in der Ansicht aber nicht zu sehen.
      </UiAlert>

      <label v-if="groups.length > 8" class="block">
        <span class="sr-only">Fundstellen filtern</span>
        <input v-model="filter" type="search" class="ui-control w-full" placeholder="Fundstellen filtern …" />
      </label>

      <p v-if="!plan.candidates.length" class="text-sm text-gray-600 dark:text-gray-300">
        Keine Fundstellen. Sie können trotzdem eigene Bereiche markieren.
      </p>

      <p v-if="filter && !filteredGroups.length" class="text-sm text-gray-600 dark:text-gray-300">Keine Fundstelle passt zu „{{ filter }}“.</p>

      <ul class="max-h-[60vh] space-y-1 overflow-y-auto pr-1 text-sm">
        <li v-for="group in visibleGroups" :key="group.key" class="rounded-xl ring-1 ring-gray-200 dark:ring-gray-700">
          <div class="flex items-start gap-2 p-2">
            <input
              type="checkbox"
              class="mt-1 rounded"
              :checked="groupState(group) === 'all'"
              :indeterminate.prop="groupState(group) === 'some'"
              :aria-label="`${group.text} (${group.items.length}×) schwärzen`"
              @change="toggleGroup(group, ($event.target as HTMLInputElement).checked)"
            />
            <button type="button" class="min-w-0 flex-1 text-left" :aria-expanded="expanded.has(group.key)" @click="toggleExpanded(group.key)">
              <span class="block break-all font-mono" :class="groupState(group) === 'none' ? 'line-through opacity-60' : ''">{{ group.text }}</span>
              <span class="block text-xs opacity-70">
                {{ group.label }} · {{ group.items.length }}×<template v-if="group.pages.length"> · S. {{ formatPages(group.pages) }}</template><template v-if="group.hidden"> · auch versteckt</template>
              </span>
            </button>
          </div>
          <ul v-if="expanded.has(group.key)" class="border-t border-gray-200 px-2 py-1 dark:border-gray-700">
            <li v-for="(item, n) in group.items" :key="item.id" class="flex items-center gap-2 py-0.5 text-xs">
              <span class="w-6 text-right tabular-nums opacity-60">{{ n + 1 }}.</span>
              <input type="checkbox" class="rounded" :checked="selected.has(item.id)" :aria-label="`Fundstelle ${item.location} schwärzen`" @change="toggleOne(item.id)" />
              <button v-if="item.page && item.kind === 'text'" type="button" class="font-medium text-primary-700 underline hover:no-underline dark:text-primary-300" @click="page = item.page">Seite {{ item.page }}</button>
              <span v-if="item.kind === 'text' && item.text !== group.text" class="break-all font-mono opacity-70">{{ item.text }}</span>
              <span v-else>{{ item.location }}<template v-if="item.page"> (S. {{ item.page }})</template></span>
              <span v-if="item.kind === 'text' && item.location !== 'Seitentext'" class="opacity-70">{{ item.location }}</span>
            </li>
          </ul>
        </li>
      </ul>
      <UiButton v-if="filteredGroups.length > visibleGroups.length" size="sm" variant="ghost" @click="groupLimit += 200">
        Weitere {{ Math.min(200, filteredGroups.length - visibleGroups.length) }} anzeigen
      </UiButton>

      <div v-if="hiddenGroups.length" class="rounded-2xl bg-amber-50 p-3 text-xs text-amber-950 dark:bg-amber-500/10 dark:text-amber-100">
        <p class="font-semibold">Fundstellen außerhalb des Seitentexts</p>
        <p class="mt-1">
          In {{ hiddenLocations }} stehen Treffer, die man auf der Seite nicht sieht. Ausgewählte Einträge werden entfernt
          (Kommentar, Link, Formularfeld, Anhang) oder geleert (Metadaten, Lesezeichentext).
        </p>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PdfViewer from '@/components/PdfViewer.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import {
  formatPages,
  groupCandidates,
  normalizeText,
  type CandidateGroup,
  type RedactionArea,
  type RedactionPlan,
} from '@/lib/redaction'

type Box = [number, number, number, number]

const props = defineProps<{ source: Blob; plan: RedactionPlan }>()
const selected = defineModel<Set<string>>('selected', { required: true })
const areas = defineModel<RedactionArea[]>('areas', { required: true })

const page = ref(1)
const pageCount = ref(0)
const overlay = ref<HTMLElement | null>(null)
const draft = ref<Box | null>(null)
const filter = ref('')
const expanded = ref<Set<string>>(new Set())
const groupLimit = ref(200)
let drawStart: [number, number] | null = null
let resizing: string | null = null
let areaCounter = 0

const MIN_SIZE = 0.004
const MAX_AREAS = 500
const MAX_AREAS_PER_PAGE = 100
const areaLimitHit = ref(false)

const groups = computed(() => groupCandidates(props.plan.candidates))
const filteredGroups = computed(() => {
  const needle = normalizeText(filter.value)
  if (!needle) return groups.value
  return groups.value.filter((g) => normalizeText(g.text).includes(needle) || normalizeText(g.label).includes(needle))
})
const visibleGroups = computed(() => filteredGroups.value.slice(0, groupLimit.value))
const hiddenGroups = computed(() => groups.value.filter((g) => g.hidden))
const hiddenLocations = computed(() => {
  const names = new Set<string>()
  for (const c of props.plan.candidates) if (c.kind === 'hidden') names.add(c.location.replace(/ „.*“$/, '').replace(/ \(.*\)$/, ''))
  return [...names].join(', ')
})
const selectedCount = computed(() => props.plan.candidates.reduce((n, c) => n + (selected.value.has(c.id) ? 1 : 0), 0))
const outsideCount = computed(() => props.plan.candidates.filter((c) => c.outside_view).length)
const pagesWithFindings = computed(() => {
  const pages = new Set<number>()
  for (const c of props.plan.candidates) if (c.kind === 'text' && c.page) pages.add(c.page)
  for (const a of areas.value) pages.add(a.page)
  return [...pages].sort((a, b) => a - b)
})

const sources = computed(() => {
  const map = new Map<string, { source: string; label: string; total: number; selected: number }>()
  for (const c of props.plan.candidates) {
    const entry = map.get(c.source) ?? { source: c.source, label: c.label, total: 0, selected: 0 }
    entry.total += 1
    if (selected.value.has(c.id)) entry.selected += 1
    map.set(c.source, entry)
  }
  return [...map.values()]
})

const pageBoxes = computed(() =>
  props.plan.candidates
    .filter((c) => c.kind === 'text' && c.page === page.value && !c.outside_view)
    .flatMap((c) => c.rects.map((rect, i) => ({ key: `${c.id}-${i}`, id: c.id, rect: rect as Box, label: c.label, text: c.text }))),
)
const pageAreas = computed(() => areas.value.filter((a) => a.page === page.value))

watch(() => props.plan, () => {
  page.value = 1
  filter.value = ''
  expanded.value = new Set()
  groupLimit.value = 200
})

function boxStyle(rect: Box): Record<string, string> {
  const [x0, y0, x1, y1] = rect
  return {
    left: `${x0 * 100}%`,
    top: `${y0 * 100}%`,
    width: `${Math.max(0, x1 - x0) * 100}%`,
    height: `${Math.max(0, y1 - y0) * 100}%`,
  }
}

function updateSelected(mutate: (next: Set<string>) => void): void {
  const next = new Set(selected.value)
  mutate(next)
  selected.value = next
}

function toggleOne(id: string): void {
  updateSelected((next) => (next.has(id) ? next.delete(id) : next.add(id)))
}

function setAll(on: boolean): void {
  updateSelected((next) => {
    for (const c of props.plan.candidates) on ? next.add(c.id) : next.delete(c.id)
  })
}

function toggleSource(source: string, on: boolean): void {
  updateSelected((next) => {
    for (const c of props.plan.candidates) if (c.source === source) on ? next.add(c.id) : next.delete(c.id)
  })
}

function groupState(group: CandidateGroup): 'all' | 'some' | 'none' {
  const n = group.items.reduce((acc, c) => acc + (selected.value.has(c.id) ? 1 : 0), 0)
  return n === group.items.length ? 'all' : n === 0 ? 'none' : 'some'
}

function toggleGroup(group: CandidateGroup, on: boolean): void {
  updateSelected((next) => {
    for (const c of group.items) on ? next.add(c.id) : next.delete(c.id)
  })
}

function toggleExpanded(key: string): void {
  const next = new Set(expanded.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  expanded.value = next
}

function point(event: PointerEvent): [number, number] {
  const box = overlay.value?.getBoundingClientRect()
  if (!box || !box.width || !box.height) return [0, 0]
  const clamp = (v: number) => Math.min(1, Math.max(0, v))
  return [clamp((event.clientX - box.left) / box.width), clamp((event.clientY - box.top) / box.height)]
}

function normalized(a: [number, number], b: [number, number]): Box {
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])]
}

function startDraw(event: PointerEvent): void {
  if (event.button !== 0) return
  drawStart = point(event)
  draft.value = [...drawStart, ...drawStart] as Box
  overlay.value?.setPointerCapture?.(event.pointerId)
}

function startResize(id: string, event: PointerEvent): void {
  resizing = id
  overlay.value?.setPointerCapture?.(event.pointerId)
}

const KEY_STEP = 0.005
const KEY_STEP_LARGE = 0.05
const KEY_DELTAS: Record<string, [number, number]> = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] }

/** Größe per Tastatur: Pfeiltasten verschieben die rechte untere Ecke. */
function resizeByKey(id: string, event: KeyboardEvent): void {
  const delta = KEY_DELTAS[event.key]
  if (!delta) return
  event.preventDefault()
  const step = event.shiftKey ? KEY_STEP_LARGE : KEY_STEP
  areas.value = areas.value.map((a) => {
    if (a.id !== id) return a
    const x1 = Math.min(1, Math.max(a.rect[0] + MIN_SIZE, a.rect[2] + delta[0] * step))
    const y1 = Math.min(1, Math.max(a.rect[1] + MIN_SIZE, a.rect[3] + delta[1] * step))
    return { ...a, rect: [a.rect[0], a.rect[1], x1, y1] }
  })
}

function moveDraw(event: PointerEvent): void {
  if (resizing) {
    const [x, y] = point(event)
    areas.value = areas.value.map((a) =>
      a.id === resizing
        ? { ...a, rect: [a.rect[0], a.rect[1], Math.max(a.rect[0] + MIN_SIZE, x), Math.max(a.rect[1] + MIN_SIZE, y)] }
        : a,
    )
    return
  }
  if (drawStart) draft.value = normalized(drawStart, point(event))
}

function endDraw(event: PointerEvent): void {
  if (resizing) {
    resizing = null
    return
  }
  if (!drawStart) return
  const rect = normalized(drawStart, point(event))
  drawStart = null
  draft.value = null
  if (rect[2] - rect[0] < MIN_SIZE || rect[3] - rect[1] < MIN_SIZE) return
  // Gleiche Grenzen wie im Backend (MAX_AREAS, MAX_AREAS_PER_PAGE).
  if (areas.value.length >= MAX_AREAS || pageAreas.value.length >= MAX_AREAS_PER_PAGE) {
    areaLimitHit.value = true
    return
  }
  areaLimitHit.value = false
  areaCounter += 1
  areas.value = [...areas.value, { id: `bereich-${Date.now()}-${areaCounter}`, page: page.value, rect }]
}

function cancelDraw(): void {
  drawStart = null
  draft.value = null
  resizing = null
}

function removeArea(id: string): void {
  areaLimitHit.value = false
  areas.value = areas.value.filter((a) => a.id !== id)
}
</script>
