<template>
  <div class="space-y-5">
    <ToolHeader title="KI-Assistent" description="Dokument lokal zusammenfassen, übersetzen oder inhaltlich befragen." @back="$emit('back')" />

    <UiAlert tone="info">
      Die Verarbeitung läuft ausschließlich auf eigener Infrastruktur. KI-Antworten können Fehler enthalten und müssen fachlich geprüft werden.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file" class="space-y-4">
      <div class="flex flex-wrap gap-2" role="group" aria-label="KI-Aufgabe auswählen">
        <UiButton v-for="item in modes" :key="item.value" size="sm" :variant="mode === item.value ? 'primary' : 'secondary'" :aria-pressed="mode === item.value" @click="mode = item.value">
          {{ item.label }}
        </UiButton>
      </div>
      <UiField v-if="mode === 'ask'" label="Frage zum Dokument" for-id="ai-question" hint="Mindestens drei, höchstens 2.000 Zeichen.">
        <textarea id="ai-question" v-model="question" rows="3" maxlength="2000" class="ui-control w-full" placeholder="z. B. Welche Fristen werden genannt?"></textarea>
      </UiField>
      <UiField v-else-if="mode === 'translate'" label="Zielsprache" for-id="ai-language">
        <input id="ai-language" v-model="targetLanguage" type="text" maxlength="60" list="ai-languages" class="ui-control w-full" />
        <datalist id="ai-languages"><option value="Englisch" /><option value="Französisch" /><option value="Italienisch" /><option value="Spanisch" /><option value="Polnisch" /><option value="Deutsch" /></datalist>
      </UiField>
    </UiPanel>

    <UiPanel v-if="answer" class="space-y-3">
      <div class="flex items-center justify-between gap-3"><strong>Antwort</strong><UiButton size="sm" @click="copyAnswer">{{ copied ? 'Kopiert ✓' : 'Kopieren' }}</UiButton></div>
      <p class="whitespace-pre-wrap text-sm leading-6 text-gray-700 dark:text-gray-200">{{ answer }}</p>
      <p class="text-xs text-gray-600 dark:text-gray-400">KI-generiert{{ model ? ` (${model})` : '' }} – bitte fachlich prüfen.</p>
    </UiPanel>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" :disabled="!canRun" @click="apply">
      {{ loading ? 'KI arbeitet…' : activeModeLabel }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { useNotifications } from '@/composables/useNotifications'
import { apiPost } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

type AiMode = 'summary' | 'ask' | 'translate' | 'keywords' | 'outline'
interface AiResponse { answer?: unknown; model?: unknown }

const notifications = useNotifications()
const file = ref<File | null>(null)
const mode = ref<AiMode>('summary')
const question = ref('')
const targetLanguage = ref('Englisch')
const answer = ref('')
const model = ref('')
const loading = ref(false)
const error = ref<string | null>(null)
const copied = ref(false)
let generation = 0
let controller: AbortController | null = null
let copiedTimer: ReturnType<typeof globalThis.setTimeout> | null = null

const modes: { value: AiMode; label: string }[] = [
  { value: 'summary', label: 'Zusammenfassen' }, { value: 'ask', label: 'Frage stellen' },
  { value: 'translate', label: 'Übersetzen' }, { value: 'keywords', label: 'Schlagwörter' },
  { value: 'outline', label: 'Gliederung' },
]
const activeModeLabel = computed(() => modes.find((item) => item.value === mode.value)?.label ?? 'Ausführen')
const canRun = computed(() => {
  if (mode.value === 'ask') return question.value.trim().length >= 3
  if (mode.value === 'translate') return targetLanguage.value.trim().length >= 2
  return true
})

watch([file, mode], () => {
  generation += 1
  controller?.abort()
  controller = null
  answer.value = ''
  model.value = ''
  error.value = null
  copied.value = false
  loading.value = false
})

async function apply(): Promise<void> {
  const currentFile = file.value
  if (!currentFile || !canRun.value || loading.value) return
  const currentGeneration = ++generation
  const requestController = new AbortController()
  controller?.abort()
  controller = requestController
  loading.value = true
  error.value = null
  answer.value = ''
  model.value = ''

  try {
    const formData = new FormData()
    formData.append('file', currentFile)
    let url = '/api/pdf-more/ai/summarize'
    if (mode.value === 'ask') {
      url = '/api/pdf-more/ai/ask'
      formData.append('question', question.value.trim())
    } else if (mode.value === 'translate') {
      url = '/api/pdf-more/ai/translate'
      formData.append('target_language', targetLanguage.value.trim())
    } else if (mode.value === 'keywords') url = '/api/pdf-more/ai/keywords'
    else if (mode.value === 'outline') url = '/api/pdf-more/ai/outline'

    const response = await apiPost(url, formData, { signal: requestController.signal, timeout: 10 * 60 * 1000, notifyOnError: false })
    const body = await response.json() as AiResponse
    if (currentGeneration !== generation || file.value !== currentFile) return
    const responseText = typeof body.answer === 'string' ? body.answer.trim() : ''
    if (!responseText) throw new Error('Das Sprachmodell hat keine Antwort zurückgegeben.')
    answer.value = responseText.slice(0, 500_000)
    model.value = typeof body.model === 'string' ? body.model.slice(0, 120) : ''
  } catch (caught: unknown) {
    if (requestController.signal.aborted || currentGeneration !== generation) return
    error.value = caught instanceof Error ? caught.message : 'KI-Verarbeitung fehlgeschlagen.'
    notifications.error('KI-Verarbeitung fehlgeschlagen', error.value)
  } finally {
    if (currentGeneration === generation) loading.value = false
    if (controller === requestController) controller = null
  }
}

async function copyAnswer(): Promise<void> {
  if (!answer.value) return
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Die Zwischenablage ist in diesem Browserkontext nicht verfügbar.')
    await navigator.clipboard.writeText(answer.value)
    copied.value = true
    if (copiedTimer) globalThis.clearTimeout(copiedTimer)
    copiedTimer = globalThis.setTimeout(() => { copied.value = false; copiedTimer = null }, 1500)
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Antwort konnte nicht kopiert werden.'
  }
}

onBeforeUnmount(() => {
  generation += 1
  controller?.abort()
  if (copiedTimer) globalThis.clearTimeout(copiedTimer)
})
</script>
