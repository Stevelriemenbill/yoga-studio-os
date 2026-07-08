<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import { myBookings, cancelMyBooking, listSchedule, listCourses } from '@/api/me'
import type { Booking, BookingStatus, Course, SessionWithStats } from '@/types'

const { t, locale } = useI18n()

const bookings = ref<Booking[]>([])
const sessions = ref<Map<string, SessionWithStats>>(new Map())
const courses = ref<Course[]>([])
const loading = ref(false)
const cancellingId = ref<string | null>(null)
const error = ref('')
const info = ref('')

const courseName = computed(() => {
  const map = new Map(courses.value.map((c) => [c.id, c.name]))
  return (courseId: string | undefined) => (courseId ? map.get(courseId) ?? '—' : '—')
})

const statusLabel: Record<BookingStatus, string> = {
  booked: 'myArea.statusBooked',
  cancelled: 'myArea.statusCancelled',
  attended: 'myArea.statusAttended',
  no_show: 'myArea.statusNoShow',
}

const statusSeverity: Record<BookingStatus, string> = {
  booked: 'info',
  cancelled: 'secondary',
  attended: 'success',
  no_show: 'warn',
}

function labelFor(status: BookingStatus): string {
  return t(statusLabel[status])
}

function severityFor(status: BookingStatus): string {
  return statusSeverity[status]
}

function sessionWhen(sessionId: string): string {
  const s = sessions.value.get(sessionId)
  if (!s) return '—'
  return new Date(s.starts_at).toLocaleString(
    locale.value === 'de' ? 'de-DE' : 'en-US',
    { weekday: 'short', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' },
  )
}

function sessionCourse(sessionId: string): string {
  return courseName.value(sessions.value.get(sessionId)?.course_id)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [mine, sched, crs] = await Promise.all([
      myBookings(),
      listSchedule(),
      listCourses(),
    ])
    bookings.value = mine
    sessions.value = new Map(sched.map((s) => [s.id, s]))
    courses.value = crs
  } catch {
    error.value = t('myArea.loadError')
  } finally {
    loading.value = false
  }
}

async function cancel(booking: Booking) {
  cancellingId.value = booking.id
  error.value = ''
  info.value = ''
  try {
    const updated = await cancelMyBooking(booking.id)
    const idx = bookings.value.findIndex((b) => b.id === booking.id)
    if (idx !== -1) bookings.value[idx] = updated
    info.value = t('myArea.cancelSuccess')
  } catch {
    error.value = t('myArea.cancelError')
  } finally {
    cancellingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('myArea.bookingsTitle') }}</h1>
    <p class="lead">{{ t('myArea.bookingsLead') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="info">{{ info }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>
    <p v-else-if="bookings.length === 0" class="muted">{{ t('myArea.noBookings') }}</p>

    <DataTable v-else :value="bookings" dataKey="id" responsiveLayout="scroll">
      <Column :header="t('myArea.course')">
        <template #body="{ data }">{{ sessionCourse(data.session_id) }}</template>
      </Column>
      <Column :header="t('myArea.when')">
        <template #body="{ data }">{{ sessionWhen(data.session_id) }}</template>
      </Column>
      <Column :header="t('myArea.status')">
        <template #body="{ data }">
          <Tag :severity="severityFor(data.status)" :value="labelFor(data.status)" />
        </template>
      </Column>
      <Column :header="t('myArea.action')">
        <template #body="{ data }">
          <Button
            v-if="data.status === 'booked'"
            :label="t('myArea.cancel')"
            severity="danger"
            text
            size="small"
            :loading="cancellingId === data.id"
            @click="cancel(data)"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
}
.lead {
  color: #6b7280;
  margin-bottom: 1.25rem;
}
.error {
  color: #dc2626;
}
.info {
  color: var(--p-primary-600, #059669);
}
.muted {
  color: #6b7280;
}
</style>
