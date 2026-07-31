<template>
  <div class="max-w-4xl mx-auto px-4 py-8 space-y-8">
    <header class="space-y-2">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Verwendete Komponenten &amp; Lizenzen</h1>
      <p class="text-sm text-gray-600 dark:text-gray-400">
        Diese Anwendung baut auf freier Software auf. Die Liste wird nicht
        gepflegt, sondern aus dem Bauteil-Register des Servers gelesen — sie
        beschreibt genau die Komponenten, die tatsächlich geladen sind.
      </p>
    </header>

    <div v-if="loading" class="text-sm text-gray-600 dark:text-gray-400">Lade Komponentenliste…</div>
    <div
      v-else-if="error"
      class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300"
    >
      {{ error }}
    </div>

    <template v-else>
      <!-- Quelltext-Pflicht (AGPL § 13) -->
      <section
        v-if="report?.source_disclosure_required"
        class="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg space-y-2"
      >
        <h2 class="font-semibold text-amber-900 dark:text-amber-200">Quelltext dieser Anwendung</h2>
        <p class="text-sm text-amber-900 dark:text-amber-200">
          Diese Anwendung setzt Komponenten unter der GNU Affero General Public
          License ein ({{ agplNames }}). Deren Lizenz verlangt, dass alle, die
          den Dienst über das Netz nutzen, den vollständigen Quelltext erhalten.
          Er wird deshalb offen bereitgestellt.
        </p>
        <p v-if="report.source_url" class="text-sm">
          <a
            :href="report.source_url"
            rel="noopener"
            class="text-amber-900 dark:text-amber-200 underline hover:no-underline font-medium"
          >{{ report.source_url }}</a>
        </p>
        <p v-else class="text-sm text-amber-900 dark:text-amber-200">
          <strong>Hinweis an den Betreiber:</strong> Es ist noch keine
          Quelltext-Adresse hinterlegt (<code>PDFAPP_SOURCE_URL</code>). Ohne
          sie ist die Lizenzbedingung nicht erfüllt.
        </p>
      </section>

      <!-- Komponenten nach Art gruppiert -->
      <section v-for="group in groups" :key="group.kind" class="space-y-3">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">{{ group.title }}</h2>
        <ul class="space-y-3">
          <li
            v-for="c in group.items"
            :key="c.key"
            class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-4 space-y-1"
          >
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <a
                :href="c.url"
                rel="noopener"
                class="font-medium text-primary-700 dark:text-primary-400 underline hover:no-underline"
              >{{ c.name }}</a>
              <span class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200">
                {{ c.license }}
              </span>
              <span
                v-if="c.copyleft_network"
                class="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-200"
              >Quelltext-Pflicht</span>
              <span
                v-if="!c.available"
                class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200"
              >in dieser Installation nicht aktiv</span>
            </div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{{ c.purpose }}</p>
            <p v-if="c.alternative" class="text-xs text-gray-600 dark:text-gray-400">
              Ersetzbar durch: {{ c.alternative }}
            </p>
          </li>
        </ul>
      </section>

      <section class="text-sm text-gray-700 dark:text-gray-300 space-y-3 border-t border-gray-200 dark:border-gray-700 pt-6">
        <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Warum fremde Bibliotheken</h2>
        <p>
          Das PDF-Format umfasst rund tausend Seiten Spezifikation, dazu kommen
          Schriftinterpretation, Bildkodierungen, Farbprofile und
          Verschlüsselungsverfahren. Ein selbst geschriebener Ersatz wäre
          gegenüber diesen seit Jahrzehnten geprüften Implementierungen auch
          sicherheitstechnisch ein Rückschritt.
        </p>
        <p>
          Die Abhängigkeit wird deshalb nicht vermieden, sondern eingefasst:
          Alle Fremdbibliotheken laufen über einen einzigen Zugangspunkt im
          Server. Ein Versionswechsel oder ein Austausch trifft eine Datei
          statt sieben — und diese Seite kann nicht veralten, weil sie aus
          demselben Register stammt.
        </p>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiGetJson } from '@/lib/api'

interface Component {
  key: string
  name: string
  kind: string
  purpose: string
  license: string
  url: string
  alternative: string
  copyleft_network: boolean
  available: boolean
}

interface Report {
  components: Component[]
  source_disclosure_required: boolean
  source_url: string | null
}

const report = ref<Report | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const KIND_TITLES: Record<string, string> = {
  bibliothek: 'Programmbibliotheken',
  programm: 'Externe Programme',
  rahmenwerk: 'Rahmenwerke',
}

const groups = computed(() => {
  const out: { kind: string; title: string; items: Component[] }[] = []
  for (const kind of ['bibliothek', 'programm', 'rahmenwerk']) {
    const items = (report.value?.components ?? []).filter((c) => c.kind === kind)
    if (items.length) out.push({ kind, title: KIND_TITLES[kind] ?? kind, items })
  }
  return out
})

const agplNames = computed(() =>
  (report.value?.components ?? [])
    .filter((c) => c.copyleft_network && c.available)
    .map((c) => c.name)
    .join(', '),
)

onMounted(async () => {
  try {
    report.value = await apiGetJson<Report>('/api/licenses')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Komponentenliste nicht abrufbar'
  } finally {
    loading.value = false
  }
})
</script>
