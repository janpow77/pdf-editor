<template>
  <div class="space-y-2">
    <div :class="isFormDesigner && !modelValue ? 'grid gap-4 md:grid-cols-2' : ''">
      <UiDropZone
        :accepted="Boolean(modelValue)"
        :invalid="Boolean(validationError)"
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

      <!--
        Nur im Formular-Designer erscheint eine gleichwertige zweite
        Einstiegskarte. Das PDF wird vollständig im Browser erzeugt und
        anschließend wie eine hochgeladene Datei an den bestehenden Editor
        übergeben. So bleibt die komplexe Designer-Logik unverändert und erhält
        dennoch einen echten Blank-Canvas-Workflow.
      -->
      <UiPanel
        v-if="isFormDesigner && !modelValue"
        as="button"
        type="button"
        class="flex min-h-64 flex-col items-center justify-center text-center transition hover:-translate-y-0.5 hover:shadow-apple"
        @click="createBlankForm"
      >
        <span class="grid h-12 w-12 place-items-center rounded-2xl bg-violet-100 text-2xl text-violet-700 shadow-sm dark:bg-violet-400/15 dark:text-violet-300" aria-hidden="true">＋</span>
        <span class="mt-3 font-semibold text-gray-950 dark:text-white">Leeres Formular erstellen</span>
        <span class="mt-1 text-sm leading-6 text-gray-600 dark:text-gray-300">DIN A4, Hochformat – ohne Dummy-Datei direkt im Editor starten.</span>
        <span class="mt-4 rounded-full bg-gray-950 px-5 py-2.5 text-sm font-semibold text-white shadow-sm dark:bg-white dark:text-gray-950">Neu erstellen</span>
      </UiPanel>
    </div>

    <UiAlert v-if="validationError" tone="danger">{{ validationError }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiDropZone from '@/components/ui/UiDropZone.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { useWorkspace } from '@/composables/useWorkspace'
import { formatFileSize, validatePdfFile } from '@/lib/fileValidation'
import { createBlankA4Pdf } from '@/lib/pdfFactory'
import { removeStoredValue } from '@/lib/safeStorage'

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
const notifications = useNotifications()
const { activeWorkspace } = useWorkspace()
const isFormDesigner = computed(() => activeWorkspace.value?.toolId === 'formDesigner')

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

/** Prüft Dateityp, optionales Fachlimit und bei PDFs zusätzlich Signatur und Kontolimit. */
async function acceptFile(file: File): Promise<void> {
  validationError.value = ''

  if (!matches(file)) {
    validationError.value = `Dieser Dateityp wird nicht unterstützt. Zulässig: ${props.accept}.`
  } else if (props.maxBytes !== undefined && file.size > props.maxBytes) {
    validationError.value = `${file.name} ist ${formatFileSize(file.size)} groß. Zulässig sind maximal ${formatFileSize(props.maxBytes)}.`
  } else if (props.accept.toLowerCase().includes('.pdf')) {
    const result = await validatePdfFile(file)
    if (!result.valid) validationError.value = result.message ?? 'Die PDF-Datei ist ungültig.'
  }

  if (validationError.value) {
    notifications.error('Datei nicht angenommen', validationError.value)
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
  const file = files[0]
  if (file) void acceptFile(file)
}

function removeFile(): void {
  validationError.value = ''
  emit('update:modelValue', null)
}

function createBlankForm(): void {
  // „Von Grund auf“ bedeutet bewusst ohne automatisch restauriertes Alt-Layout.
  removeStoredValue('pdfapp_form_layout')

  const blob = createBlankA4Pdf()
  const file = new File([blob], 'leeres-formular-din-a4.pdf', {
    type: 'application/pdf',
    lastModified: Date.now(),
  })
  validationError.value = ''
  emit('update:modelValue', file)
  notifications.success('Leeres Formular erstellt', 'Eine weiße DIN-A4-Seite wurde lokal erzeugt und im Designer geöffnet.')
}
</script>
