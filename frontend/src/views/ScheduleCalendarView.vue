<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import { listSchedule, listCourses, bookSession, myBookings } from '@/api/me'
import { useAuthStore } from '@/stores/auth'
import type { Booking, Course, SessionWithStats } from '@/types'

const { t, locale } = useI18n()
const auth = useAuthStore()

const isMember = computed(
  () => auth.user?.role === 'member' || auth.user?.role === 'trainee',
)

const sessions = ref<SessionWithStats[]>([])
const courses = ref<Course[]>([])
const bookedSessionIds = ref<Set<string>>(new Set())
const loading = ref(false)
const bookingId = ref<string | null>(null)
const error = ref('')
const info = ref('')

/** Monday 00:00 of the currently displayed week. */
const weekStart = ref<Date>(startOfWeek(new Date()))

function startOfWeek(d: Date): Date {
  const date = new Date(d)
  date.setHours(0, 0, 0, 0)
  const day = (date.getDay() + 6) % 7 // 0 = Monday
  date.setDate(date.getDate() - day)
  return date
}

function addDays(d: Date, n: number): Date {
  const date = new Date(d)
  date.setDate(date.getDate() + n)
  return date
}

const weekEnd = computed(() => addDays(weekStart.value, 7))

const days = computed(() =>
  Array.from({ length: 7 }, (_, i) => addDays(weekStart.value, i)),
)

const dtfLocale = computed(() => (locale.value === 'de' ? 'de-DE' : 'en-US'))

const weekLabel = computed(() => {
  const opts: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short' }
  const from = weekStart.value.toLocaleDateString(dtfLocale.value, opts)
  const to = addDays(weekStart.value, 6).toLocaleDateString(dtfLocale.value, opts)
  return `${from} – ${to}`
})

function dayLabel(d: Date): string {
  return d.toLocaleDateString(dtfLocale.value, { weekday: 'short', day: '2-digit', month: '2-digit' })
}

function isToday(d: Date): boolean {
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

const courseName = computed(() => {
  const map = new Map(courses.value.map((c) => [c.id, c.name]))
  return (id: string) => map.get(id) ?? '—'
})

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(dtfLocale.value, {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Sessions for a given calendar day, sorted by start time. */
function sessionsForDay(d: Date): SessionWithStats[] {
  return sessions.value
    .filter((s) => new Date(s.starts_at).toDateString() === d.toDateString())
    .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
}

async function load() {
  loading.value = true
  error.value = ''
  info.value = ''
  try {
    const requests: [
      Promise<SessionWithStats[]>,
      Promise<Course[]>,
      Promise<Booking[]> | Promise<[]>,
    ] = [
      listSchedule({
        start: weekStart.value.toISOString(),
        end: weekEnd.value.toISOString(),
      }),
      listCourses(),
      isMember.value ? myBookings() : Promise.resolve([]),
    ]
    const [sched, crs, mine] = await Promise.all(requests)
    sessions.value = sched.filter((s) => s.status === 'scheduled')
    courses.value = crs
    bookedSessionIds.value = new Set(
      (mine as Booking[])
        .filter((b) => b.status === 'booked')
        .map((b) => b.session_id),
    )
  } catch {
    error.value = t('calendar.loadError')
  } finally {
    loading.value = false
  }
}

function prevWeek() {
  weekStart.value = addDays(weekStart.value, -7)
  load()
}

function nextWeek() {
  weekStart.value = addDays(weekStart.value, 7)
  load()
}

function goToday() {
  weekStart.value = startOfWeek(new Date())
  load()
}

async function book(session: SessionWithStats) {
  bookingId.value = session.id
  error.value = ''
  info.value = ''
  try {
    await bookSession(session.id)
    bookedSessionIds.value = new Set([...bookedSessionIds.value, session.id])
    session.available_spots = Math.max(0, session.available_spots - 1)
    session.booked_count += 1
    info.value = t('calendar.bookSuccess')
  } catch {
    error.value = t('calendar.bookError')
  } finally {
    bookingId.value = null
  }
}

function isBooked(id: string): boolean {
  return bookedSessionIds.value.has(id)
}

function capacityOf(s: SessionWithStats): number {
  return s.capacity + s.overbooking_allowance
}

function isPast(s: SessionWithStats): boolean {
  return new Date(s.starts_at).getTime() < Date.now()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('calendar.title') }}</h1>
      <div class="nav">
        <Button icon="pi pi-chevron-left" text rounded @click="prevWeek" />
        <Button :label="t('calendar.today')" text @click="goToday" />
        <span class="week-label">{{ weekLabel }}</span>
        <Button icon="pi pi-chevron-right" text rounded @click="nextWeek" />
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="info">{{ info }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>

    <div v-else class="grid">
      <div v-for="d in days" :key="d.toISOString()" class="day" :class="{ today: isToday(d) }">
        <div class="day-head">{{ dayLabel(d) }}</div>
        <div v-if="sessionsForDay(d).length === 0" class="empty">—</div>
        <div
          v-for="s in sessionsForDay(d)"
          :key="s.id"
          class="slot"
          :class="{ mine: isMember && isBooked(s.id), past: isPast(s) }"
        >
          <div class="slot-time">{{ fmtTime(s.starts_at) }}</div>
          <div class="slot-name">{{ courseName(s.course_id) }}</div>

          <!-- Member view: booking controls -->
          <template v-if="isMember">
            <Tag v-if="isBooked(s.id)" severity="success" :value="t('calendar.booked')" />
            <Tag
              v-else-if="isPast(s)"
              severity="secondary"
              :value="t('calendar.past')"
            />
            <Tag
              v-else-if="s.available_spots <= 0"
              severity="warn"
              :value="t('calendar.full')"
            />
            <Button
              v-else
              :label="t('calendar.book')"
              size="small"
              :loading="bookingId === s.id"
              @click="book(s)"
            />
          </template>

          <!-- Staff view: occupancy -->
          <div v-else class="occupancy">
            {{ t('calendar.occupancy', { booked: s.booked_count, capacity: capacityOf(s) }) }}
            <span v-if="s.waitlist_count > 0" class="waitlist">
              · {{ t('calendar.waitlist', { count: s.waitlist_count }) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1400px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
}
.nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.week-label {
  font-weight: 600;
  min-width: 9rem;
  text-align: center;
}
.error {
  color: #dc2626;
}
.info {
  color: #059669;
}
.grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 1rem;
}
.day {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.5rem;
  min-height: 8rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.day.today {
  border-color: #10b981;
  background: #ecfdf5;
}
.day-head {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
  text-align: center;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #e5e7eb;
}
.empty {
  color: #cbd5e1;
  text-align: center;
  font-size: 0.85rem;
}
.slot {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 0.4rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.slot.mine {
  border-color: #10b981;
}
.slot.past {
  opacity: 0.55;
}
.slot-time {
  font-size: 0.75rem;
  color: #6b7280;
}
.slot-name {
  font-weight: 600;
  font-size: 0.9rem;
}
.occupancy {
  font-size: 0.78rem;
  color: #6b7280;
}
.waitlist {
  color: #d97706;
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .day {
    min-height: auto;
  }
}
</style>
