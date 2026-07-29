<template>
  <div class="max-w-md mx-auto px-4 py-12">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">Kostenlos registrieren</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mb-6">
      Mit Konto: höhere Limits (100 MB pro Datei) und gespeicherte
      Werkzeug-Einstellungen. Ihre Dateien werden auch mit Konto niemals gespeichert.
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
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <div>
        <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Passwort</label>
        <input
          id="password"
          v-model="password"
          type="password"
          required
          autocomplete="new-password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <p class="mt-1 text-xs text-gray-400">
          Mindestens 12 Zeichen mit Groß-/Kleinbuchstaben, Zahl und Sonderzeichen.
        </p>
      </div>

      <label class="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
        <input v-model="consent" type="checkbox" required class="mt-0.5 rounded" />
        <span>
          Ich habe die
          <RouterLink to="/datenschutz" class="text-blue-600 dark:text-blue-400 hover:underline">Datenschutzerklärung</RouterLink>
          gelesen und bin mit der Speicherung meiner E-Mail-Adresse und
          Konto-Einstellungen einverstanden.
        </span>
      </label>

      <div v-if="turnstileSiteKey" ref="turnstileBox" class="min-h-[70px]"></div>

      <div v-if="error" class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">
        {{ error }}
      </div>

      <button
        type="submit"
        :disabled="loading || !consent"
        class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {{ loading ? 'Registrieren…' : 'Konto erstellen' }}
      </button>
    </form>

    <p class="mt-4 text-sm text-gray-500 dark:text-gray-400">
      Bereits ein Konto?
      <RouterLink to="/login" class="text-blue-600 dark:text-blue-400 hover:underline">Anmelden</RouterLink>
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { apiGetJson } from '@/lib/api'
import { register } from '@/lib/auth'

const router = useRouter()
const email = ref('')
const password = ref('')
const consent = ref(false)
const loading = ref(false)
const error = ref<string | null>(null)

// Cloudflare Turnstile — nur aktiv, wenn der Server einen Site-Key meldet
const turnstileSiteKey = ref('')
const turnstileToken = ref('')
const turnstileBox = ref<HTMLElement | null>(null)

onMounted(async () => {
  try {
    const health = await apiGetJson<{ turnstile_site_key: string | null }>('/api/health')
    if (!health.turnstile_site_key) return
    turnstileSiteKey.value = health.turnstile_site_key
    await new Promise<void>((resolve, reject) => {
      const s = document.createElement('script')
      s.src = 'https://challenges.cloudflare.com/turnstile/api.js?render=explicit'
      s.async = true
      s.onload = () => resolve()
      s.onerror = () => reject(new Error('Turnstile konnte nicht geladen werden'))
      document.head.appendChild(s)
    })
    const turnstile = (window as any).turnstile
    if (turnstile && turnstileBox.value) {
      turnstile.render(turnstileBox.value, {
        sitekey: turnstileSiteKey.value,
        callback: (token: string) => { turnstileToken.value = token },
        'expired-callback': () => { turnstileToken.value = '' },
      })
    }
  } catch {
    // Widget-Fehler blockieren die Seite nicht — der Server lehnt dann ab
  }
})

async function submit() {
  if (!consent.value) return
  loading.value = true
  error.value = null
  try {
    await register(email.value, password.value, turnstileToken.value || undefined)
    router.push('/')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Registrierung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
