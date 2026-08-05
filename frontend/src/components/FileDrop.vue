<template>
  <div class="space-y-2">
    <div>
      <UiDropZone
        :active="isDragging"
        :accepted="Boolean(modelValue)"
        :invalid="Boolean(validationError)"
        @drag-active="isDragging = $event"
        @drop="onDroppedFiles"
      >
        <input ref="input" type="file" :accept="accept" class="hidden" @change="onSelect" />

        <div v-if="!modelValue">
          <div class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-primary-50 text-2xl text-primary-700 shadow-sm dark:bg-primary-500/15 dark:text-primary-300" aria-hidden="true">⇧</div>
          <p class="mt-3 font-semibold text-gray-900 dark:text-white">{{ label }} hierher ziehen</p>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">oder lokal auf dem Gerät auswählen</p>
          <UiButton variant="primary" class="mt-4" @click="input?.click()">Datei auswählen</UiButton>
        </div>

        <div v-else>
          <div class="mx-auto grid h-11 w-11 place-items-center rounded-full bg-emerald-100 text-xl text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300" aria-hidden="true">✓</div>
          <p class="mt-3 break-all font-semibold text-gray-950 dark:text-white">{{ modelValue.name }}</p>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-300">{{ formatFileSize(modelValue.size) }}</p>
          <UiButton variant="danger" size="sm" class="mt-3" @click="removeFile">Entfernen</UiButton>
        </div>
      </UiDropZone>
    </div>

    <UiAlert v-if="validationError" tone="danger">{{ validationError }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import { useNotifications } from '@/composables/useNotifications'
import { currentFileLimit, formatFileSize, validatePdfFile } from '@/lib/fileValidation'
import { takePendingHandoff } from '@/lib/handoff'

const props = withDefaults(
  defineProps<{
    modelValue: File | null
    accept?: string
    label?: string
    /** Optionales werkzeugspezifisches Limit, z. B. 10 MB für Wasserzeichenbilder. */
    maxBytes?: number
  }>(),
  { accept: '.pdf', label: 'PDF', maxBytes: undefined },
)
const emit = defineEmits<{ (event: 'update:modelValue', file: File | null): void }>()
const input = ref<HTMLInputElement | null>(null)
const validationError = ref('')
const isDragging = ref(false)
const notifications = useNotifications()
let validationGeneration = 0

// Von einem anderen Werkzeug übergebene Datei (z. B. Werkbank-Ergebnis)
// durchläuft dieselbe Validierung wie eine manuelle Auswahl.
onMounted(() => {
  const pending = takePendingHandoff()
  if (pending) void acceptFile(pending)
})

/** Prüft sowohl Dateiendungen als auch MIME-Angaben aus dem accept-Attribut. */
function matches(file: File): boolean {
  const name = file.name.toLowerCase()
  const mime = file.type.toLowerCase()
  return props.accept.split(',').some((rawToken) => {
    const token = rawToken.trim().toLowerCase()
    if (!token) return false
    if (token.startsWith('.')) return name.endsWith(token)
    if (token.endsWith('/*')) return mime.startsWith(token.slice(0, -1))
    if (token.includes('/')) return mime === token
    return name.endsWith(token)
  })
}

function acceptsPdf(): boolean {
  const normalized = props.accept.toLowerCase()
  return normalized.includes('.pdf') || normalized.includes('application/pdf')
}

/**
 * Prüft Dateityp, allgemeines Kontolimit, optionales Fachlimit und bei PDFs
 * zusätzlich die Signatur. Der Generationszähler verhindert, dass eine
 * langsamere ältere Auswahl eine neuere Datei oder einen Reset überschreibt.
 */
async function acceptFile(file: File): Promise<void> {
  const generation = ++validationGeneration
  validationError.value = ''

  const effectiveLimit = Math.min(currentFileLimit(), props.maxBytes ?? Number.POSITIVE_INFINITY)
  let nextError = ''

  if (!matches(file)) {
    nextError = `Dieser Dateityp wird nicht unterstützt. Zulässig: ${props.accept}.`
  } else if (file.size > effectiveLimit) {
    nextError = `${file.name} ist ${formatFileSize(file.size)} groß. Zulässig sind maximal ${formatFileSize(effectiveLimit)}.`
  } else if (acceptsPdf()) {
    const result = await validatePdfFile(file)
    if (!result.valid) nextError = result.message ?? 'Die PDF-Datei ist ungültig.'
  }

  if (generation !== validationGeneration) return
  validationError.value = nextError

  if (nextError) {
    notifications.error('Datei nicht angenommen', nextError)
    // Eine bereits ausgewählte gültige Datei bleibt erhalten. Ein fehlerhafter
    // Ersatzversuch darf nicht unbemerkt den aktuellen Arbeitsstand löschen.
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

function onDroppedFiles(files: File[]): void {
  isDragging.value = false
  const file = files[0]
  if (!file) return
  if (files.length > 1) {
    notifications.warning('Nur eine Datei möglich', 'Für dieses Werkzeug wird nur die erste abgelegte Datei verwendet.')
  }
  void acceptFile(file)
}

function removeFile(): void {
  validationGeneration += 1
  validationError.value = ''
  isDragging.value = false
  emit('update:modelValue', null)
}
</script>
