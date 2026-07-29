<template>
  <div class="max-w-md mx-auto px-4 py-12 text-center space-y-4">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">E-Mail-Adresse bestätigen</h1>
    <p v-if="status === 'pending'" class="text-sm text-gray-500 dark:text-gray-400">Bestätige…</p>
    <div v-else-if="status === 'ok'" class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm text-green-700 dark:text-green-300">
      Ihre E-Mail-Adresse ist bestätigt. <RouterLink to="/" class="underline">Zur Startseite</RouterLink>
    </div>
    <div v-else class="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-700 dark:text-red-300">
      {{ error }} — Sie können auf der <RouterLink to="/konto" class="underline">Konto-Seite</RouterLink> eine neue Bestätigungs-Mail anfordern.
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { apiJson } from '@/lib/api'
import { fetchMe } from '@/lib/auth'

const route = useRoute()
const status = ref<'pending' | 'ok' | 'error'>('pending')
const error = ref('Link ist ungültig oder abgelaufen')

onMounted(async () => {
  const token = (route.query.token as string) || ''
  if (!token) {
    status.value = 'error'
    return
  }
  try {
    await apiJson('POST', '/api/auth/verify-email', { token })
    status.value = 'ok'
    await fetchMe()
  } catch (e: unknown) {
    if (e instanceof Error) error.value = e.message
    status.value = 'error'
  }
})
</script>
