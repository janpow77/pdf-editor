<template>
  <component :is="as" :class="panelClass">
    <slot />
  </component>
</template>

<script setup lang="ts">
/**
 * Einheitliche Karten- und Informationsfläche für Werkzeugoptionen.
 *
 * Die Komponente bündelt Material, Radius, Kontrast und Tonalität. Dadurch
 * müssen Fachmodule keine eigenen Kombinationen aus Hintergrund, Rahmen und
 * Schatten pflegen. `as` erlaubt dabei passende semantische Elemente wie
 * section, article oder li, ohne die Gestaltung zu duplizieren.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  as?: string
  tone?: 'default' | 'info' | 'success' | 'warning' | 'danger'
  padding?: 'sm' | 'md' | 'lg'
}>(), {
  as: 'div',
  tone: 'default',
  padding: 'md',
})

const panelClass = computed(() => [
  'rounded-[1.25rem] shadow-apple-sm ring-1 backdrop-blur-xl',
  {
    sm: 'p-3',
    md: 'p-4 sm:p-5',
    lg: 'p-5 sm:p-6',
  }[props.padding],
  {
    default: 'bg-white/85 text-gray-800 ring-gray-300/80 dark:bg-white/[0.07] dark:text-gray-100 dark:ring-gray-600',
    info: 'bg-blue-50/85 text-blue-900 ring-blue-200 dark:bg-blue-500/10 dark:text-blue-100 dark:ring-blue-400/30',
    success: 'bg-emerald-50/85 text-emerald-900 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-100 dark:ring-emerald-400/30',
    warning: 'bg-amber-50/85 text-amber-900 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-100 dark:ring-amber-400/30',
    danger: 'bg-rose-50/85 text-rose-900 ring-rose-200 dark:bg-rose-500/10 dark:text-rose-100 dark:ring-rose-400/30',
  }[props.tone],
])
</script>
