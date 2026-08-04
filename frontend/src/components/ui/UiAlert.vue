<template>
  <div :class="alertClass" :role="role">
    <slot />
  </div>
</template>

<script setup lang="ts">
/**
 * Konsistente Inline-Rückmeldung für Information, Erfolg, Warnung und Fehler.
 *
 * Globale Toasts informieren über den Vorgang; dieses Element hält denselben
 * Zustand zusätzlich direkt im Arbeitskontext sichtbar und barrierefrei.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  tone?: 'info' | 'success' | 'warning' | 'danger'
  live?: boolean
}>(), {
  tone: 'info',
  live: false,
})

const role = computed(() => props.tone === 'danger' ? 'alert' : props.live ? 'status' : undefined)
const alertClass = computed(() => [
  'rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ring-1',
  {
    info: 'bg-blue-50/85 text-blue-900 ring-blue-200 dark:bg-blue-500/10 dark:text-blue-100 dark:ring-blue-400/30',
    success: 'bg-emerald-50/85 text-emerald-900 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-100 dark:ring-emerald-400/30',
    warning: 'bg-amber-50/85 text-amber-900 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-100 dark:ring-amber-400/30',
    danger: 'bg-rose-50/85 text-rose-900 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-100 dark:ring-rose-400/30',
  }[props.tone],
])
</script>
