<template>
  <!-- Erscheint nur, wenn der Server tatsächlich AGPL-Komponenten meldet.
       Fällt PyMuPDF eines Tages weg, verschwindet der Hinweis von selbst,
       statt als falsche Angabe stehen zu bleiben. -->
  <aside
    v-if="visible"
    class="p-4 bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 rounded-lg
           text-sm text-gray-700 dark:text-gray-300 flex items-start gap-3"
  >
    <span aria-hidden="true" class="text-lg leading-none mt-0.5">📖</span>
    <p>
      <strong class="text-gray-900 dark:text-white">Offener Quelltext.</strong>
      Diese Anwendung baut auf freier Software auf. Darunter ist
      {{ agplNames }} — unter der GNU Affero GPL. Deren Lizenz verlangt, dass
      alle, die den Dienst nutzen, den Quelltext erhalten; er ist deshalb offen
      einsehbar.
      <a
        v-if="sourceUrl"
        :href="sourceUrl"
        rel="noopener"
        class="text-primary-700 dark:text-primary-400 underline hover:no-underline"
      >Quelltext ansehen</a>
      <RouterLink
        to="/lizenzen"
        class="text-primary-700 dark:text-primary-400 underline hover:no-underline"
      >Alle Komponenten und Lizenzen</RouterLink>
    </p>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { apiGetJson } from '@/lib/api'

interface Report {
  components: { name: string; copyleft_network: boolean; available: boolean }[]
  source_disclosure_required: boolean
  source_url: string | null
}

const report = ref<Report | null>(null)

const visible = computed(() => Boolean(report.value?.source_disclosure_required))
const sourceUrl = computed(() => report.value?.source_url || '')
const agplNames = computed(() =>
  (report.value?.components ?? [])
    .filter((c) => c.copyleft_network && c.available)
    .map((c) => c.name)
    .join(' und '),
)

onMounted(async () => {
  try {
    report.value = await apiGetJson<Report>('/api/licenses')
  } catch {
    // Ohne Antwort bleibt der Hinweis aus — die Fußzeile verlinkt die
    // Lizenzseite ohnehin dauerhaft.
  }
})
</script>
