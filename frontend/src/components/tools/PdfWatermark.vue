<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600 flex items-center gap-1" @click="$emit('back')">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
        Zurück
      </button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Wasserzeichen hinzufügen</h2>
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
        <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="file = null">Entfernen</button>
      </div>
    </div>

    <!-- Options -->
    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-4">
      <!-- Mode -->
      <div class="flex gap-4">
        <label class="flex items-center gap-2 text-sm"><input v-model="mode" type="radio" value="text" class="text-primary-600" /> Text</label>
        <label class="flex items-center gap-2 text-sm"><input v-model="mode" type="radio" value="image" class="text-primary-600" /> Bild</label>
      </div>

      <!-- Text options -->
      <div v-if="mode === 'text'" class="space-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Text</label>
          <input v-model="text" type="text" class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm" placeholder="z.B. ENTWURF, VERTRAULICH" />
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label class="block text-xs text-gray-500 mb-1">Schriftgröße</label>
            <input v-model.number="fontSize" type="number" min="10" max="200" class="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">Farbe</label>
            <input v-model="color" type="color" class="w-full h-8 rounded cursor-pointer" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">Rotation</label>
            <input v-model.number="rotation" type="number" min="-180" max="180" class="w-full px-2 py-1.5 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">Transparenz</label>
            <input v-model.number="opacity" type="range" min="0.05" max="1" step="0.05" class="w-full" />
            <span class="text-xs text-gray-600 dark:text-gray-400">{{ Math.round(opacity * 100) }}%</span>
          </div>
        </div>
      </div>

      <!-- Image options -->
      <div v-if="mode === 'image'" class="space-y-3">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Wasserzeichen-Bild</label>
          <input type="file" accept="image/*" class="text-sm text-gray-500" @change="onImageSelect" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Transparenz</label>
          <input v-model.number="opacity" type="range" min="0.05" max="1" step="0.05" class="w-full" />
          <span class="text-xs text-gray-600 dark:text-gray-400">{{ Math.round(opacity * 100) }}%</span>
        </div>
      </div>

      <!-- Position -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Position</label>
        <div class="grid grid-cols-3 gap-2 w-48">
          <button
            v-for="pos in positions" :key="pos.value"
            class="p-2 text-xs rounded border transition-colors text-center"
            :class="position === pos.value ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500 text-gray-500'"
            @click="position = pos.value"
          >
            {{ pos.label }}
          </button>
        </div>
      </div>

      <!-- Pages -->
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Seiten (leer = alle)</label>
        <input v-model="pages" type="text" class="w-48 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm" placeholder="z.B. 1-5" />
      </div>
    </div>

    <button
      v-if="file && (text || watermarkImage)"
      :disabled="loading"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      @click="doWatermark"
    >
      <svg v-if="loading" class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      {{ loading ? 'Wasserzeichen wird hinzugefügt...' : 'Wasserzeichen hinzufügen' }}
    </button>

    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { usePdfTools } from '@/composables/usePdfTools'
import { prefDefault } from '@/lib/auth'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, withLoading, addWatermark } = usePdfTools()
const file = ref<File | null>(null)
const mode = ref('text')
const text = ref(prefDefault('watermark_text', 'ENTWURF'))
const watermarkImage = ref<File | null>(null)
const position = ref('center')
const opacity = ref(0.3)
const rotation = ref(-45)
const fontSize = ref(60)
const color = ref('#808080')
const pages = ref('')

const positions = [
  { value: 'top-left', label: '↖' },
  { value: 'center', label: '⊕' },
  { value: 'top-right', label: '↗' },
  { value: 'bottom-left', label: '↙' },
  { value: 'center', label: '⊕' },
  { value: 'bottom-right', label: '↘' },
]
// Deduplicate center
const uniquePositions = [
  { value: 'top-left', label: 'OL' },
  { value: 'center', label: 'Mitte' },
  { value: 'top-right', label: 'OR' },
  { value: 'bottom-left', label: 'UL' },
  { value: 'center', label: 'M' },
  { value: 'bottom-right', label: 'UR' },
]

function onFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) file.value = input.files[0]
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f?.name.toLowerCase().endsWith('.pdf')) file.value = f
}

function onImageSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) watermarkImage.value = input.files[0]
}

async function doWatermark() {
  if (!file.value) return
  await withLoading(() => addWatermark(file.value!, {
    text: mode.value === 'text' ? text.value : undefined,
    image: mode.value === 'image' ? watermarkImage.value || undefined : undefined,
    position: position.value,
    opacity: opacity.value,
    rotation: rotation.value,
    fontSize: fontSize.value,
    color: color.value,
    pages: pages.value || undefined,
  }))
}
</script>
