<template>
  <div class="space-y-2">
    <!-- Angebot, den letzten Stand fortzusetzen -->
    <div
      v-if="offer"
      class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-900 dark:text-amber-200 flex flex-wrap items-center justify-between gap-3"
    >
      <span>
        Unterbrochene Bearbeitung gefunden: <strong>{{ offer.name }}</strong>
        ({{ formatSavedAt(offer.savedAt) }}{{ offerChanges ? `, ${offerChanges} offene Änderung(en)` : '' }}).
      </span>
      <span class="flex gap-2 shrink-0">
        <button class="px-3 py-1 rounded-lg bg-primary-600 text-white hover:bg-primary-700" @click="resume">
          Fortsetzen
        </button>
        <button class="px-3 py-1 rounded-lg border border-amber-300 dark:border-amber-700" @click="discard">
          Verwerfen
        </button>
      </span>
    </div>

    <!-- Aktionen: Laden geht immer, Speichern nur mit geöffnetem Dokument -->
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <button
        v-if="blob"
        class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400"
        :disabled="busy"
        title="Arbeitskopie samt offener Änderungen als Datei sichern"
        @click="saveFile"
      >
        Arbeitsstand speichern
      </button>
      <button
        class="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-primary-400"
        :disabled="busy"
        @click="input?.click()"
      >
        Arbeitsstand laden
      </button>
      <input ref="input" type="file" accept=".zip,.pdf" class="hidden" @change="onFile" />
      <span v-if="hint" class="text-gray-500 dark:text-gray-400">{{ hint }}</span>
      <span v-else-if="localSaved" class="text-gray-400 dark:text-gray-500">
        im Browser gesichert · {{ formatSavedAt(localSaved) }}
      </span>
      <button
        v-if="localSaved"
        class="text-xs text-gray-400 hover:text-red-600 underline"
        @click="discard"
      >
        Browser-Sicherung löschen
      </button>
    </div>

    <p class="text-xs text-gray-400 dark:text-gray-500">
      <template v-if="blob">
        Der Arbeitsstand wird auf diesem Gerät im Browser gesichert (nicht auf dem Server).
        Für einen Wechsel des Geräts oder längere Pausen die Datei „Arbeitsstand speichern"
        nutzen — sie enthält die Arbeitskopie und die offenen Änderungen.
      </template>
      <template v-else>
        Eine unterbrochene Bearbeitung fortsetzen? Über „Arbeitsstand laden" eine zuvor
        gespeicherte Sitzungsdatei (.zip) oder ein PDF öffnen.
      </template>
    </p>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
/**
 * Einheitliche Bedienung für „Bearbeitung unterbrechen und fortsetzen"
 * in allen Editoren (siehe lib/worksession.ts).
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
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
    /** Werkzeug-Kennung, bestimmt den Speicherplatz */
    tool: string
    /** aktuelle Arbeitskopie (null = noch kein Dokument geöffnet) */
    blob: Blob | null
    /** Dateiname der Arbeitskopie */
    name: string
    /** werkzeugspezifischer Zustand, z.B. vorgemerkte Änderungen */
    state: unknown
    /** Anzahl offener Änderungen — nur für die Anzeige */
    changeCount?: number
  }>(),
  { changeCount: 0 },
)

const emit = defineEmits<{
  (e: 'restore', payload: { name: string; blob: Blob; state: unknown }): void
}>()

const input = ref<HTMLInputElement | null>(null)
const offer = ref<WorkSession | null>(null)
const offerChanges = ref(0)
const localSaved = ref('')
const hint = ref('')
const error = ref<string | null>(null)
const busy = ref(false)

let timer: ReturnType<typeof setTimeout> | null = null

function countChanges(state: unknown): number {
  if (Array.isArray(state)) return state.length
  if (state && typeof state === 'object') {
    const entries = (state as { edits?: unknown[]; pending?: unknown[]; fields?: unknown[] })
    return (entries.edits ?? entries.pending ?? entries.fields ?? []).length
  }
  return 0
}

onMounted(async () => {
  // Nur anbieten, solange nichts geöffnet ist — sonst überschriebe man die Arbeit
  if (props.blob) return
  const stored = await loadLocalSession(props.tool)
  if (stored) {
    offer.value = stored
    offerChanges.value = countChanges(stored.state)
  }
})

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})

// Automatische Sicherung auf diesem Gerät (entprellt)
watch(
  () => [props.blob, props.state] as const,
  () => {
    if (!props.blob) return
    if (timer) clearTimeout(timer)
    timer = setTimeout(async () => {
      const result = await saveLocalSession(props.tool, props.name, props.blob as Blob, props.state)
      if (result === 'ok') {
        localSaved.value = new Date().toISOString()
        hint.value = ''
      } else if (result === 'zu-gross') {
        hint.value = 'Dokument zu groß für die Browser-Sicherung — bitte Arbeitsstand speichern'
      } else {
        hint.value = 'Browser-Sicherung nicht möglich — bitte Arbeitsstand als Datei speichern'
      }
    }, 1500)
  },
  { deep: true },
)

function resume() {
  const stored = offer.value
  offer.value = null
  if (!stored) return
  emit('restore', { name: stored.name, blob: stored.blob, state: stored.state })
  localSaved.value = stored.savedAt
}

async function discard() {
  offer.value = null
  localSaved.value = ''
  await clearLocalSession(props.tool)
}

async function saveFile() {
  if (!props.blob) return
  busy.value = true
  error.value = null
  try {
    const filename = await downloadSessionFile(props.tool, props.name, props.blob, props.state)
    hint.value = `${filename} gespeichert`
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Speichern fehlgeschlagen'
  } finally {
    busy.value = false
  }
}

async function onFile(event: Event) {
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
    emit('restore', { name: loaded.name, blob: loaded.blob, state: loaded.state })
    offer.value = null
    hint.value = 'Arbeitsstand geladen'
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Datei konnte nicht gelesen werden'
  } finally {
    busy.value = false
  }
}
</script>
