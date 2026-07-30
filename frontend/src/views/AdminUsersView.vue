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

    <!-- Werkzeug-Freigabe -->
    <section class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
      <div class="flex items-start justify-between gap-4 mb-3">
        <div>
          <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Werkzeug-Freigabe</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Angehakte Werkzeuge stehen nur angemeldeten Nutzern zur Verfügung. Für alle
            anderen erscheinen sie ausgegraut mit Hinweis auf die Anmeldung — und werden
            auch serverseitig abgewiesen. Ohne Haken bleibt alles frei nutzbar.
          </p>
        </div>
        <div class="shrink-0 text-right">
          <span class="text-sm text-gray-500 dark:text-gray-400">{{ restricted.size }} gesperrt</span>
        </div>
      </div>

      <div v-if="toolsLoading" class="text-sm text-gray-500">Lade Werkzeuge…</div>
      <div v-else class="space-y-4">
        <div v-for="group in toolGroups" :key="group.name">
          <div class="flex items-center gap-3 mb-2">
            <h3 class="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">{{ group.name }}</h3>
            <button class="text-xs text-primary-600 hover:underline" @click="setGroup(group, true)">alle sperren</button>
            <button class="text-xs text-primary-600 hover:underline" @click="setGroup(group, false)">alle freigeben</button>
          </div>
          <div class="grid sm:grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1">
            <label
              v-for="t in group.tools"
              :key="t.id"
              class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300"
            >
              <input
                type="checkbox"
                class="rounded"
                :checked="restricted.has(t.id)"
                @change="toggleTool(t.id)"
              />
              {{ t.label }}
            </label>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <button
            class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 text-sm"
            :disabled="toolsSaving || !toolsDirty"
            @click="saveToolAccess"
          >
            {{ toolsSaving ? 'Speichere…' : 'Freigabe speichern' }}
          </button>
          <button
            v-if="toolsDirty"
            class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            @click="resetToolAccess"
          >
            Änderungen verwerfen
          </button>
          <span v-if="toolsSaved" class="text-sm text-green-600 dark:text-green-400">Gespeichert.</span>
        </div>
      </div>
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
import { computed, onMounted, ref } from 'vue'
import { apiGetJson, apiJson } from '@/lib/api'

interface ToolAccessEntry {
  id: string
  label: string
  group: string
  login_required: boolean
}

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

// ── Werkzeug-Freigabe ───────────────────────────────────────

const tools = ref<ToolAccessEntry[]>([])
const restricted = ref<Set<string>>(new Set())
const savedRestricted = ref<Set<string>>(new Set())
const toolsLoading = ref(true)
const toolsSaving = ref(false)
const toolsSaved = ref(false)

const toolGroups = computed(() => {
  const groups: { name: string; tools: ToolAccessEntry[] }[] = []
  for (const t of tools.value) {
    const existing = groups.find((g) => g.name === t.group)
    if (existing) existing.tools.push(t)
    else groups.push({ name: t.group, tools: [t] })
  }
  return groups
})

const toolsDirty = computed(() => {
  if (restricted.value.size !== savedRestricted.value.size) return true
  for (const id of restricted.value) if (!savedRestricted.value.has(id)) return true
  return false
})

async function loadToolAccess() {
  toolsLoading.value = true
  try {
    const body = await apiGetJson<{ tools: ToolAccessEntry[]; login_required: string[] }>(
      '/api/admin/tool-access',
    )
    tools.value = body.tools
    restricted.value = new Set(body.login_required)
    savedRestricted.value = new Set(body.login_required)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Werkzeuge laden fehlgeschlagen'
  } finally {
    toolsLoading.value = false
  }
}

function toggleTool(id: string) {
  const next = new Set(restricted.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  restricted.value = next
  toolsSaved.value = false
}

function setGroup(group: { tools: ToolAccessEntry[] }, locked: boolean) {
  const next = new Set(restricted.value)
  for (const t of group.tools) {
    if (locked) next.add(t.id)
    else next.delete(t.id)
  }
  restricted.value = next
  toolsSaved.value = false
}

function resetToolAccess() {
  restricted.value = new Set(savedRestricted.value)
  toolsSaved.value = false
}

async function saveToolAccess() {
  toolsSaving.value = true
  error.value = null
  try {
    const body = await apiJson<{ login_required: string[] }>('PUT', '/api/admin/tool-access', {
      login_required: [...restricted.value],
    })
    const saved = body?.login_required ?? []
    restricted.value = new Set(saved)
    savedRestricted.value = new Set(saved)
    toolsSaved.value = true
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Speichern fehlgeschlagen'
  } finally {
    toolsSaving.value = false
  }
}

onMounted(() => {
  reload()
  loadToolAccess()
})

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
