<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="$emit('close')">
    <div class="w-full max-w-md bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 space-y-4">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Ergebnisse per E-Mail senden</h2>

      <p class="text-sm text-gray-600 dark:text-gray-300">
        {{ items.length }} Datei(en), gesamt {{ formatSize(size) }}.
      </p>

      <div>
        <label for="mail-to" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Empfänger-Adresse
        </label>
        <input
          id="mail-to"
          v-model="to"
          type="email"
          required
          placeholder="name@example.org"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700
                 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          @keyup.enter="send"
        />
      </div>

      <p class="text-xs text-gray-500 dark:text-gray-400">
        Ihre E-Mail-Adresse wird ausschließlich für diesen einen Versand verwendet und
        weder gespeichert noch protokolliert.
      </p>

      <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">
        {{ error }}
      </div>
      <div v-if="sent" class="p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg text-sm text-emerald-700 dark:text-emerald-300">
        E-Mail wurde versendet.
      </div>

      <div class="flex justify-end gap-2">
        <button
          class="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300
                 hover:bg-gray-50 dark:hover:bg-gray-700"
          @click="$emit('close')"
        >
          Schließen
        </button>
        <button
          class="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          :disabled="sending || !to.trim() || items.length === 0"
          @click="send"
        >
          {{ sending ? 'Senden…' : 'Senden' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { apiPost } from '@/lib/api'
import { formatSize, type SessionResult } from '@/lib/results'

const props = defineProps<{ items: SessionResult[] }>()
defineEmits<{ (e: 'close'): void }>()

const to = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref<string | null>(null)

const size = computed(() => props.items.reduce((s, r) => s + r.blob.size, 0))

async function send() {
  if (sending.value || !to.value.trim()) return
  sending.value = true
  sent.value = false
  error.value = null
  try {
    const fd = new FormData()
    fd.append('to', to.value.trim())
    for (const item of props.items) {
      fd.append('files', item.blob, item.name)
    }
    await apiPost('/api/mail/send', fd)
    sent.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Mailversand fehlgeschlagen'
  } finally {
    sending.value = false
  }
}
</script>
