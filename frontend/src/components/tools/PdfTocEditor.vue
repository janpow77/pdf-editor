<template>
  <div class="space-y-5">
    <ToolHeader title="Lesezeichen / Inhaltsverzeichnis" description="PDF-Lesezeichen lesen, automatisch erkennen und in stabiler Reihenfolge bearbeiten." @back="$emit('back')" />

    <FileDrop v-if="!file" v-model="file" />

    <template v-if="file">
      <UiPanel padding="sm" class="flex flex-wrap items-center gap-2">
        <span class="min-w-0 truncate text-sm font-semibold">{{ file.name }}</span>
        <span class="text-xs text-gray-600 dark:text-gray-400">{{ entries.length }} Einträge</span>
        <span class="flex-1"></span>
        <UiButton size="sm" :disabled="busy" @click="requestAutoDetect">Automatisch erkennen</UiButton>
        <UiButton variant="primary" size="sm" :loading="busy" @click="write">Speichern und herunterladen</UiButton>
        <UiButton variant="danger" size="sm" @click="reset">Neues Dokument</UiButton>
      </UiPanel>

      <UiAlert v-if="loaded && !entries.length" tone="warning">Keine Lesezeichen vorhanden – Einträge manuell hinzufügen oder automatisch erkennen lassen.</UiAlert>
      <UiAlert v-if="confirmAuto" tone="warning">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <span>Die automatische Erkennung ersetzt die aktuell bearbeiteten Einträge.</span>
          <span class="flex gap-2">
            <UiButton size="sm" @click="confirmAuto = false">Abbrechen</UiButton>
            <UiButton variant="primary" size="sm" @click="runAutoDetect">Ersetzen</UiButton>
          </span>
        </div>
      </UiAlert>

      <UiPanel padding="sm" class="overflow-x-auto">
        <table class="w-full min-w-[42rem] text-sm">
          <thead>
            <tr class="border-b border-gray-300 text-left text-gray-600 dark:border-gray-600 dark:text-gray-300">
              <th class="w-24 px-2 py-2">Ebene</th>
              <th class="px-2 py-2">Titel</th>
              <th class="w-28 px-2 py-2">Seite</th>
              <th class="w-36 px-2 py-2">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(entry, index) in entries" :key="entry.id" class="border-b border-gray-200/80 dark:border-gray-700">
              <td class="px-2 py-2">
                <label :for="`toc-level-${entry.id}`" class="sr-only">Ebene von {{ entry.title || `Eintrag ${index + 1}` }}</label>
                <select :id="`toc-level-${entry.id}`" v-model.number="entry.level" class="ui-control w-20 px-2 py-1.5">
                  <option :value="1">1</option><option :value="2">2</option><option :value="3">3</option>
                </select>
              </td>
              <td class="px-2 py-2">
                <label :for="`toc-title-${entry.id}`" class="sr-only">Titel von Eintrag {{ index + 1 }}</label>
                <input :id="`toc-title-${entry.id}`" v-model="entry.title" type="text" :style="{ paddingLeft: `${0.75 + (entry.level - 1)}rem` }" class="ui-control w-full" />
              </td>
              <td class="px-2 py-2">
                <label :for="`toc-page-${entry.id}`" class="sr-only">Zielseite von {{ entry.title || `Eintrag ${index + 1}` }}</label>
                <input :id="`toc-page-${entry.id}`" v-model.number="entry.page" type="number" min="1" :max="pageCount || undefined" class="ui-control w-24 px-2 py-1.5" />
              </td>
              <td class="whitespace-nowrap px-2 py-2">
                <span class="flex gap-1">
                  <UiIconButton size="sm" :disabled="index === 0" :aria-label="`${entry.title || 'Eintrag'} nach oben verschieben`" @click="move(index, -1)">↑</UiIconButton>
                  <UiIconButton size="sm" :disabled="index === entries.length - 1" :aria-label="`${entry.title || 'Eintrag'} nach unten verschieben`" @click="move(index, 1)">↓</UiIconButton>
                  <UiIconButton size="sm" variant="danger" :aria-label="`${entry.title || 'Eintrag'} entfernen`" @click="removeEntry(entry.id)">×</UiIconButton>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <UiButton class="mt-3" size="sm" @click="addEntry">+ Eintrag hinzufügen</UiButton>
      </UiPanel>
    </template>

    <UiAlert v-if="done" tone="success" live>Lesezeichen gespeichert und Datei heruntergeladen.</UiAlert>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

interface TocEntry { id: string; level: 1 | 2 | 3; title: string; page: number }

const file = ref<File | null>(null)
const entries = ref<TocEntry[]>([])
const pageCount = ref(0)
const loaded = ref(false)
const busy = ref(false)
const done = ref(false)
const error = ref<string | null>(null)
const confirmAuto = ref(false)
let nextId = 1
let generation = 0
let controller: AbortController | null = null

