<template>
  <button
    v-bind="$attrs"
    type="button"
    :disabled="disabled"
    :class="buttonClass"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
/**
 * Einheitlicher runder Button für kompakte Werkzeugaktionen.
 *
 * Entfernen, Verschieben, Drehen und Navigieren erhalten dadurch identische
 * Trefferfläche, Fokusdarstellung und Disabled-Zustände.
 */
import { computed } from 'vue'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  variant?: 'default' | 'danger' | 'primary'
  size?: 'sm' | 'md'
  disabled?: boolean
}>(), {
  variant: 'default',
  size: 'md',
  disabled: false,
})

const buttonClass = computed(() => [
  'inline-grid shrink-0 place-items-center rounded-full shadow-sm ring-1 transition',
  'active:scale-95 disabled:cursor-not-allowed disabled:opacity-35',
  props.size === 'sm' ? 'h-9 w-9 text-sm' : 'h-11 w-11 text-base',
  {
    default: 'bg-white/85 text-gray-700 ring-gray-300 hover:-translate-y-0.5 hover:bg-white hover:shadow-apple dark:bg-white/10 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-white/15',
    primary: 'bg-primary-600 text-white ring-primary-600 hover:-translate-y-0.5 hover:bg-primary-700 hover:shadow-apple',
    danger: 'bg-rose-50 text-rose-700 ring-rose-200 hover:-translate-y-0.5 hover:bg-rose-100 dark:bg-rose-500/10 dark:text-rose-200 dark:ring-rose-400/30 dark:hover:bg-rose-500/20',
  }[props.variant],
])
</script>
