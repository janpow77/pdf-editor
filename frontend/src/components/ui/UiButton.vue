<template>
  <button
    v-bind="$attrs"
    :type="type"
    :disabled="disabled || loading"
    :class="buttonClass"
  >
    <span
      v-if="loading"
      class="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-r-transparent"
      aria-hidden="true"
    ></span>
    <slot />
  </button>
</template>

<script setup lang="ts">
/**
 * Einheitlicher Button für sämtliche Fachmodule.
 *
 * Varianten, Radien, Abstände, Ladezustand und Interaktionen werden an einer
 * Stelle gepflegt. Fachkomponenten beschreiben nur noch die fachliche Variante
 * und wiederholen keine langen Tailwind-Kombinationen.
 */
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
  loading?: boolean
  block?: boolean
}>(), {
  variant: 'secondary',
  size: 'md',
  type: 'button',
  disabled: false,
  loading: false,
  block: false,
})

const buttonClass = computed(() => [
  'inline-flex items-center justify-center gap-2 rounded-full font-semibold shadow-sm transition',
  'focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-45',
  'active:scale-[0.97]',
  props.block ? 'w-full' : '',
  {
    sm: 'min-h-9 px-3.5 py-2 text-sm',
    md: 'min-h-10 px-4 py-2.5 text-sm',
    lg: 'min-h-12 px-6 py-3 text-base',
  }[props.size],
  {
    primary: 'bg-primary-600 text-white hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-apple',
    secondary: 'bg-white/85 text-gray-800 ring-1 ring-gray-300 hover:-translate-y-0.5 hover:bg-white hover:shadow-apple dark:bg-white/10 dark:text-gray-100 dark:ring-gray-600 dark:hover:bg-white/15',
    danger: 'bg-rose-50 text-rose-700 ring-1 ring-rose-200 hover:-translate-y-0.5 hover:bg-rose-100 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-400/30 dark:hover:bg-rose-500/20',
    ghost: 'bg-transparent text-gray-600 shadow-none hover:bg-black/5 hover:text-gray-950 dark:text-gray-300 dark:hover:bg-white/10 dark:hover:text-white',
  }[props.variant],
])
</script>
