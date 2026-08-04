<template>
  <div class="space-y-2">
    <!--
      Die großzügige Glasfläche ist vollständig als Drop-Ziel erkennbar. Ein
      rötlicher Ring markiert fehlerhafte Eingaben dezent, ohne den gesamten
      Arbeitsbereich mit einer aggressiven Warnfläche zu überdecken.
    -->
    <div
      class="apple-upload-zone p-7 text-center"
      :class="[
        modelValue ? 'border-emerald-500 bg-emerald-50/70 dark:bg-emerald-500/10' : '',
        validationError ? 'border-rose-500 bg-rose-50/70 dark:bg-rose-500/10' : '',
      ]"
      @dragover.prevent
      @drop.prevent="onDrop"
    >
      <input ref="input" type="file" :accept="accept" class="hidden" @change="onSelect" />

      <div v-if="!modelValue">
        <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-primary-50 text-2xl text-primary-700 shadow-sm dark:bg-primary-500/15 dark:text-primary-300" aria-hidden="true">⇧</div>
        <p class="mt-3 font-semibold text-gray-900 dark:text-white">{{ label }} hierher ziehen</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">oder lokal auf dem Gerät auswählen</p>
        <button type="button" class="mt-4 rounded-full bg-primary-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-apple active:scale-[0.98]" @click="input?.click()">
          Datei auswählen
        </button>
      </div>

      <div v-else>
        <div class="mx-auto grid h-11 w-11 place-items-center rounded-full bg-emerald-100 text-xl text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300" aria-hidden="true">✓</div>
        <p class="mt-3 break-all font-semibold text-gray-950 dark:text-white">{{ modelValue.name }}</p>
        <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ formatFileSize(modelValue.size) }}</p>
        <button type="button" class="mt-3 rounded-full px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10" @click="removeFile">
          Entfernen
        </button>
      </div>
    </div>

    <p v-if="validationError" class="apple-inline-error text-sm" role="alert">
      {{ validationError }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useNotifications } from '@/composables/useNotifications'
import { formatFileSize, validatePdfFile } from '@/lib/fileValidation'

const props = withDefaults(
  defineProps<{ modelValue: File | null; accept?: string; label?: string }>(),
  { accept: '.pdf', label: 'PDF' },
)
const emit = defineEmits<{ (e: 'update:modelValue', file: File | null): void }>()
const input = ref<HTMLInputElement | null>(null)
const validationError = ref('')
const notifications = useNotifications()

function matches(name: string): boolean {
  return props.accept.split(',').some((extension) => name.toLowerCase().endsWith(extension.trim().toLowerCase()))
}

/** Prüft Dateityp und bei PDFs zusätzlich Größe sowie Dateisignatur. */
async function acceptFile(file: File): Promise<void> {
  validationError.value = ''

  if (!matches(file.name)) {
    validationError.value = `Dieser Dateityp wird nicht unterstützt. Zulässig: ${props.accept}.`
  } else if (props.accept.toLowerCase().includes('.pdf')) {
    const result = await validatePdfFile(file)
    if (!result.valid) validationError.value = result.message ?? 'Die PDF-Datei ist ungültig.'
  }

  if (validationError.value) {
    notifications.error('Datei nicht angenommen', validationError.value)
    emit('update:modelValue', null)
    return
  }

  emit('update:modelValue', file)
  notifications.success('Datei geladen', `${file.name} ist bereit zur Verarbeitung.`)
}

function onSelect(event: Event): void {
  const element = event.target as HTMLInputElement
  const file = element.files?.[0]
  element.value = ''
  if (file) void acceptFile(file)
}

function onDrop(event: DragEvent): void {
  const file = event.dataTransfer?.files?.[0]
  if (file) void acceptFile(file)
}

function removeFile(): void {
  validationError.value = ''
  emit('update:modelValue', null)
}
</script>
