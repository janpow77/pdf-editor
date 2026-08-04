<template>
  <!--
    Die Live-Region liegt global über der Anwendung. Die mittige, kompakte Form
    erinnert an Dynamic Island/macOS-Benachrichtigungen, ohne wichtige Inhalte
    dauerhaft zu verdecken. `pointer-events-none` lässt Klicks neben den Toasts
    weiterhin durch; nur die Meldung selbst bleibt bedienbar.
  -->
  <div
    class="pointer-events-none fixed inset-x-0 top-3 z-[100] flex flex-col items-center gap-2 px-4 sm:top-5"
    aria-live="polite"
    aria-relevant="additions removals"
  >
    <TransitionGroup name="notification">
      <article
        v-for="item in notifications"
        :key="item.id"
        class="pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-[1.15rem]
               border border-white/[0.45] bg-gray-950/90 px-4 py-3 text-white
               shadow-[0_18px_50px_rgba(0,0,0,0.28),0_2px_8px_rgba(0,0,0,0.18)]
               backdrop-blur-2xl dark:border-white/10 dark:bg-gray-900/[0.88]"
        :role="item.type === 'error' ? 'alert' : 'status'"
      >
        <span
          class="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold"
          :class="iconClass(item.type)"
          aria-hidden="true"
        >{{ icon(item.type) }}</span>

        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold leading-5 tracking-[-0.01em]">{{ item.title }}</p>
          <p v-if="item.message" class="mt-0.5 text-sm leading-5 text-gray-200">{{ item.message }}</p>
        </div>

        <button
          type="button"
          class="-mr-1 grid h-8 w-8 shrink-0 place-items-center rounded-full text-gray-300
                 transition hover:bg-white/10 hover:text-white active:scale-95"
          :aria-label="`${item.title} schließen`"
          @click="remove(item.id)"
        >×</button>
      </article>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { useNotifications, type NotificationType } from '@/composables/useNotifications'

const { notifications, remove } = useNotifications()

function icon(type: NotificationType): string {
  return { success: '✓', info: 'i', warning: '!', error: '!' }[type]
}

function iconClass(type: NotificationType): string {
  return {
    success: 'bg-emerald-400/20 text-emerald-300',
    info: 'bg-sky-400/20 text-sky-300',
    warning: 'bg-amber-400/20 text-amber-300',
    error: 'bg-rose-400/20 text-rose-300',
  }[type]
}
</script>

<style scoped>
/*
 * Kurze Translation plus Skalierung wirkt direkt und federnd, ohne lange
 * Animationen. Die globale Reduced-Motion-Regel deaktiviert sie bei Bedarf.
 */
.notification-enter-active,
.notification-leave-active {
  transition: opacity 180ms ease, transform 240ms cubic-bezier(.2, .9, .2, 1.15);
}
.notification-enter-from,
.notification-leave-to {
  opacity: 0;
  transform: translateY(-14px) scale(.96);
}
</style>
