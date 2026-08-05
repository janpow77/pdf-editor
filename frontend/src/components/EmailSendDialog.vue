<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" @mousedown.self="close">
    <form
      ref="dialog"
      class="w-full max-w-md space-y-4 rounded-[1.5rem] bg-white/95 p-6 shadow-apple backdrop-blur-2xl dark:bg-gray-900/95"
      role="dialog"
      aria-modal="true"
      aria-labelledby="mail-dialog-title"
      @submit.prevent="send"
    >
      <h2 id="mail-dialog-title" class="text-xl font-semibold text-gray-950 dark:text-white">Ergebnisse per E-Mail senden</h2>

      <p class="text-sm text-gray-600 dark:text-gray-300">
        {{ items.length }} Datei(en), gesamt {{ formatSize(size) }}.
      </p>

      <UiField label="Empfänger-Adresse" for-id="mail-to" required>
        <input
          id="mail-to"
          ref="emailInput"
          v-model="to"
          type="email"
          required
          autocomplete="email"
          placeholder="name@example.org"
          class="ui-control w-full"
        />
      </UiField>

      <p class="text-xs leading-5 text-gray-600 dark:text-gray-400">
        Die E-Mail-Adresse wird ausschließlich für diesen Versand verwendet und weder gespeichert noch protokolliert.
      </p>

      <UiAlert v-if="tooLarge" tone="warning">
        Die Anhänge sind größer als {{ formatSize(maxAttachmentBytes) }}. Bitte verwenden Sie stattdessen den ZIP-Download.
      </UiAlert>
      <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
      <UiAlert v-if="sent" tone="success" live>E-Mail wurde versendet.</UiAlert>

      <div class="flex justify-end gap-2">
        <UiButton :disabled="sending" @click="close">Schließen</UiButton>
        <UiButton
          variant="primary"
          type="submit"
          :loading="sending"
          :disabled="!to.trim() || !items.length || tooLarge || sent"
        >{{ sending ? 'Senden…' : 'Senden' }}</UiButton>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
/**
 * Modaler Versanddialog mit initialem Fokus, Fokusfalle, Escape-Unterstützung
 * und Wiederherstellung des vorherigen Fokus. Das serverseitig konfigurierte
 * Anhangslimit wird bereits vor dem Netzwerkaufruf berücksichtigt.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import { useNotifications } from '@/composables/useNotifications'
import { apiPost } from '@/lib/api'
import { formatSize, type SessionResult } from '@/lib/results'

const props = defineProps<{ items: SessionResult[]; maxAttachmentBytes: number }>()
const emit = defineEmits<{ (event: 'close'): void }>()
const notifications = useNotifications()
const dialog = ref<HTMLFormElement | null>(null)
const emailInput = ref<HTMLInputElement | null>(null)
const to = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref<string | null>(null)
const size = computed(() => props.items.reduce((sum, result) => sum + result.blob.size, 0))
const tooLarge = computed(() => size.value > props.maxAttachmentBytes)
let previousFocus: HTMLElement | null = null
let previousOverflow = ''

function focusableElements(): HTMLElement[] {
  if (!dialog.value) return []
  return Array.from(dialog.value.querySelectorAll<HTMLElement>(
    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
  )).filter((element) => !element.hasAttribute('hidden'))
}

function close(): void {
  if (!sending.value) emit('close')
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key !== 'Tab') return
  const elements = focusableElements()
  if (!elements.length) return
  const first = elements[0]
  const last = elements[elements.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  document.addEventListener('keydown', onKeydown)
  await nextTick()
  emailInput.value?.focus()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = previousOverflow
  previousFocus?.focus()
})

async function send(): Promise<void> {
  const input = emailInput.value
  if (sending.value || sent.value || tooLarge.value || !input?.checkValidity()) {
    input?.reportValidity()
    return
  }
  sending.value = true
  sent.value = false
  error.value = null
  try {
    const formData = new FormData()
    formData.append('to', to.value.trim())
    for (const item of props.items) formData.append('files', item.blob, item.name)
    await apiPost('/api/mail/send', formData)
    sent.value = true
    notifications.success('E-Mail versendet', `${props.items.length} Datei(en) wurden versendet.`)
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Mailversand fehlgeschlagen.'
  } finally {
    sending.value = false
  }
}
</script>
