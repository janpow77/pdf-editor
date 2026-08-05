<template>
  <div class="space-y-5">
    <ToolHeader title="Digital signieren" description="Eine zertifikatsbasierte PAdES-Signatur mit eigenem PKCS#12-Zertifikat erstellen." @back="$emit('back')" />

    <UiAlert tone="info">
      Zertifikat und Passwort werden ausschließlich für diesen Vorgang verwendet und weder gespeichert noch protokolliert.
    </UiAlert>

    <FileDrop v-model="file" label="PDF" />
    <FileDrop v-model="cert" accept=".p12,.pfx" label="Zertifikat (.p12/.pfx)" />

    <UiPanel v-if="file && cert" class="space-y-4">
      <UiField label="Zertifikats-Passwort" for-id="digital-sign-passphrase">
        <input id="digital-sign-passphrase" v-model="passphrase" type="password" class="ui-control w-full" autocomplete="new-password" />
      </UiField>
      <div class="grid gap-4 sm:grid-cols-2">
        <UiField label="Grund (optional)" for-id="digital-sign-reason">
          <input id="digital-sign-reason" v-model="reason" type="text" placeholder="z. B. Freigabe" class="ui-control w-full" />
        </UiField>
        <UiField label="Ort (optional)" for-id="digital-sign-location">
          <input id="digital-sign-location" v-model="location" type="text" class="ui-control w-full" />
        </UiField>
      </div>
      <UiField label="Zeitstempel-Dienst (optional)" for-id="digital-sign-tsa" hint="RFC-3161-Dienst für einen extern bestätigten Signaturzeitpunkt.">
        <input id="digital-sign-tsa" v-model="tsaUrl" type="url" placeholder="https://freetsa.org/tsr" class="ui-control w-full" />
      </UiField>
    </UiPanel>

    <UiAlert v-if="done" tone="success" live>PDF digital signiert und heruntergeladen.</UiAlert>

    <UiButton v-if="file && cert" variant="primary" size="lg" :loading="loading" @click="apply">
      {{ loading ? 'Signiere…' : 'Digital signieren' }}
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
import { useToolRun } from '@/composables/useToolRun'

defineEmits<{ (event: 'back'): void }>()

const { loading, error, done, run } = useToolRun()
const file = ref<File | null>(null)
const cert = ref<File | null>(null)
const passphrase = ref('')
const reason = ref('')
const location = ref('')
const tsaUrl = ref('')

async function apply(): Promise<void> {
  if (!file.value || !cert.value) return
  const fd = new FormData()
  fd.append('file', file.value)
  fd.append('certificate', cert.value)
  fd.append('passphrase', passphrase.value)
  fd.append('reason', reason.value)
  fd.append('location', location.value)
  fd.append('tsa_url', tsaUrl.value.trim())
  await run('/api/pdf-extras/sign-digital', fd, file.value.name.replace(/\.pdf$/i, '_signiert.pdf'))
}
</script>
