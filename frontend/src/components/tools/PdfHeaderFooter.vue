<template>
  <div class="space-y-4">
    <div class="flex items-center gap-3">
      <button class="text-sm text-gray-500 dark:text-gray-400 hover:text-primary-600" @click="$emit('back')">← Zurück</button>
      <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Kopf- und Fußzeile</h2>
    </div>

    <FileDrop v-model="file" />

    <div v-if="file" class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
      <p class="text-xs text-gray-400">Platzhalter: {page}, {total}, {date}, {title}</p>
      <div class="grid grid-cols-3 gap-3">
        <input v-model="fields.header_left" placeholder="Kopf links" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model="fields.header_center" placeholder="Kopf Mitte" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model="fields.header_right" placeholder="Kopf rechts" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model="fields.footer_left" placeholder="Fuß links" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model="fields.footer_center" placeholder="Fuß Mitte" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        <input v-model="fields.footer_right" placeholder="Fuß rechts" class="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
      </div>
      <div class="flex gap-3 items-end">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Schriftgröße</label>
          <input v-model.number="fontSize" type="number" min="6" max="18" class="w-24 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ab Seite</label>
          <input v-model.number="startPage" type="number" min="1" class="w-24 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white" />
        </div>
      </div>
    </div>

    <div v-if="done" class="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg text-sm text-green-700 dark:text-green-300">
      Kopf-/Fußzeile eingefügt, Datei heruntergeladen.
    </div>

    <button
      v-if="file"
      :disabled="loading || !hasContent"
      class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
      @click="apply"
    >
      {{ loading ? 'Verarbeite…' : 'Einfügen' }}
    </button>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (e: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const fields = reactive({
  header_left: '', header_center: '', header_right: '',
  footer_left: '', footer_center: '', footer_right: '',
})
const fontSize = ref(9)
const startPage = ref(1)
const hasContent = computed(() => Object.values(fields).some((v) => v.trim()))

async function apply() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  for (const [k, v] of Object.entries(fields)) fd.append(k, v)
  fd.append('font_size', String(fontSize.value))
  fd.append('start_page', String(startPage.value))
  await run('/api/pdf-editor/header-footer', fd, file.value.name.replace(/\.pdf$/i, '_kopf_fuss.pdf'))
}
</script>
