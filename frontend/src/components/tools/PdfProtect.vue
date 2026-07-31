<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">PDF schützen / entsperren</h2>
    </div>

    <!-- Modus -->
    <div class="grid grid-cols-2 gap-3">
      <button
        v-for="m in modes"
        :key="m.value"
        class="p-3 rounded-lg border-2 text-center transition-colors"
        :class="mode === m.value
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'"
        @click="mode = m.value; done = false"
      >
        <div class="text-lg mb-1">{{ m.icon }}</div>
        <div class="text-sm font-medium text-gray-900 dark:text-white">{{ m.label }}</div>
        <div class="text-xs text-gray-500">{{ m.desc }}</div>
      </button>
    </div>

    <!-- Upload -->
    <div
      class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
      :class="file ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="fileInput" type="file" accept=".pdf" class="hidden" @change="onFileSelect" />
      <div v-if="!file">
        <p class="text-gray-500 dark:text-gray-400 mb-2">PDF hierher ziehen oder</p>
        <button class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm" @click="($refs.fileInput as HTMLInputElement).click()">Datei auswählen</button>
      </div>
      <div v-else>
        <p class="font-medium text-gray-900 dark:text-white">{{ file.name }}</p>
        <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="file = null; done = false">Entfernen</button>
      </div>
    </div>

    <!-- Passwörter -->
    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {{ mode === 'protect' ? 'Passwort zum Öffnen' : 'Bekanntes Passwort des PDFs' }}
        </label>
        <input
          v-model="password"
          type="password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
      <div v-if="mode === 'protect'">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Besitzer-Passwort (optional, Standard: wie Öffnen-Passwort)
        </label>
        <input
          v-model="ownerPassword"
          type="password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
      <p class="text-xs text-gray-600 dark:text-gray-400">
        Verschlüsselung: AES-256. Das Passwort wird nur für diese eine Verarbeitung verwendet und nicht gespeichert.
      </p>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      {{ mode === 'protect' ? 'PDF wurde verschlüsselt und heruntergeladen.' : 'PDF wurde entsperrt und heruntergeladen.' }}
    </div>

    <button
      v-if="file"
      :disabled="loading || !password"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="run"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Verarbeite...' : mode === 'protect' ? 'PDF schützen' : 'PDF entsperren' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, protectPdf, unlockPdf } = usePdfTools()
const mode = ref<'protect' | 'unlock'>('protect')
const file = ref<File | null>(null)
const password = ref('')
const ownerPassword = ref('')
const done = ref(false)

const modes = [
  { value: 'protect' as const, label: 'Schützen', desc: 'Passwort setzen', icon: '🔒' },
  { value: 'unlock' as const, label: 'Entsperren', desc: 'Passwort aufheben', icon: '🔓' },
]

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) { file.value = input.files[0]; done.value = false }
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) { file.value = f; done.value = false }
}

async function run() {
  if (!file.value || !password.value) return
  done.value = false
  const ok = await withLoading(() =>
    mode.value === 'protect'
      ? protectPdf(file.value!, password.value, ownerPassword.value || undefined)
      : unlockPdf(file.value!, password.value),
  )
  if (ok) done.value = true
}
</script>
