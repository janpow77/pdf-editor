<template>
  <div class="max-w-md mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Anmelden</h1>
    <div
      v-if="requestedTool"
      class="mb-4 p-3 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-700 rounded-lg text-sm text-primary-800 dark:text-primary-300"
    >
      Das gewählte Werkzeug hat der Betreiber auf angemeldete Nutzer beschränkt.
      Nach der Anmeldung steht es zur Verfügung — ein Konto ist kostenlos.
    </div>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      Ein Konto ist optional — die meisten Werkzeuge funktionieren auch ohne Anmeldung.
      Angemeldet gelten höhere Limits und Ihre gespeicherten Einstellungen.
    </p>

    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">E-Mail-Adresse</label>
        <input
          id="email"
          v-model="email"
          type="email"
          required
          autocomplete="email"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>
      <div>
        <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Passwort</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          autocomplete="current-password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">
        {{ error }}
      </div>

      <button
        type="submit"
        :disabled="loading"
        class="w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      >
        {{ loading ? 'Anmelden…' : 'Anmelden' }}
      </button>
    </form>

    <p class="mt-4 text-sm text-gray-500 dark:text-gray-400">
      <RouterLink to="/passwort-vergessen" class="text-primary-600 dark:text-primary-400 hover:underline">Passwort vergessen?</RouterLink>
    </p>
    <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
      Noch kein Konto?
      <RouterLink to="/registrieren" class="text-primary-600 dark:text-primary-400 hover:underline">Kostenlos registrieren</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { login } from '@/lib/auth'

const router = useRouter()
const route = useRoute()
// Von einer gesperrten Werkzeug-Kachel hierher geleitet?
const requestedTool = computed(() => (route.query.werkzeug as string | undefined) || '')
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

async function submit() {
  loading.value = true
  error.value = null
  try {
    await login(email.value, password.value)
    router.push((route.query.redirect as string) || '/')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Anmeldung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
