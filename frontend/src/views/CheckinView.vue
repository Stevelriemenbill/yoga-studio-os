<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import QrScanner from 'qr-scanner'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import Card from 'primevue/card'

import { listMembers } from '@/api/members'
import { listCourses, listSessions } from '@/api/courses'
import {
  checkInManual,
  checkInQr,
  getMemberPass,
  listPendingAttendance,
  confirmAttendance,
  rejectAttendance,
} from '@/api/training'
import type {
  Member,
  MemberPass,
  CheckIn,
  Attendance,
  Course,
  SessionWithStats,
} from '@/types'

const { t, locale } = useI18n()

const members = ref<Member[]>([])
const courses = ref<Course[]>([])
const sessions = ref<SessionWithStats[]>([])
const error = ref('')

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

const courseName = computed(() => {
  const map = new Map(courses.value.map((c) => [c.id, c.name]))
  return (id: string) => map.get(id) ?? '—'
})

const sessionOptions = computed(() =>
  [...sessions.value]
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
    .map((s) => ({
      label: `${courseName.value(s.course_id)} · ${fmtDateTime(s.starts_at)} (${s.booked_count}/${s.capacity})`,
      value: s.id,
    })),
)

/** Session used for QR check-ins (required by the backend). */
const activeSessionId = ref('')

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
const manualResult = ref<CheckIn | null>(null)

// Pass
const passMemberId = ref('')
const pass = ref<MemberPass | null>(null)

// QR check-in (camera scanner)
const videoEl = ref<HTMLVideoElement | null>(null)
let scanner: QrScanner | null = null
const scanning = ref(false)
const hasCamera = ref(true)
const qrResult = ref<CheckIn | null>(null)
const qrBusy = ref(false)
// Guard against duplicate submits while a scan is in flight.
let lastScanned = ''

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US')
}

async function loadInitial() {
  try {
    const start = new Date()
    start.setHours(start.getHours() - 2)
    const end = new Date()
    end.setDate(end.getDate() + 14)
    const [mem, crs, sess] = await Promise.all([
      listMembers(),
      listCourses(),
      listSessions({ start: start.toISOString(), end: end.toISOString() }),
    ])
    members.value = mem
    courses.value = crs
    sessions.value = sess
  } catch {
    error.value = t('checkin.errors.loadMembers')
  }
}

async function doManual() {
  if (!manualMemberId.value || !activeSessionId.value) return
  error.value = ''
  try {
    manualResult.value = await checkInManual({
      member_id: manualMemberId.value,
      session_id: activeSessionId.value,
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

async function submitToken(token: string) {
  if (!activeSessionId.value) {
    error.value = t('checkin.errors.noSession')
    return
  }
  qrBusy.value = true
  error.value = ''
  try {
    qrResult.value = await checkInQr({
      token,
      session_id: activeSessionId.value,
    })
    await loadPending()
  } catch {
    error.value = t('checkin.errors.qr')
  } finally {
    qrBusy.value = false
  }
}

async function onScan(result: QrScanner.ScanResult) {
  const data = result?.data ?? ''
  if (!data || data === lastScanned || qrBusy.value) return
  lastScanned = data
  await submitToken(data)
  // Allow re-scanning the same code after a short cooldown.
  setTimeout(() => {
    lastScanned = ''
  }, 3000)
}

async function startScanner() {
  if (!videoEl.value || scanner) return
  if (!activeSessionId.value) {
    error.value = t('checkin.errors.noSession')
    return
  }
  try {
    scanner = new QrScanner(videoEl.value, onScan, {
      returnDetailedScanResult: true,
      highlightScanRegion: true,
      highlightCodeOutline: true,
      preferredCamera: 'environment',
      maxScansPerSecond: 4,
    })
    await scanner.start()
    scanning.value = true
  } catch {
    hasCamera.value = false
    scanner?.destroy()
    scanner = null
    error.value = t('checkin.errors.camera')
  }
}

function stopScanner() {
  scanner?.stop()
  scanning.value = false
}

onMounted(async () => {
  loadInitial()
  loadPending()
  hasCamera.value = await QrScanner.hasCamera().catch(() => false)
})

onBeforeUnmount(() => {
  scanner?.destroy()
  scanner = null
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
      <template #title>{{ t('checkin.sessionTitle') }}</template>
      <template #content>
        <div class="form">
          <label>{{ t('checkin.session') }}</label>
          <Dropdown
            v-model="activeSessionId"
            :options="sessionOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('checkin.selectSession')"
            filter
          />
          <p class="muted">{{ t('checkin.sessionHint') }}</p>
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>{{ t('checkin.qrCheckinTitle') }}</template>
      <template #content>
        <div class="form">
          <p v-if="!hasCamera" class="muted">{{ t('checkin.noCamera') }}</p>
          <div class="scanner">
            <video ref="videoEl" class="scanner-video" />
          </div>
          <div class="scanner-actions">
            <Button
              v-if="!scanning"
              :label="t('checkin.startScan')"
              icon="pi pi-camera"
              :disabled="!hasCamera || !activeSessionId"
              @click="startScanner"
            />
            <Button
              v-else
              :label="t('checkin.stopScan')"
              icon="pi pi-stop"
              severity="secondary"
              outlined
              @click="stopScanner"
            />
          </div>
          <p v-if="qrBusy" class="muted">{{ t('checkin.checking') }}</p>
          <p v-if="qrResult" class="success">
            {{ t('checkin.checkedInAt', { time: fmtDateTime(qrResult.checked_in_at) }) }}
          </p>
        </div>
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
          <Button
            :label="t('checkin.checkIn')"
            :disabled="!manualMemberId || !activeSessionId"
            @click="doManual"
          />
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
.scanner {
  width: 100%;
  max-width: 360px;
  aspect-ratio: 1;
  background: #0f172a;
  border-radius: 12px;
  overflow: hidden;
}
.scanner-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.scanner-actions {
  display: flex;
  gap: 0.5rem;
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
