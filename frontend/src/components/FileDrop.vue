<template>
  <div
    class="border-2 border-dashed rounded-xl p-6 text-center transition-colors"
    :class="modelValue ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 'border-gray-300 dark:border-gray-600'"
    @dragover.prevent
    @drop.prevent="onDrop"
  >
    <input ref="input" type="file" :accept="accept" class="hidden" @change="onSelect" />
    <div v-if="!modelValue">
      <p class="text-gray-500 dark:text-gray-400 mb-2">{{ label }} hierher ziehen oder</p>
      <button
        class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-sm"
        @click="input?.click()"
      >
        Datei auswählen
      </button>
    </div>
    <div v-else>
      <p class="font-medium text-gray-900 dark:text-white">{{ modelValue.name }}</p>
      <p class="text-sm text-gray-500">{{ (modelValue.size / (1024 * 1024)).toFixed(1).replace('.', ',') }} MB</p>
      <button class="mt-1 text-sm text-red-500 hover:text-red-700" @click="emit('update:modelValue', null)">
        Entfernen
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{ modelValue: File | null; accept?: string; label?: string }>(),
  { accept: '.pdf', label: 'PDF' },
)
const emit = defineEmits<{ (e: 'update:modelValue', f: File | null): void }>()
const input = ref<HTMLInputElement | null>(null)

function matches(name: string): boolean {
  return props.accept.split(',').some((ext) => name.toLowerCase().endsWith(ext.trim()))
}

function onSelect(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (f) emit('update:modelValue', f)
}

function onDrop(e: DragEvent) {
  const f = e.dataTransfer?.files?.[0]
  if (f && matches(f.name)) emit('update:modelValue', f)
}
</script>
