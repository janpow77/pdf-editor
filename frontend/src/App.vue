<template>
  <div class="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
    <header class="sticky top-0 z-30 border-b border-gray-200/70 dark:border-gray-700/70 bg-white/80 dark:bg-gray-800/80 backdrop-blur-md">
      <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <RouterLink to="/" class="flex items-center gap-2 font-semibold text-gray-900 dark:text-white">
          <span aria-hidden="true">📄</span> PDF-Editor
        </RouterLink>

        <div class="flex items-center gap-3">
          <RouterLink
            v-if="!isAuthenticated"
            to="/login"
            class="text-sm px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Anmelden
          </RouterLink>

          <div v-else class="relative">
            <button
              class="text-sm px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-1"
              @click="menuOpen = !menuOpen"
            >
              {{ user?.email }}
              <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <div
              v-if="menuOpen"
              class="absolute right-0 mt-1 w-44 bg-white dark:bg-gray-800 rounded-xl shadow-xl ring-1 ring-black/5 dark:ring-white/10 z-20 py-1 text-sm"
              @click="menuOpen = false"
            >
              <RouterLink to="/konto" class="block px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">Mein Konto</RouterLink>
              <RouterLink v-if="isAdmin" to="/admin" class="block px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700">Administration</RouterLink>
              <button class="block w-full text-left px-3 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700" @click="doLogout">Abmelden</button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main class="flex-1">
      <RouterView />
    </main>

    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
import { fetchMe, isAdmin, isAuthenticated, logout, user } from '@/lib/auth'

const router = useRouter()
const menuOpen = ref(false)

onMounted(() => {
  if (isAuthenticated.value) fetchMe()
})

function doLogout() {
  logout()
  router.push('/')
}
</script>
