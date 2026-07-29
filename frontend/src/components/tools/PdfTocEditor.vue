<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-purple-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Lesezeichen / Inhaltsverzeichnis</h2>
    </div>

    <FileDrop v-if="!file" v-model="file" />

    <template v-if="file">
      <div class="flex items-center gap-2 flex-wrap bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-3">
        <span class="text-sm text-gray-700 dark:text-gray-300 truncate">{{ file.name }}</span>
        <span class="text-xs text-gray-400">{{ entries.length }} Einträge</span>
        <span class="flex-1"></span>
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-purple-300" :disabled="busy" @click="autoDetect">
          Automatisch erkennen
        </button>
        <button class="px-3 py-1.5 text-sm rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50" :disabled="busy" @click="write">
          {{ busy ? 'Arbeite…' : 'Speichern & herunterladen' }}
        </button>
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300" @click="reset">
          Neues Dokument
        </button>
      </div>

      <div v-if="loaded && entries.length === 0" class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300">
        Keine Lesezeichen vorhanden — Einträge manuell hinzufügen oder automatisch erkennen lassen.
      </div>

      <div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <th class="py-2 px-3 w-24">Ebene</th>
              <th class="py-2 px-3">Titel</th>
              <th class="py-2 px-3 w-24">Seite</th>
              <th class="py-2 px-3 w-28">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(e, i) in entries" :key="i" class="border-b border-gray-100 dark:border-gray-700/50">
              <td class="py-1.5 px-3">
                <select v-model.number="e.level" class="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                  <option :value="3">3</option>
                </select>
              </td>
              <td class="py-1.5 px-3">
                <input v-model="e.title" type="text" :style="{ paddingLeft: `${(e.level - 1) * 16}px` }" class="w-full rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white" />
              </td>
              <td class="py-1.5 px-3">
                <input v-model.number="e.page" type="number" min="1" class="w-20 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-2 py-1 text-gray-900 dark:text-white" />
              </td>
              <td class="py-1.5 px-3 whitespace-nowrap space-x-2">
                <button class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 disabled:opacity-30" :disabled="i === 0" title="nach oben" @click="move(i, -1)">↑</button>
                <button class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 disabled:opacity-30" :disabled="i === entries.length - 1" title="nach unten" @click="move(i, 1)">↓</button>
                <button class="text-red-500 hover:text-red-700" title="entfernen" @click="entries.splice(i, 1)">✕</button>
              </td>
            </tr>
          </tbody>
        </table>
        <button class="m-3 px-3 py-1.5 text-sm rounded-lg border border-dashed border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:border-purple-300" @click="addEntry">
          + Eintrag hinzufügen
        </button>
      </div>
    </template>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Lesezeichen gespeichert, Datei heruntergeladen.
    </div>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { apiPost, downloadBlob } from '@/lib/api'

defineEmits<{ (e: 'back'): void }>()

interface TocEntry {
  level: number
  title: string
  page: number
}

const file = ref<File | null>(null)
const entries = ref<TocEntry[]>([])
const loaded = ref(false)
const busy = ref(false)
const done = ref(false)
const error = ref<string | null>(null)

watch(file, async (f) => {
  entries.value = []
  loaded.value = false
  done.value = false
  error.value = null
  if (!f) return
  busy.value = true
  try {
    const fd = new FormData()
    fd.append('file', f)
    const resp = await apiPost('/api/pdf-editor/toc/read', fd)
    const data = await resp.json()
    entries.value = (data.entries || data.toc || []).map((e: any) => ({
      level: Math.min(3, Math.max(1, e.level ?? 1)),
      title: e.title ?? '',
      page: e.page ?? 1,
    }))
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Lesezeichen lesen fehlgeschlagen'
  } finally {
    busy.value = false
    loaded.value = true
  }
})

async function autoDetect() {
  if (!file.value) return
  busy.value = true
  error.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    const resp = await apiPost('/api/pdf-editor/toc/auto-detect', fd)
    const data = await resp.json()
    const detected = (data.entries || data.toc || []).map((e: any) => ({
      level: Math.min(3, Math.max(1, e.level ?? 1)),
      title: e.title ?? '',
      page: e.page ?? 1,
    }))
    if (detected.length === 0) {
      error.value = 'Keine Überschriften erkannt'
    } else {
      entries.value = detected
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Automatische Erkennung fehlgeschlagen'
  } finally {
    busy.value = false
  }
}

function addEntry() {
  entries.value.push({ level: 1, title: '', page: 1 })
}

function move(i: number, delta: number) {
  const j = i + delta
  const arr = entries.value
  ;[arr[i], arr[j]] = [arr[j], arr[i]]
}

async function write() {
  if (!file.value) return
  busy.value = true
  done.value = false
  error.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    fd.append(
      'entries',
      JSON.stringify(entries.value.filter((e) => e.title.trim())),
    )
    const resp = await apiPost('/api/pdf-editor/toc/write', fd)
    await downloadBlob(resp, file.value.name.replace(/\.pdf$/i, '_lesezeichen.pdf'))
    done.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Speichern fehlgeschlagen'
  } finally {
    busy.value = false
  }
}

function reset() {
  file.value = null
}
</script>
