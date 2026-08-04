<template>
  <div class="min-h-screen flex flex-col bg-[#f5f5f7] text-gray-950 transition-colors dark:bg-[#09090b] dark:text-white">
    <a
      href="#hauptinhalt"
      class="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[110] focus:rounded-full focus:bg-primary-600 focus:px-4 focus:py-2 focus:text-white focus:shadow-apple"
      @click="focusMain"
    >Zum Hauptinhalt springen</a>

    <header class="sticky top-0 z-40 border-b border-black/5 bg-white/[0.72] backdrop-blur-2xl dark:border-white/10 dark:bg-gray-950/[0.72]">
      <div
        class="mx-auto flex items-center justify-between gap-3 px-4 transition-all duration-200 sm:px-6"
        :class="isWorkspaceActive ? 'max-w-[1800px] py-1.5' : 'max-w-[1600px] py-3'"
      >
        <RouterLink
          to="/"
          class="group flex min-w-0 items-center gap-2.5 rounded-full pr-3 text-sm font-semibold tracking-[-0.01em] text-gray-950 transition hover:bg-black/[0.035] active:scale-[0.98] dark:text-white dark:hover:bg-white/[0.07]"
          @click="closeWorkspace"
        >
          <img
            src="/auditlogo.png"
            alt=""
            aria-hidden="true"
            class="shrink-0 rounded-xl object-contain transition-all"
            :class="isWorkspaceActive ? 'h-8 w-8' : 'h-10 w-10'"
          />
          <span class="truncate">{{ isWorkspaceActive ? activeWorkspace?.toolName : 'PDF-Editor' }}</span>
        </RouterLink>

        <div class="flex shrink-0 items-center gap-2">
          <UiIconButton
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
          </UiIconButton>

          <RouterLink
            v-if="!isWorkspaceActive && !isAuthenticated"
            to="/login"
            class="rounded-full bg-gray-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-apple active:scale-[0.98] dark:bg-white dark:text-gray-950"
          >Anmelden</RouterLink>

          <!--
            Eine Disclosure-Navigation ist hier semantisch passender als ein
            ARIA-Menü: Die enthaltenen Ziele sind normale Links. Außenklick,
            Escape und Fokus-Rückgabe werden dennoch vollständig unterstützt.
          -->
          <div v-else-if="!isWorkspaceActive" ref="accountMenu" class="relative">
            <button
              ref="accountButton"
              type="button"
              class="flex max-w-56 items-center gap-1.5 rounded-full bg-white/80 px-3.5 py-2 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-black/5 backdrop-blur-xl transition hover:shadow-apple active:scale-[0.98] dark:bg-white/10 dark:text-gray-200 dark:ring-white/10"
              :aria-expanded="menuOpen"
              aria-controls="account-navigation"
              @click="menuOpen = !menuOpen"
              @keydown.esc.stop="closeAccountMenu(true)"
            >
              <span class="truncate">{{ user?.email ?? 'Mein Konto' }}</span>
              <svg class="h-3 w-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
            </button>
            <nav
              v-if="menuOpen"
              id="account-navigation"
              class="absolute right-0 mt-2 w-48 rounded-2xl border border-white/50 bg-white/[0.92] p-1.5 text-sm shadow-apple backdrop-blur-2xl dark:border-white/10 dark:bg-gray-900/[0.94]"
              aria-label="Kontonavigation"
              @keydown.esc.stop="closeAccountMenu(true)"
              @click="closeAccountMenu()"
            >
              <RouterLink to="/konto" class="block rounded-xl px-3 py-2 text-gray-700 transition hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10">Mein Konto</RouterLink>
              <RouterLink v-if="isAdmin" to="/admin" class="block rounded-xl px-3 py-2 text-gray-700 transition hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10">Administration</RouterLink>
              <button type="button" class="block w-full rounded-xl px-3 py-2 text-left text-gray-700 transition hover:bg-black/5 dark:text-gray-200 dark:hover:bg-white/10" @click="doLogout">Abmelden</button>
            </nav>
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
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRouter } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
import NotificationHost from '@/components/NotificationHost.vue'
import UiIconButton from '@/components/ui/UiIconButton.vue'
import { useNotifications } from '@/composables/useNotifications'
import { useTheme } from '@/composables/useTheme'
import { useWorkspace } from '@/composables/useWorkspace'
import { fetchMe, isAdmin, isAuthenticated, logout, user } from '@/lib/auth'

const router = useRouter()
const notifications = useNotifications()
const menuOpen = ref(false)
const mainEl = ref<HTMLElement | null>(null)
const accountMenu = ref<HTMLElement | null>(null)
const accountButton = ref<HTMLButtonElement | null>(null)
const { isDark, toggleTheme } = useTheme()
const { activeWorkspace, isWorkspaceActive, closeWorkspace } = useWorkspace()

function focusMain(): void {
  mainEl.value?.focus()
}

function closeAccountMenu(restoreFocus = false): void {
  menuOpen.value = false
  if (restoreFocus) accountButton.value?.focus()
}

function onDocumentPointerDown(event: PointerEvent): void {
  const target = event.target
  if (menuOpen.value && target instanceof Node && !accountMenu.value?.contains(target)) closeAccountMenu()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  if (isAuthenticated.value) {
    void fetchMe().catch((caught: unknown) => {
      notifications.warning(
        'Kontodaten nicht geladen',
        caught instanceof Error ? caught.message : 'Die Kontodaten konnten nicht abgerufen werden.',
      )
    })
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocumentPointerDown)
})

function doLogout(): void {
  logout()
  closeWorkspace()
  closeAccountMenu()
  void router.push('/')
}
</script>
