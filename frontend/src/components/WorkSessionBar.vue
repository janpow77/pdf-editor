<template>
  <div class="space-y-3">
    <UiPanel v-if="offer" tone="warning" padding="sm" class="flex flex-wrap items-center justify-between gap-3">
      <span class="text-sm">
        Unterbrochene Bearbeitung gefunden: <strong>{{ offer.name }}</strong>
        ({{ formatSavedAt(offer.savedAt) }}{{ offerChanges ? `, ${offerChanges} offene Änderung(en)` : '' }}).
      </span>
      <span class="flex shrink-0 gap-2">
        <UiButton variant="primary" size="sm" @click="resume">Fortsetzen</UiButton>
        <UiButton size="sm" @click="discard">Verwerfen</UiButton>
      </span>
    </UiPanel>

    <div class="flex flex-wrap items-center gap-2 text-sm">
      <UiButton v-if="blob" size="sm" :disabled="busy" title="Arbeitskopie samt offenen Änderungen als Datei sichern" @click="saveFile">
        Arbeitsstand speichern
      </UiButton>
      <UiButton size="sm" :disabled="busy" @click="input?.click()">Arbeitsstand laden</UiButton>
      <input ref="input" type="file" accept=".zip,.pdf" class="hidden" @change="onFile" />
      <span v-if="hint" class="text-gray-600 dark:text-gray-300">{{ hint }}</span>
      <span v-else-if="localSaved" class="text-gray-600 dark:text-gray-400">
        im Browser gesichert · {{ formatSavedAt(localSaved) }}
      </span>
      <UiButton v-if="localSaved" variant="ghost" size="sm" @click="discard">Browser-Sicherung löschen</UiButton>
    </div>

    <p class="text-xs leading-5 text-gray-600 dark:text-gray-400">
      <template v-if="blob">
        Der Arbeitsstand wird auf diesem Gerät im Browser gesichert. Für einen Gerätewechsel oder eine längere Pause die portable Arbeitsstandsdatei verwenden.
      </template>
      <template v-else>
        Eine unterbrochene Bearbeitung lässt sich aus einer zuvor gespeicherten ZIP-Datei oder einem PDF fortsetzen.
      </template>
    </p>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
/**
 * Einheitliche Bedienung für „Bearbeitung unterbrechen und fortsetzen“.
 *
 * Ein Generationszähler entwertet geplante oder noch laufende Autosaves, sobald
 * das Dokument wechselt, zurückgesetzt oder die Komponente geschlossen wird.
 * Ein verzögert geladener Browserstand wird nur angeboten, solange wirklich
 * noch kein Dokument geöffnet ist.
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import {
  clearLocalSession,
  downloadSessionFile,
  formatSavedAt,
  loadLocalSession,
  readSessionFile,
  saveLocalSession,
  type WorkSession,
} from '@/lib/worksession'

const props = withDefaults(
  defineProps<{
    tool: string
    blob: Blob | null
    name: string
    state: unknown
    changeCount?: number
  }>(),
  { changeCount: 0 },
)

const emit = defineEmits<{
  (event: 'restore', payload: { name: string; blob: Blob; state: unknown }): void
}>()

const input = ref<HTMLInputElement | null>(null)
const offer = ref<WorkSession | null>(null)
const offerChanges = ref(0)
const localSaved = ref('')
const hint = ref('')
const error = ref<string | null>(null)
const busy = ref(false)

let timer: ReturnType<typeof globalThis.setTimeout> | null = null
let saveGeneration = 0
let mounted = true

function countChanges(state: unknown): number {
  if (Array.isArray(state)) return state.length
  if (state && typeof state === 'object') {
    const entries = state as { edits?: unknown[]; pending?: unknown[]; fields?: unknown[] }
    return (entries.edits ?? entries.pending ?? entries.fields ?? []).length
  }
  return 0
}

function cancelPendingSave(): void {
  saveGeneration += 1
  if (timer) globalThis.clearTimeout(timer)
  timer = null
}

onMounted(async () => {
  if (props.blob) return
  const stored = await loadLocalSession(props.tool)
  if (!mounted || props.blob || !stored) return
  offer.value = stored
  offerChanges.value = countChanges(stored.state)
})

onBeforeUnmount(() => {
  mounted = false
  cancelPendingSave()
})

watch(
  () => [props.blob, props.name, props.state] as const,
  () => {
    cancelPendingSave()
    const blob = props.blob
    if (!blob) return

    const generation = saveGeneration
    const name = props.name
    const state = props.state
    timer = globalThis.setTimeout(async () => {
      timer = null
      const result = await saveLocalSession(props.tool, name, blob, state)
      if (!mounted || generation !== saveGeneration) return
      if (result === 'ok') {
        localSaved.value = new Date().toISOString()
        hint.value = ''
      } else if (result === 'zu-gross') {
        hint.value = 'Dokument zu groß für die Browser-Sicherung – bitte Arbeitsstand als Datei speichern.'
      } else {
        hint.value = 'Browser-Sicherung nicht möglich – bitte Arbeitsstand als Datei speichern.'
      }
    }, 1500)
  },
  { deep: true },
)

function resume(): void {
  const stored = offer.value
  offer.value = null
  if (!stored) return
  emit('restore', { name: stored.name, blob: stored.blob, state: stored.state })
  localSaved.value = stored.savedAt
}

async function discard(): Promise<void> {
  cancelPendingSave()
  offer.value = null
  localSaved.value = ''
  hint.value = ''
  await clearLocalSession(props.tool)
}

async function saveFile(): Promise<void> {
  if (!props.blob) return
  busy.value = true
  error.value = null
  try {
    const filename = await downloadSessionFile(props.tool, props.name, props.blob, props.state)
    hint.value = `${filename} gespeichert`
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Speichern fehlgeschlagen.'
  } finally {
    busy.value = false
  }
}

async function onFile(event: Event): Promise<void> {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  target.value = ''
  if (!file) return
  busy.value = true
  error.value = null
  hint.value = ''
  try {
    const loaded = await readSessionFile(file, props.tool)
    if (loaded.foreignTool) {
      error.value = `Diese Sitzungsdatei stammt aus einem anderen Werkzeug (${loaded.foreignTool}).`
      return
    }
    cancelPendingSave()
    emit('restore', { name: loaded.name, blob: loaded.blob, state: loaded.state })
    offer.value = null
    hint.value = 'Arbeitsstand geladen.'
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Datei konnte nicht gelesen werden.'
  } finally {
    busy.value = false
  }
}
</script>
