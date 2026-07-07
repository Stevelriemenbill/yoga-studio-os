<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Card from 'primevue/card'

import { listMembers } from '@/api/members'
import { checkInManual, checkInQr, getMemberPass } from '@/api/training'
import type { Member, MemberPass, CheckIn } from '@/types'

const members = ref<Member[]>([])
const error = ref('')

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

// Manual check-in
const manualMemberId = ref('')
const manualSessionId = ref('')
const manualResult = ref<CheckIn | null>(null)

// Pass
const passMemberId = ref('')
const pass = ref<MemberPass | null>(null)

// QR check-in
const qrPayload = ref('')
const qrSessionId = ref('')
const qrResult = ref<CheckIn | null>(null)

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('de-DE')
}

async function loadMembers() {
  try {
    members.value = await listMembers()
  } catch {
    error.value = 'Mitglieder konnten nicht geladen werden.'
  }
}

async function doManual() {
  if (!manualMemberId.value) return
  error.value = ''
  try {
    manualResult.value = await checkInManual({
      member_id: manualMemberId.value,
      session_id: manualSessionId.value || undefined,
    })
  } catch {
    error.value = 'Manueller Check-in fehlgeschlagen.'
  }
}

async function loadPass() {
  if (!passMemberId.value) return
  error.value = ''
  try {
    pass.value = await getMemberPass(passMemberId.value)
  } catch {
    error.value = 'Pass konnte nicht geladen werden.'
  }
}

async function doQr() {
  if (!qrPayload.value) return
  error.value = ''
  try {
    qrResult.value = await checkInQr({
      qr_payload: qrPayload.value,
      session_id: qrSessionId.value || undefined,
    })
  } catch {
    error.value = 'QR-Check-in fehlgeschlagen.'
  }
}

onMounted(loadMembers)
</script>

<template>
  <div class="page">
    <h1>Check-in</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>Manueller Check-in</template>
      <template #content>
        <div class="form">
          <label>Mitglied</label>
          <Dropdown
            v-model="manualMemberId"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Mitglied wählen"
            filter
          />
          <label>Session-ID (optional)</label>
          <InputText v-model="manualSessionId" />
          <Button label="Check-in" :disabled="!manualMemberId" @click="doManual" />
          <p v-if="manualResult" class="success">
            Eingecheckt um {{ fmtDateTime(manualResult.checked_in_at) }}
          </p>
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>QR-Pass</template>
      <template #content>
        <div class="form">
          <label>Mitglied</label>
          <Dropdown
            v-model="passMemberId"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Mitglied wählen"
            filter
          />
          <Button label="Pass anzeigen" :disabled="!passMemberId" @click="loadPass" />
          <template v-if="pass">
            <p><strong>Token:</strong> {{ pass.token }}</p>
            <p><strong>QR-Payload:</strong> {{ pass.qr_payload }}</p>
          </template>
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>QR Check-in</template>
      <template #content>
        <div class="form">
          <label>QR-Payload</label>
          <Textarea v-model="qrPayload" rows="3" autoResize />
          <label>Session-ID (optional)</label>
          <InputText v-model="qrSessionId" />
          <Button label="Check-in" :disabled="!qrPayload" @click="doQr" />
          <p v-if="qrResult" class="success">
            Eingecheckt um {{ fmtDateTime(qrResult.checked_in_at) }}
          </p>
        </div>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.error {
  color: #dc2626;
}
.success {
  color: #16a34a;
}
.block {
  margin-bottom: 1rem;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 480px;
}
.form label {
  font-weight: 600;
}
</style>
