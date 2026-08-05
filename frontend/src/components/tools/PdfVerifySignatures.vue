<template>
  <div class="space-y-5">
    <ToolHeader title="Signatur prüfen" description="Integrität, Signierzeitpunkt und Unterzeichner digitaler PDF-Signaturen auswerten." @back="$emit('back')" />

    <UiAlert tone="info">
      Ohne hinterlegte Vertrauensanker kann die Zertifikatskette nicht abschließend bewertet werden; die Integritätsprüfung bleibt dennoch möglich.
    </UiAlert>

    <FileDrop v-model="file" />

    <UiPanel v-if="file">
      <UiField label="Vertrauensanker (optional)" for-id="signature-anchors" hint="PEM, CRT, CER oder DER. Ohne Anker wird nur die Integrität bewertet.">
        <input id="signature-anchors" type="file" accept=".pem,.crt,.cer,.der" class="block w-full text-sm text-gray-600 dark:text-gray-300" @change="onAnchors" />
      </UiField>
    </UiPanel>

    <div v-if="report" class="space-y-3">
      <UiAlert v-if="report.count === 0" tone="warning">Dieses PDF enthält keine digitalen Signaturen.</UiAlert>
      <UiPanel v-for="(signature, index) in report.signatures" :key="index" :tone="signature.intact ? 'success' : 'danger'" class="space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-semibold">{{ signature.field }}</span>
          <span class="rounded-full bg-white/70 px-2.5 py-1 text-xs font-semibold dark:bg-black/20">
            {{ signature.error ? 'Prüfung fehlgeschlagen' : signature.intact ? 'Unverändert' : 'Verändert' }}
          </span>
        </div>
        <template v-if="!signature.error">
          <dl class="grid grid-cols-[auto,1fr] gap-x-4 gap-y-1 text-sm">
            <dt class="opacity-70">Unterzeichner</dt><dd>{{ signature.signer }}</dd>
            <dt class="opacity-70">Signiert am</dt><dd>{{ signature.signing_time || 'unbekannt' }}</dd>
            <dt class="opacity-70">CMS gültig</dt><dd>{{ signature.valid_cms ? 'ja' : 'nein' }}</dd>
            <dt class="opacity-70">Abdeckung</dt><dd>{{ signature.coverage }}</dd>
            <dt class="opacity-70">Vertrauenskette</dt>
            <dd>{{ anchors ? (signature.trusted ? 'vertrauenswürdig' : 'nicht bestätigt') : 'nicht bewertet' }}</dd>
          </dl>
          <p class="text-xs opacity-75">{{ signature.hinweis }}</p>
        </template>
        <UiAlert v-else tone="danger">{{ signature.error }}</UiAlert>
      </UiPanel>
    </div>

    <UiButton v-if="file" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Prüfe…' : 'Signaturen prüfen' }}
    </UiButton>
    <UiAlert v-if="error" tone="danger">{{ error }}</UiAlert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDrop from '@/components/FileDrop.vue'
import ToolHeader from '@/components/ui/ToolHeader.vue'
import UiAlert from '@/components/ui/UiAlert.vue'
import UiButton from '@/components/ui/UiButton.vue'
import UiField from '@/components/ui/UiField.vue'
import UiPanel from '@/components/ui/UiPanel.vue'
import { apiPost } from '@/lib/api'

defineEmits<{ (event: 'back'): void }>()

interface SignatureEntry {
  field: string
  signer?: string
  intact?: boolean
  valid_cms?: boolean
  coverage?: string
  signing_time?: string
  trusted?: boolean
  hinweis?: string
  error?: string
}
interface Report {
  count: number
  signatures: SignatureEntry[]
}

const file = ref<File | null>(null)
const anchors = ref<File | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const report = ref<Report | null>(null)

function onAnchors(event: Event): void {
  anchors.value = (event.target as HTMLInputElement).files?.[0] ?? null
  report.value = null
}

async function apply(): Promise<void> {
  if (!file.value) return
  loading.value = true
  error.value = null
  report.value = null
  try {
    const fd = new FormData()
    fd.append('file', file.value)
    if (anchors.value) fd.append('trust_anchors', anchors.value)
    const response = await apiPost('/api/pdf-more/verify-signatures', fd)
    report.value = (await response.json()) as Report
  } catch (caught: unknown) {
    error.value = caught instanceof Error ? caught.message : 'Unbekannter Fehler'
  } finally {
    loading.value = false
  }
}
</script>
