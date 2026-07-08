<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import Checkbox from 'primevue/checkbox'
import Card from 'primevue/card'

import {
  listSessionBookings,
  listWaitlist,
  createBooking,
  cancelBooking,
  acceptOffer,
  declineOffer,
} from '@/api/bookings'
import { listMembers } from '@/api/members'
import { listSessions, listCourses } from '@/api/courses'
import type { Booking, WaitlistEntry, Member, Course, SessionWithStats } from '@/types'

const { t, locale } = useI18n()

const sessionId = ref('')
const members = ref<Member[]>([])
const sessions = ref<SessionWithStats[]>([])
const courses = ref<Course[]>([])
const bookings = ref<Booking[]>([])
const waitlist = ref<WaitlistEntry[]>([])
const loading = ref(false)
const error = ref('')

const bookingForm = ref<{ member_id: string; drop_in: boolean }>({
  member_id: '',
  drop_in: false,
})

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

const memberName = computed(() => {
  const map = new Map(members.value.map((m) => [m.id, `${m.first_name} ${m.last_name}`]))
  return (id: string) => map.get(id) ?? id
})

const sessionOptions = computed(() =>
  [...sessions.value]
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
    .map((s) => ({
      label: `${courseName.value(s.course_id)} · ${fmtDateTime(s.starts_at)} (${s.booked_count}/${s.capacity})`,
      value: s.id,
    })),
)

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US') : '—'
}

async function loadInitial() {
  try {
    const start = new Date()
    start.setDate(start.getDate() - 7)
    const end = new Date()
    end.setDate(end.getDate() + 30)
    const [mem, crs, sess] = await Promise.all([
      listMembers(),
      listCourses(),
      listSessions({ start: start.toISOString(), end: end.toISOString() }),
    ])
    members.value = mem
    courses.value = crs
    sessions.value = sess
  } catch {
    error.value = t('bookings.errors.loadMembers')
  }
}

async function loadSession() {
  if (!sessionId.value) return
  loading.value = true
  error.value = ''
  try {
    bookings.value = await listSessionBookings(sessionId.value)
    waitlist.value = await listWaitlist(sessionId.value)
  } catch {
    error.value = t('bookings.errors.loadBookings')
  } finally {
    loading.value = false
  }
}

async function submitBooking() {
  if (!sessionId.value || !bookingForm.value.member_id) return
  error.value = ''
  try {
    await createBooking({
      session_id: sessionId.value,
      member_id: bookingForm.value.member_id,
      drop_in: bookingForm.value.drop_in,
    })
    bookingForm.value = { member_id: '', drop_in: false }
    await loadSession()
  } catch {
    error.value = t('bookings.errors.booking')
  }
}

async function doCancel(b: Booking) {
  error.value = ''
  try {
    await cancelBooking(b.id)
    await loadSession()
  } catch {
    error.value = t('bookings.errors.cancel')
  }
}

async function doAccept(w: WaitlistEntry) {
  error.value = ''
  try {
    await acceptOffer(w.id)
    await loadSession()
  } catch {
    error.value = t('bookings.errors.accept')
  }
}

async function doDecline(w: WaitlistEntry) {
  error.value = ''
  try {
    await declineOffer(w.id)
    await loadSession()
  } catch {
    error.value = t('bookings.errors.decline')
  }
}

onMounted(loadInitial)
</script>

<template>
  <div class="page">
    <h1>{{ t('bookings.title') }}</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>{{ t('bookings.loadSession') }}</template>
      <template #content>
        <div class="row">
          <Dropdown
            v-model="sessionId"
            :options="sessionOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('bookings.selectSession')"
            filter
            class="session-select"
            @change="loadSession"
          />
          <Button :label="t('bookings.loadBookings')" :loading="loading" @click="loadSession" />
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>{{ t('bookings.newBooking') }}</template>
      <template #content>
        <div class="row">
          <Dropdown
            v-model="bookingForm.member_id"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('bookings.selectMember')"
            filter
          />
          <div class="check">
            <Checkbox v-model="bookingForm.drop_in" :binary="true" inputId="dropin" />
            <label for="dropin">{{ t('bookings.dropIn') }}</label>
          </div>
          <Button
            :label="t('bookings.book')"
            :disabled="!sessionId || !bookingForm.member_id"
            @click="submitBooking"
          />
        </div>
      </template>
    </Card>

    <h2>{{ t('bookings.bookingsHeading') }}</h2>
    <DataTable :value="bookings" dataKey="id" responsiveLayout="scroll">
      <Column :header="t('bookings.columns.member')">
        <template #body="{ data }">{{ memberName(data.member_id) }}</template>
      </Column>
      <Column :header="t('bookings.columns.status')">
        <template #body="{ data }"><Tag :value="data.status" /></template>
      </Column>
      <Column field="source" :header="t('bookings.columns.source')" />
      <Column :header="t('bookings.columns.bookedAt')">
        <template #body="{ data }">{{ fmtDateTime(data.booked_at) }}</template>
      </Column>
      <Column :header="t('bookings.columns.actions')">
        <template #body="{ data }">
          <Button
            :label="t('bookings.actions.cancel')"
            size="small"
            text
            severity="danger"
            @click="doCancel(data)"
          />
        </template>
      </Column>
    </DataTable>

    <h2>{{ t('bookings.waitlistHeading') }}</h2>
    <DataTable :value="waitlist" dataKey="id" responsiveLayout="scroll">
      <Column :header="t('bookings.columns.member')">
        <template #body="{ data }">{{ memberName(data.member_id) }}</template>
      </Column>
      <Column :header="t('bookings.columns.status')">
        <template #body="{ data }"><Tag :value="data.status" /></template>
      </Column>
      <Column field="priority" :header="t('bookings.columns.priority')" />
      <Column :header="t('bookings.columns.joinedAt')">
        <template #body="{ data }">{{ fmtDateTime(data.joined_at) }}</template>
      </Column>
      <Column :header="t('bookings.columns.actions')">
        <template #body="{ data }">
          <Button :label="t('bookings.actions.accept')" size="small" text @click="doAccept(data)" />
          <Button
            :label="t('bookings.actions.decline')"
            size="small"
            text
            severity="danger"
            @click="doDecline(data)"
          />
        </template>
      </Column>
    </DataTable>
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
.block {
  margin-bottom: 1rem;
}
.row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}
.check {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
</style>
