<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
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

const { t, locale } = useI18n()

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
    error.value = t('checkin.errors.loadPending')
  }
}

async function confirm(a: Attendance) {
  pendingBusy.value = a.id
  error.value = ''
  try {
    await confirmAttendance(a.session_id, a.member_id)
    await loadPending()
  } catch {
    error.value = t('checkin.errors.confirm')
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
    error.value = t('checkin.errors.reject')
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
  return new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US')
}

async function loadMembers() {
  try {
    members.value = await listMembers()
  } catch {
    error.value = t('checkin.errors.loadMembers')
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
    error.value = t('checkin.errors.manual')
  }
}

async function loadPass() {
  if (!passMemberId.value) return
  error.value = ''
  try {
    pass.value = await getMemberPass(passMemberId.value)
  } catch {
    error.value = t('checkin.errors.loadPass')
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
    error.value = t('checkin.errors.qr')
  }
}

onMounted(() => {
  loadMembers()
  loadPending()
})
</script>

<template>
  <div class="page">
    <h1>{{ t('checkin.title') }}</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>
        {{ t('checkin.pendingTitle') }}
        <span v-if="pending.length" class="badge">{{ pending.length }}</span>
      </template>
      <template #content>
        <p v-if="!pending.length" class="muted">
          {{ t('checkin.noPending') }}
        </p>
        <ul v-else class="pending-list">
          <li v-for="a in pending" :key="a.id" class="pending-item">
            <span class="pending-name">
              <i class="pi pi-user" />
              {{ memberName(a.member_id) }}
            </span>
            <span class="pending-actions">
              <Button
                :label="t('checkin.actions.confirm')"
                icon="pi pi-check"
                size="small"
                severity="success"
                :loading="pendingBusy === a.id"
                @click="confirm(a)"
              />
              <Button
                :label="t('checkin.actions.reject')"
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
      <template #title>{{ t('checkin.manualTitle') }}</template>
      <template #content>
        <div class="form">
          <label>{{ t('checkin.member') }}</label>
          <Dropdown
            v-model="manualMemberId"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('checkin.selectMember')"
            filter
          />
          <label>{{ t('checkin.sessionIdOptional') }}</label>
          <InputText v-model="manualSessionId" />
          <Button :label="t('checkin.checkIn')" :disabled="!manualMemberId" @click="doManual" />
          <p v-if="manualResult" class="success">
            {{ t('checkin.checkedInAt', { time: fmtDateTime(manualResult.checked_in_at) }) }}
          </p>
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>{{ t('checkin.qrPassTitle') }}</template>
      <template #content>
        <div class="form">
          <label>{{ t('checkin.member') }}</label>
          <Dropdown
            v-model="passMemberId"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('checkin.selectMember')"
            filter
          />
          <Button :label="t('checkin.showPass')" :disabled="!passMemberId" @click="loadPass" />
          <template v-if="pass">
            <p><strong>{{ t('checkin.token') }}:</strong> {{ pass.token }}</p>
            <p><strong>{{ t('checkin.qrPayload') }}:</strong> {{ pass.qr_payload }}</p>
          </template>
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>{{ t('checkin.qrCheckinTitle') }}</template>
      <template #content>
        <div class="form">
          <label>{{ t('checkin.qrPayload') }}</label>
          <Textarea v-model="qrPayload" rows="3" autoResize />
          <label>{{ t('checkin.sessionIdOptional') }}</label>
          <InputText v-model="qrSessionId" />
          <Button :label="t('checkin.checkIn')" :disabled="!qrPayload" @click="doQr" />
          <p v-if="qrResult" class="success">
            {{ t('checkin.checkedInAt', { time: fmtDateTime(qrResult.checked_in_at) }) }}
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
