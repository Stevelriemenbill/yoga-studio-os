<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Card from 'primevue/card'

import { listMembers } from '@/api/members'
import {
  checkInManual,
  checkInQr,
  getMemberPass,
  listPendingAttendance,
  confirmAttendance,
  rejectAttendance,
} from '@/api/training'
import type { Member, MemberPass, CheckIn, Attendance } from '@/types'

const members = ref<Member[]>([])
const error = ref('')

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

const memberName = (id: string): string => {
  const m = members.value.find((x) => x.id === id)
  return m ? `${m.first_name} ${m.last_name}` : id
}

// Pending self check-ins awaiting staff confirmation.
const pending = ref<Attendance[]>([])
const pendingBusy = ref<string | null>(null)

async function loadPending() {
  try {
    pending.value = await listPendingAttendance()
  } catch {
    error.value = 'Ausstehende Check-ins konnten nicht geladen werden.'
  }
}

async function confirm(a: Attendance) {
  pendingBusy.value = a.id
  error.value = ''
  try {
    await confirmAttendance(a.session_id, a.member_id)
    await loadPending()
  } catch {
    error.value = 'Bestätigung fehlgeschlagen.'
  } finally {
    pendingBusy.value = null
  }
}

async function reject(a: Attendance) {
  pendingBusy.value = a.id
  error.value = ''
  try {
    await rejectAttendance(a.session_id, a.member_id)
    await loadPending()
  } catch {
    error.value = 'Ablehnung fehlgeschlagen.'
  } finally {
    pendingBusy.value = null
  }
}

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

onMounted(() => {
  loadMembers()
  loadPending()
})
</script>

<template>
  <div class="page">
    <h1>Check-in</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>
        Ausstehende Bestätigungen
        <span v-if="pending.length" class="badge">{{ pending.length }}</span>
      </template>
      <template #content>
        <p v-if="!pending.length" class="muted">
          Keine Selbst-Check-ins warten auf Bestätigung.
        </p>
        <ul v-else class="pending-list">
          <li v-for="a in pending" :key="a.id" class="pending-item">
            <span class="pending-name">
              <i class="pi pi-user" />
              {{ memberName(a.member_id) }}
            </span>
            <span class="pending-actions">
              <Button
                label="Bestätigen"
                icon="pi pi-check"
                size="small"
                severity="success"
                :loading="pendingBusy === a.id"
                @click="confirm(a)"
              />
              <Button
                label="Ablehnen"
                icon="pi pi-times"
                size="small"
                severity="danger"
                outlined
                :loading="pendingBusy === a.id"
                @click="reject(a)"
              />
            </span>
          </li>
        </ul>
      </template>
    </Card>

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
.muted {
  color: #64748b;
  margin: 0;
}
.badge {
  display: inline-grid;
  place-items: center;
  min-width: 1.4rem;
  height: 1.4rem;
  padding: 0 0.4rem;
  margin-left: 0.5rem;
  border-radius: 999px;
  background: #f59e0b;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
  vertical-align: middle;
}
.pending-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.pending-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.6rem 0.85rem;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
}
.pending-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}
.pending-actions {
  display: flex;
  gap: 0.5rem;
}
</style>
