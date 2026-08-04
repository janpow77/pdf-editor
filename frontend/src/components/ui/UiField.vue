<template>
  <div class="space-y-1.5">
    <label v-if="label" :for="forId" class="block text-sm font-semibold text-gray-700 dark:text-gray-200">
      {{ label }}
      <span v-if="required" class="text-rose-600 dark:text-rose-300" aria-hidden="true">*</span>
    </label>
    <slot />
    <p v-if="hint && !error" class="text-xs leading-5 text-gray-600 dark:text-gray-400">{{ hint }}</p>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
/**
 * Einheitliche Beschriftung, Hilfestellung und Fehlermeldung für Eingaben.
 *
 * Die eigentliche Eingabe bleibt als Slot flexibel; semantische Zuordnung und
 * vertikale Abstände sind dennoch in allen Werkzeugen identisch.
 */
import UiAlert from '@/components/ui/UiAlert.vue'

withDefaults(defineProps<{
  label?: string
  forId?: string
  hint?: string
  error?: string | null
  required?: boolean
}>(), {
  label: '',
  forId: undefined,
  hint: '',
  error: null,
  required: false,
})
</script>
