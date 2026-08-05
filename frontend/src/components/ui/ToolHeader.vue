<template>
  <header class="flex flex-wrap items-center gap-3">
    <UiButton variant="ghost" size="sm" aria-label="Zur Werkzeugübersicht zurückkehren" @click="$emit('back')">
      <span aria-hidden="true">←</span>
      Zurück
    </UiButton>
    <div class="min-w-0">
      <h2 class="truncate text-xl font-semibold tracking-[-0.025em] text-gray-950 dark:text-white">
        {{ title }}
      </h2>
      <p v-if="description" class="mt-0.5 text-sm leading-5 text-gray-600 dark:text-gray-300">
        {{ description }}
      </p>
    </div>
    <div v-if="$slots.actions" class="ml-auto flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
/**
 * Verbindlicher Kopf aller Fachwerkzeuge.
 *
 * Zurück-Navigation, Überschriftshierarchie und optionale Aktionen werden
 * dadurch nicht mehr in jedem Modul separat nachgebaut.
 */
import UiButton from '@/components/ui/UiButton.vue'

defineProps<{
  title: string
  description?: string
}>()

defineEmits<{ (event: 'back'): void }>()
</script>