function normalizedEntries(value: unknown): { entries: TocEntry[]; pageCount: number } {
  const source = value && typeof value === 'object' ? value as Record<string, unknown> : {}
  const list = Array.isArray(source.entries) ? source.entries : Array.isArray(source.toc) ? source.toc : []
  const normalized = list.slice(0, 1000).flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const raw = item as Record<string, unknown>
    const title = String(raw.title ?? '').slice(0, 500)
    const level = Math.min(3, Math.max(1, Math.trunc(Number(raw.level) || 1))) as 1 | 2 | 3
    const page = Math.max(1, Math.trunc(Number(raw.page) || 1))
    return [{ id: `toc-${nextId++}`, level, title, page }]
  })
  return { entries: normalized, pageCount: Math.max(0, Math.trunc(Number(source.page_count) || 0)) }
}

watch(file, async (currentFile) => {
  const currentGeneration = ++generation
  controller?.abort()
  controller = null
  entries.value = []
  pageCount.value = 0
  loaded.value = false
  done.value = false
  error.value = null
  confirmAuto.value = false
  busy.value = false
  if (!currentFile) return

  const requestController = new AbortController()
  controller = requestController
  busy.value = true
  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    const response = await apiPost('/api/pdf-editor/toc/read', formData, { signal: requestController.signal, notifyOnError: false })
    const normalized = normalizedEntries(await response.json())
    if (currentGeneration !== generation || file.value !== currentFile) return
    entries.value = normalized.entries
    pageCount.value = normalized.pageCount
  } catch (caught: unknown) {
    if (!requestController.signal.aborted && currentGeneration === generation) {
      error.value = caught instanceof Error ? caught.message : 'Lesezeichen konnten nicht gelesen werden.'
    }
  } finally {
    if (currentGeneration === generation) {
      busy.value = false
      loaded.value = true
      if (controller === requestController) controller = null
    }
  }
})

watch(entries, () => { done.value = false }, { deep: true })

function requestAutoDetect(): void {
  if (!file.value) return
  if (entries.value.length) confirmAuto.value = true
  else void runAutoDetect()
}

async function runAutoDetect(): Promise<void> {
  const currentFile = file.value
  if (!currentFile || busy.value) return
  confirmAuto.value = false
  const currentGeneration = generation
  const requestController = new AbortController()
  controller?.abort()
  controller = requestController
  busy.value = true
  error.value = null
  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    const response = await apiPost('/api/pdf-editor/toc/auto-detect', formData, { signal: requestController.signal, notifyOnError: false })
    const normalized = normalizedEntries(await response.json())
    if (currentGeneration !== generation || file.value !== currentFile) return
    if (!normalized.entries.length) error.value = 'Keine Überschriften erkannt.'
    else entries.value = normalized.entries
    if (normalized.pageCount) pageCount.value = normalized.pageCount
  } catch (caught: unknown) {
    if (!requestController.signal.aborted && currentGeneration === generation) {
      error.value = caught instanceof Error ? caught.message : 'Automatische Erkennung fehlgeschlagen.'
    }
  } finally {
    if (currentGeneration === generation) busy.value = false
    if (controller === requestController) controller = null
  }
}

function addEntry(): void {
  entries.value.push({ id: `toc-${nextId++}`, level: 1, title: '', page: 1 })
}

function removeEntry(id: string): void {
  entries.value = entries.value.filter((entry) => entry.id !== id)
}

function move(index: number, delta: -1 | 1): void {
  const target = index + delta
  if (target < 0 || target >= entries.value.length) return
  const [entry] = entries.value.splice(index, 1)
  if (entry) entries.value.splice(target, 0, entry)
}

async function write(): Promise<void> {
  const currentFile = file.value
  if (!currentFile || busy.value) return
  const currentGeneration = generation
  busy.value = true
  done.value = false
  error.value = null
  try {
    const payload = entries.value
      .filter((entry) => entry.title.trim())
      .map(({ level, title, page }) => ({
        level,
        title: title.trim(),
        page: Math.max(1, pageCount.value ? Math.min(pageCount.value, Math.trunc(page)) : Math.trunc(page)),
      }))
    const formData = new FormData()
    formData.append('file', currentFile)
    formData.append('entries', JSON.stringify(payload))
    const response = await apiPost('/api/pdf-editor/toc/write', formData)
    await downloadBlob(response, currentFile.name.replace(/\.pdf$/i, '_lesezeichen.pdf'))
    if (currentGeneration === generation && file.value === currentFile) done.value = true
  } catch (caught: unknown) {
    if (currentGeneration === generation) error.value = caught instanceof Error ? caught.message : 'Speichern fehlgeschlagen.'
  } finally {
    if (currentGeneration === generation) busy.value = false
  }
}

function reset(): void {
  generation += 1
  controller?.abort()
  controller = null
  file.value = null
}
</script>
