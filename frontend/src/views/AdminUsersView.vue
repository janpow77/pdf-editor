<template>
  <div class="max-w-4xl mx-auto px-4 py-8 space-y-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Administration</h1>

    <!-- Nutzerverwaltung -->
    <section class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Benutzer ({{ users.length }})</h2>

      <div v-if="loading" class="text-sm text-gray-500">Lade…</div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <th class="py-2 pr-4">E-Mail</th>
              <th class="py-2 pr-4">Rolle</th>
              <th class="py-2 pr-4">Status</th>
              <th class="py-2 pr-4">Letzter Login</th>
              <th class="py-2">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" class="border-b border-gray-100 dark:border-gray-700/50">
              <td class="py-2 pr-4 text-gray-900 dark:text-white">{{ u.email }}</td>
              <td class="py-2 pr-4">
                <span :class="u.role === 'ADMIN' ? 'text-primary-600 dark:text-primary-400 font-medium' : 'text-gray-500'">{{ u.role }}</span>
              </td>
              <td class="py-2 pr-4">
                <span v-if="u.locked" class="text-amber-600 dark:text-amber-400">gesperrt</span>
                <span v-else-if="u.is_active" class="text-green-600 dark:text-green-400">aktiv</span>
                <span v-else class="text-red-600 dark:text-red-400">deaktiviert</span>
              </td>
              <td class="py-2 pr-4 text-gray-500">{{ u.last_login ? new Date(u.last_login).toLocaleString('de-DE') : '—' }}</td>
              <td class="py-2 space-x-2 whitespace-nowrap">
                <button
                  class="text-primary-600 dark:text-primary-400 hover:underline"
                  @click="toggleActive(u)"
                >
                  {{ u.is_active ? 'Deaktivieren' : 'Aktivieren' }}
                </button>
                <button v-if="u.locked" class="text-amber-600 dark:text-amber-400 hover:underline" @click="unlock(u)">
                  Entsperren
                </button>
                <button class="text-red-600 dark:text-red-400 hover:underline" @click="remove(u)">Löschen</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="error" class="mt-3 text-sm text-red-600">{{ error }}</p>
    </section>

    <!-- Konfiguration -->
    <section class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Konfiguration (Laufzeit)</h2>
      <dl v-if="config" class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
        <div v-for="(value, key) in config" :key="key" class="flex justify-between gap-4 border-b border-gray-100 dark:border-gray-700/50 py-1">
          <dt class="text-gray-500 dark:text-gray-400">{{ key }}</dt>
          <dd class="text-gray-900 dark:text-white font-mono">{{ value }}</dd>
        </div>
      </dl>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiGetJson, apiJson } from '@/lib/api'

interface AdminUser {
  id: number
  email: string
  role: string
  is_active: boolean
  locked: boolean
  last_login: string | null
}

const users = ref<AdminUser[]>([])
const config = ref<Record<string, unknown> | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

async function reload() {
  loading.value = true
  error.value = null
  try {
    users.value = await apiGetJson<AdminUser[]>('/api/admin/users')
    config.value = await apiGetJson<Record<string, unknown>>('/api/admin/config')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Laden fehlgeschlagen'
  } finally {
    loading.value = false
  }
}

onMounted(reload)

async function toggleActive(u: AdminUser) {
  error.value = null
  try {
    await apiJson('PATCH', `/api/admin/users/${u.id}`, { is_active: !u.is_active })
    await reload()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Aktion fehlgeschlagen'
  }
}

async function unlock(u: AdminUser) {
  error.value = null
  try {
    await apiJson('POST', `/api/admin/users/${u.id}/unlock`)
    await reload()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Aktion fehlgeschlagen'
  }
}

async function remove(u: AdminUser) {
  if (!confirm(`Benutzer ${u.email} endgültig löschen?`)) return
  error.value = null
  try {
    await apiJson('DELETE', `/api/admin/users/${u.id}`)
    await reload()
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Löschen fehlgeschlagen'
  }
}
</script>
