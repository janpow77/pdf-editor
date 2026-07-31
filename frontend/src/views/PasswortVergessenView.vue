<template>
  <div class="max-w-md mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Passwort vergessen</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      Wir senden Ihnen einen Link zum Zurücksetzen — sofern ein Konto mit dieser
      Adresse existiert.
    </p>

    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">E-Mail-Adresse</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>

      <div v-if="sent" class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm text-green-700 dark:text-green-300">
        Falls ein Konto existiert, wurde eine E-Mail versendet — bitte auch den Spam-Ordner prüfen.
      </div>
      <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">{{ error }}</div>

      <button type="submit" :disabled="loading" class="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
        {{ loading ? 'Sende…' : 'Link anfordern' }}
      </button>
    </form>

    <p class="mt-4 text-sm text-gray-500 dark:text-gray-400">
      <RouterLink to="/login" class="text-primary-700 dark:text-primary-400 underline hover:no-underline">Zurück zur Anmeldung</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiJson } from '@/lib/api'

const email = ref('')
const loading = ref(false)
const sent = ref(false)
const error = ref<string | null>(null)

async function submit() {
  loading.value = true
  error.value = null
  sent.value = false
  try {
    await apiJson('POST', '/api/auth/request-password-reset', { email: email.value })
    sent.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Anfrage fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
