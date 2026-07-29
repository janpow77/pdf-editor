<template>
  <div class="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
    <header class="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <RouterLink to="/" class="flex items-center gap-2 font-semibold text-gray-900 dark:text-white">
          <span aria-hidden="true">📄</span> PDF-Editor
        </RouterLink>
        <span class="text-xs px-2 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-300">
          Kostenlos · Keine Datenspeicherung
        </span>
      </div>
    </header>

    <main class="flex-1">
      <RouterView />
    </main>

    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import AppFooter from '@/components/AppFooter.vue'
</script>
