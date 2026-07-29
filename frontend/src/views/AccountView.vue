<template>
  <div class="max-w-2xl mx-auto px-4 py-8 space-y-8">
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-1">Mein Konto</h1>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        {{ user?.email }}
        <span v-if="user?.is_verified" class="text-green-600 dark:text-green-400">· bestätigt</span>
      </p>
    </div>

    <div
      v-if="user && !user.is_verified && flowsAvailable"
      class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg text-sm text-amber-800 dark:text-amber-300 flex items-center justify-between gap-3 flex-wrap"
    >
      <span>Ihre E-Mail-Adresse ist noch nicht bestätigt.</span>
      <button
        class="px-3 py-1.5 text-sm rounded-lg border border-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/40 disabled:opacity-50"
        :disabled="verifySending"
        @click="requestVerification"
      >
        {{ verifySent ? 'Mail versendet' : verifySending ? 'Sende…' : 'Bestätigungs-Mail senden' }}
      </button>
    </div>

    <!-- Werkzeug-Einstellungen -->
    <section class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5 space-y-4">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Werkzeug-Einstellungen</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Diese Voreinstellungen werden an Ihrem Konto gespeichert und in den Werkzeugen vorausgefüllt.
      </p>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Standard-OCR-Sprache</label>
        <select
          v-model="ocrLanguage"
          class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
        >
          <option value="deu">Deutsch</option>
          <option value="eng">Englisch</option>
          <option value="deu+eng">Deutsch + Englisch</option>
        </select>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Standard-Wasserzeichen-Text</label>
        <input
          v-model="watermarkText"
          type="text"
          placeholder="z.B. ENTWURF"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>

      <div class="flex items-center gap-3">
        <button
          :disabled="saving"
          class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
          @click="save"
        >
          {{ saving ? 'Speichere…' : 'Einstellungen speichern' }}
        </button>
        <span v-if="saved" class="text-sm text-green-600 dark:text-green-400">Gespeichert.</span>
      </div>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    </section>

    <!-- Konto löschen -->
    <section class="bg-white dark:bg-gray-800 rounded-xl border border-red-200 dark:border-red-900 p-5 space-y-3">
      <h2 class="text-lg font-semibold text-red-700 dark:text-red-400">Konto löschen</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">
        Löscht Ihr Konto endgültig samt aller gespeicherten Einstellungen (Art. 17 DSGVO).
        Die anonyme Nutzung der Werkzeuge bleibt Ihnen weiterhin offen.
      </p>
      <div>
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Passwort zur Bestätigung</label>
        <input
          v-model="deletePassword"
          type="password"
          autocomplete="current-password"
          class="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 px-3 py-2 text-sm text-gray-900 dark:text-white"
        />
      </div>
      <button
        :disabled="deleting || !deletePassword"
        class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm"
        @click="removeAccount"
      >
        {{ deleting ? 'Lösche…' : 'Konto endgültig löschen' }}
      </button>
      <p v-if="deleteError" class="text-sm text-red-600">{{ deleteError }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiGetJson, apiJson } from '@/lib/api'
import { deleteAccount, loadPreferences, preferences, savePreferences, user } from '@/lib/auth'

const router = useRouter()
const ocrLanguage = ref('deu')
const watermarkText = ref('')
const saving = ref(false)
const saved = ref(false)
const error = ref<string | null>(null)
const deletePassword = ref('')
const deleting = ref(false)
const deleteError = ref<string | null>(null)

const flowsAvailable = ref(false)
const verifySending = ref(false)
const verifySent = ref(false)

async function requestVerification() {
  verifySending.value = true
  try {
    await apiJson('POST', '/api/auth/request-verification')
    verifySent.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Versand fehlgeschlagen'
  } finally {
    verifySending.value = false
  }
}

onMounted(async () => {
  try {
    const health = await apiGetJson<{ account_flows: boolean }>('/api/health')
    flowsAvailable.value = health.account_flows
  } catch { /* Hinweis dann einfach ausblenden */ }
  await loadPreferences()
  ocrLanguage.value = (preferences.value.ocr_language as string) || 'deu'
  watermarkText.value = (preferences.value.watermark_text as string) || ''
})

async function save() {
  saving.value = true
  saved.value = false
  error.value = null
  try {
    await savePreferences({
      ...preferences.value,
      ocr_language: ocrLanguage.value,
      watermark_text: watermarkText.value,
    })
    saved.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Speichern fehlgeschlagen'
  } finally {
    saving.value = false
  }
}

async function removeAccount() {
  if (!confirm('Konto wirklich endgültig löschen?')) return
  deleting.value = true
  deleteError.value = null
  try {
    await deleteAccount(deletePassword.value)
    router.push('/')
  } catch (e: unknown) {
    deleteError.value = e instanceof Error ? e.message : 'Löschen fehlgeschlagen'
  } finally {
    deleting.value = false
  }
}
</script>
