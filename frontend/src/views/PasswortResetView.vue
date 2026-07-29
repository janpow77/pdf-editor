<template>
  <div class="max-w-md mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Neues Passwort setzen</h1>

    <div v-if="!token" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">
      Ungültiger Link — bitte den Link aus der E-Mail vollständig öffnen.
    </div>

    <form v-else class="space-y-4" @submit.prevent="submit">
      <div>
        <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Neues Passwort</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          autocomplete="new-password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
        <p class="mt-1 text-xs text-gray-400">Mindestens 12 Zeichen mit Groß-/Kleinbuchstaben, Zahl und Sonderzeichen.</p>
      </div>

      <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm text-green-700 dark:text-green-300">
        Passwort geändert — Sie können sich jetzt <RouterLink to="/login" class="underline">anmelden</RouterLink>.
      </div>
      <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">{{ error }}</div>

      <button type="submit" :disabled="loading || done" class="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
        {{ loading ? 'Speichere…' : 'Passwort ändern' }}
      </button>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { apiJson } from '@/lib/api'

const route = useRoute()
const token = computed(() => (route.query.token as string) || '')
const password = ref('')
const loading = ref(false)
const done = ref(false)
const error = ref<string | null>(null)

async function submit() {
  loading.value = true
  error.value = null
  try {
    await apiJson('POST', '/api/auth/reset-password', {
      token: token.value,
      password: password.value,
    })
    done.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Zurücksetzen fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
