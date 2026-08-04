<template>
  <div class="min-h-screen flex flex-col bg-[#f5f5f7] text-gray-950 transition-colors dark:bg-[#09090b] dark:text-white">
    <a
      href="#hauptinhalt"
      class="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[110]
             focus:rounded-full focus:bg-primary-600 focus:px-4 focus:py-2 focus:text-white focus:shadow-apple"
      @click="focusMain"
    >
      Zum Hauptinhalt springen
    </a>

    <!--
      Transparenz und backdrop-filter erzeugen den Apple-typischen Material-
      Effekt. Der Header bleibt bewusst kompakt, damit Werkzeugflächen maximal
      viel vertikalen Raum erhalten.
    -->
    <header class="sticky top-0 z-40 border-b border-black/5 bg-white/72 backdrop-blur-2xl
                   dark:border-white/10 dark:bg-gray-950/72">
      <div class="mx-auto flex max-w-[1600px] items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
        <RouterLink
          to="/"
          class="group flex items-center gap-2.5 rounded-full pr-3 text-sm font-semibold tracking-[-0.01em]
                 text-gray-950 transition hover:bg-black/[0.035] active:scale-[0.98]
                 dark:text-white dark:hover:bg-white/[0.07]"
        >
          <img src="/auditlogo.png" alt="" aria-hidden="true" class="h-9 w-9 rounded-xl object-contain" />
          <span>PDF-Editor</span>
        </RouterLink>

        <div class="flex items-center gap-2">
          <button
            type="button"
            class="grid h-10 w-10 place-items-center rounded-full bg-white/80 text-gray-700 shadow-sm ring-1 ring-black/5
                   backdrop-blur-xl transition duration-200 hover:-translate-y-0.5 hover:shadow-apple active:scale-95
                   dark:bg-white/10 dark:text-gray-100 dark:ring-white/10"
            :aria-label="isDark ? 'Helles Erscheinungsbild aktivieren' : 'Dunkles Erscheinungsbild aktivieren'"
            :title="isDark ? 'Hellmodus' : 'Dunkelmodus'"
            @click="toggleTheme"
          >
            <svg v-if="isDark" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
              <circle cx="12" cy="12" r="4" stroke-width="2" />
              <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" stroke-width="2" stroke-linecap="round" />
            </svg>
            <svg v-else class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
              <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3 6.8 6.8 0 0 0 21 12.8Z" stroke-width="2" stroke-linejoin="round" />
            </svg>
          </button>

          <RouterLink
            v-if="!isAuthenticated"
            to="/login"
            class="rounded-full bg-gray-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition
                   hover:-translate-y-0.5 hover:shadow-apple active:scale-[0.98]
                   dark:bg-white dark:text-gray-950"
          >Anmelden</RouterLink>

          <div v-else class="relative">
            <button
              class="flex items-center gap-1.5 rounded-full bg-white/80 px-3.5 py-2 text-sm font-medium text-gray-700
                     shadow-sm ring-1 ring-black/5 backdrop-blur-xl transition hover:shadow-apple active:scale-[0.98]
                     dark:bg-white/10 dark:text-gray-200 dark:ring-white/10"
              :aria-expanded="menuOpen"
              aria-haspopup="menu"
              @click="menuOpen = !menuOpen"
            >
              {{ user?.email }}
              <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <div
              v-if="menuOpen"
              class="absolute right-0 mt-2 w-48 rounded-2xl border border-white/50 bg-white/88 p-1.5 text-sm
                     shadow-apple backdrop-blur-2xl dark:border-white/10 dark:bg-gray-900/92"
              role="menu"
              @click="menuOpen = false"
            >
              <RouterLink to="/konto" class="block rounded-xl px-3 py-2 text-gray-700 transition hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10">Mein Konto</RouterLink>
              <RouterLink v-if="isAdmin" to="/admin" class="block rounded-xl px-3 py-2 text-gray-700 transition hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10">Administration</RouterLink>
              <button class="block w-full rounded-xl px-3 py-2 text-left text-gray-700 transition hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10" @click="doLogout">Abmelden</button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <main id="hauptinhalt" ref="mainEl" tabindex="-1" class="flex-1">
      <RouterView />
    </main>

    <AppFooter />
    <NotificationHost />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
import NotificationHost from '@/components/NotificationHost.vue'
import { useTheme } from '@/composables/useTheme'
import { fetchMe, isAdmin, isAuthenticated, logout, user } from '@/lib/auth'

const router = useRouter()
const menuOpen = ref(false)
const mainEl = ref<HTMLElement | null>(null)
const { isDark, toggleTheme } = useTheme()

function focusMain() {
  mainEl.value?.focus()
}

onMounted(() => {
  if (isAuthenticated.value) fetchMe()
})

function doLogout() {
  logout()
  router.push('/')
}
</script>
