<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import SelectButton from 'primevue/selectbutton'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Checkbox from 'primevue/checkbox'

import { listSchedule, listCourses, bookSession, myBookings } from '@/api/me'
import { cancelSession, updateSession, updateSeries, cancelSeries } from '@/api/courses'
import { useAuthStore } from '@/stores/auth'
import type { Booking, Course, SessionWithStats } from '@/types'

const { t, locale } = useI18n()
const auth = useAuthStore()

const isMember = computed(
  () => auth.user?.role === 'member' || auth.user?.role === 'trainee',
)

type ViewMode = 'week' | 'month'
const viewMode = ref<ViewMode>('week')
const viewOptions = computed(() => [
  { label: t('calendar.week'), value: 'week' as ViewMode },
  { label: t('calendar.month'), value: 'month' as ViewMode },
])

const sessions = ref<SessionWithStats[]>([])
const courses = ref<Course[]>([])
const bookedSessionIds = ref<Set<string>>(new Set())
const loading = ref(false)
const bookingId = ref<string | null>(null)
const error = ref('')
const info = ref('')

/** Start of the currently displayed period (Monday for week, 1st for month). */
const periodStart = ref<Date>(startOfWeek(new Date()))

function startOfWeek(d: Date): Date {
  const date = new Date(d)
  date.setHours(0, 0, 0, 0)
  const day = (date.getDay() + 6) % 7 // 0 = Monday
  date.setDate(date.getDate() - day)
  return date
}

function startOfMonth(d: Date): Date {
  const date = new Date(d.getFullYear(), d.getMonth(), 1)
  date.setHours(0, 0, 0, 0)
  return date
}

function addDays(d: Date, n: number): Date {
  const date = new Date(d)
  date.setDate(date.getDate() + n)
  return date
}

function addMonths(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth() + n, 1)
}

/** Number of days rendered in the grid. Month view rounds to full weeks. */
const gridStart = computed(() =>
  viewMode.value === 'week'
    ? periodStart.value
    : startOfWeek(startOfMonth(periodStart.value)),
)

const gridDayCount = computed(() => {
  if (viewMode.value === 'week') return 7
  // Weeks needed to cover the whole month, starting from the Monday grid start.
  const monthStart = startOfMonth(periodStart.value)
  const monthEnd = addMonths(monthStart, 1) // exclusive
  const start = gridStart.value
  const diffDays = Math.ceil(
    (monthEnd.getTime() - start.getTime()) / (1000 * 60 * 60 * 24),
  )
  return Math.ceil(diffDays / 7) * 7
})

/** Range fetched from the API (covers the whole visible grid). */
const rangeStart = computed(() => gridStart.value)
const rangeEnd = computed(() => addDays(gridStart.value, gridDayCount.value))

const days = computed(() =>
  Array.from({ length: gridDayCount.value }, (_, i) =>
    addDays(gridStart.value, i),
  ),
)

const dtfLocale = computed(() => (locale.value === 'de' ? 'de-DE' : 'en-US'))

const periodLabel = computed(() => {
  if (viewMode.value === 'month') {
    return startOfMonth(periodStart.value).toLocaleDateString(dtfLocale.value, {
      month: 'long',
      year: 'numeric',
    })
  }
  const opts: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short' }
  const from = periodStart.value.toLocaleDateString(dtfLocale.value, opts)
  const to = addDays(periodStart.value, 6).toLocaleDateString(dtfLocale.value, opts)
  return `${from} – ${to}`
})

function dayLabel(d: Date): string {
  return d.toLocaleDateString(dtfLocale.value, {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
  })
}

function isToday(d: Date): boolean {
  const now = new Date()
  return d.toDateString() === now.toDateString()
}

/** In month view, days outside the current month are dimmed. */
function isOutsideMonth(d: Date): boolean {
  if (viewMode.value !== 'month') return false
  return d.getMonth() !== startOfMonth(periodStart.value).getMonth()
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
        start: rangeStart.value.toISOString(),
        end: rangeEnd.value.toISOString(),
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

function changeView(mode: ViewMode) {
  if (!mode || mode === viewMode.value) return
  viewMode.value = mode
  // Re-anchor the period start to the new mode around the same reference date.
  periodStart.value =
    mode === 'week'
      ? startOfWeek(periodStart.value)
      : startOfMonth(periodStart.value)
  load()
}

function prev() {
  periodStart.value =
    viewMode.value === 'week'
      ? addDays(periodStart.value, -7)
      : addMonths(periodStart.value, -1)
  load()
}

function next() {
  periodStart.value =
    viewMode.value === 'week'
      ? addDays(periodStart.value, 7)
      : addMonths(periodStart.value, 1)
  load()
}

function goToday() {
  periodStart.value =
    viewMode.value === 'week'
      ? startOfWeek(new Date())
      : startOfMonth(new Date())
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

// --- Single session cancel (PrimeVue dialog) ---
const showCancelDialog = ref(false)
const cancelling = ref(false)
const cancelReason = ref('')
const cancelTarget = ref<SessionWithStats | null>(null)

function openCancelDialog(session: SessionWithStats) {
  cancelTarget.value = session
  cancelReason.value = ''
  showCancelDialog.value = true
}

async function confirmCancel() {
  const session = cancelTarget.value
  if (!session) return
  cancelling.value = true
  error.value = ''
  info.value = ''
  try {
    await cancelSession(session.id, cancelReason.value.trim() || undefined)
    sessions.value = sessions.value.filter((s) => s.id !== session.id)
    info.value = t('calendar.cancelSuccess')
    showCancelDialog.value = false
  } catch {
    error.value = t('calendar.cancelError')
  } finally {
    cancelling.value = false
  }
}

// --- Single session edit (PrimeVue dialog) ---
const showEditDialog = ref(false)
const savingSession = ref(false)
const editTarget = ref<SessionWithStats | null>(null)
const editCourseName = ref('')
const editForm = ref<{
  date: Date | null
  capacity: number | null
  overrideLocation: boolean
  is_online: boolean
  location: string
  online_url: string
}>({
  date: null,
  capacity: null,
  overrideLocation: false,
  is_online: false,
  location: '',
  online_url: '',
})

function openEditDialog(s: SessionWithStats) {
  editTarget.value = s
  editCourseName.value = courseName.value(s.course_id)
  editForm.value = {
    date: new Date(s.starts_at),
    capacity: s.capacity,
    overrideLocation: false,
    is_online: !!s.effective_is_online,
    location: s.effective_location ?? '',
    online_url: s.effective_online_url ?? '',
  }
  showEditDialog.value = true
}

async function saveSession() {
  const target = editTarget.value
  if (!target) return
  savingSession.value = true
  error.value = ''
  info.value = ''
  try {
    const f = editForm.value
    const payload: Record<string, unknown> = {}
    if (f.date) payload.starts_at = f.date.toISOString()
    if (f.capacity != null) payload.capacity = f.capacity
    if (f.overrideLocation) {
      payload.is_online = f.is_online
      payload.location = f.is_online ? null : f.location || null
      payload.online_url = f.is_online ? f.online_url || null : null
    }
    await updateSession(target.id, payload)
    showEditDialog.value = false
    info.value = t('calendar.edit.updated')
    await load()
  } catch {
    error.value = t('calendar.edit.updateError')
  } finally {
    savingSession.value = false
  }
}

// --- Series management (staff) ---
const showSeriesDialog = ref(false)
const savingSeries = ref(false)
const seriesId = ref<string | null>(null)
const seriesCourseName = ref('')
const seriesForm = ref<{
  time: Date | null
  capacity: number | null
  overrideLocation: boolean
  is_online: boolean
  location: string
  online_url: string
}>({
  time: null,
  capacity: null,
  overrideLocation: false,
  is_online: false,
  location: '',
  online_url: '',
})

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

function openSeriesDialog(s: SessionWithStats) {
  if (!s.series_id) return
  seriesId.value = s.series_id
  seriesCourseName.value = courseName.value(s.course_id)
  seriesForm.value = {
    time: new Date(s.starts_at),
    capacity: s.capacity,
    overrideLocation: false,
    is_online: !!s.effective_is_online,
    location: s.effective_location ?? '',
    online_url: s.effective_online_url ?? '',
  }
  showSeriesDialog.value = true
}

async function saveSeries() {
  if (!seriesId.value) return
  savingSeries.value = true
  error.value = ''
  info.value = ''
  try {
    const f = seriesForm.value
    const payload: Record<string, unknown> = {}
    if (f.time) {
      payload.start_time = `${pad(f.time.getHours())}:${pad(f.time.getMinutes())}:00`
    }
    if (f.capacity != null) payload.capacity = f.capacity
    if (f.overrideLocation) {
      payload.is_online = f.is_online
      payload.location = f.is_online ? null : f.location || null
      payload.online_url = f.is_online ? f.online_url || null : null
    }
    const res = await updateSeries(seriesId.value, payload)
    showSeriesDialog.value = false
    info.value = t('calendar.series.updated', { count: res.affected })
    await load()
  } catch {
    error.value = t('calendar.series.updateError')
  } finally {
    savingSeries.value = false
  }
}

const showSeriesCancelConfirm = ref(false)
const seriesCancelReason = ref('')

function askCancelSeries() {
  seriesCancelReason.value = ''
  showSeriesCancelConfirm.value = true
}

async function deleteSeries() {
  if (!seriesId.value) return
  savingSeries.value = true
  error.value = ''
  info.value = ''
  try {
    const res = await cancelSeries(
      seriesId.value,
      seriesCancelReason.value.trim() || undefined,
    )
    showSeriesCancelConfirm.value = false
    showSeriesDialog.value = false
    info.value = t('calendar.series.cancelled', { count: res.affected })
    await load()
  } catch {
    error.value = t('calendar.series.cancelError')
  } finally {
    savingSeries.value = false
  }
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
      <div class="controls">
        <SelectButton
          :modelValue="viewMode"
          :options="viewOptions"
          optionLabel="label"
          optionValue="value"
          :allowEmpty="false"
          @update:modelValue="changeView"
        />
        <div class="nav">
          <Button icon="pi pi-chevron-left" text rounded @click="prev" />
          <Button :label="t('calendar.today')" text @click="goToday" />
          <span class="week-label">{{ periodLabel }}</span>
          <Button icon="pi pi-chevron-right" text rounded @click="next" />
        </div>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="info">{{ info }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>

    <div v-else class="grid" :class="`grid--${viewMode}`">
      <div
        v-for="d in days"
        :key="d.toISOString()"
        class="day"
        :class="{ today: isToday(d), 'outside-month': isOutsideMonth(d) }"
      >
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
          <div v-if="s.effective_is_online" class="slot-place online">
            <i class="pi pi-video" /> {{ t('calendar.online') }}
          </div>
          <div v-else-if="s.effective_location" class="slot-place">
            <i class="pi pi-map-marker" /> {{ s.effective_location }}
          </div>

          <!-- Member view: booking controls -->
          <template v-if="isMember">
            <Tag v-if="isBooked(s.id)" severity="success" :value="t('calendar.booked')" />
            <a
              v-if="isBooked(s.id) && s.effective_is_online && s.effective_online_url"
              :href="s.effective_online_url"
              target="_blank"
              rel="noopener"
              class="join-link"
            >
              <i class="pi pi-external-link" /> {{ t('calendar.joinOnline') }}
            </a>
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
            <div class="slot-actions" v-if="!isPast(s)">
              <Button
                class="cancel-btn"
                :label="t('calendar.edit.action')"
                icon="pi pi-pencil"
                size="small"
                text
                @click="openEditDialog(s)"
              />
              <Button
                class="cancel-btn"
                :label="t('calendar.cancel')"
                icon="pi pi-times"
                size="small"
                severity="danger"
                text
                @click="openCancelDialog(s)"
              />
              <Button
                v-if="s.series_id"
                class="cancel-btn"
                :label="t('calendar.series.manage')"
                icon="pi pi-replay"
                size="small"
                text
                @click="openSeriesDialog(s)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit a single session -->
    <Dialog
      v-model:visible="showEditDialog"
      :header="t('calendar.edit.title')"
      modal
      :style="{ width: '440px' }"
    >
      <div class="form">
        <p class="series-hint">
          {{ t('calendar.edit.scope', { course: editCourseName }) }}
        </p>

        <label>{{ t('calendar.edit.dateTime') }}</label>
        <DatePicker
          v-model="editForm.date"
          showTime
          hourFormat="24"
          dateFormat="dd.mm.yy"
        />

        <label>{{ t('calendar.series.capacity') }}</label>
        <InputNumber v-model="editForm.capacity" :min="1" showButtons />

        <div class="checkbox-row">
          <Checkbox v-model="editForm.overrideLocation" inputId="eoverride" binary />
          <label for="eoverride" class="checkbox-label">
            {{ t('calendar.series.changeLocation') }}
          </label>
        </div>
        <template v-if="editForm.overrideLocation">
          <div class="checkbox-row">
            <Checkbox v-model="editForm.is_online" inputId="eonline" binary />
            <label for="eonline" class="checkbox-label">{{ t('calendar.series.isOnline') }}</label>
          </div>
          <template v-if="editForm.is_online">
            <label>{{ t('calendar.series.onlineUrl') }}</label>
            <InputText v-model="editForm.online_url" placeholder="https://…" />
          </template>
          <template v-else>
            <label>{{ t('calendar.series.location') }}</label>
            <InputText v-model="editForm.location" />
          </template>
        </template>
      </div>
      <template #footer>
        <Button :label="t('calendar.series.close')" text @click="showEditDialog = false" />
        <Button
          :label="t('calendar.series.save')"
          :loading="savingSession"
          @click="saveSession"
        />
      </template>
    </Dialog>

    <!-- Cancel a single session -->
    <Dialog
      v-model:visible="showCancelDialog"
      :header="t('calendar.cancelDialog.title')"
      modal
      :style="{ width: '420px' }"
    >
      <div class="form">
        <p class="series-hint">
          {{ t('calendar.cancelDialog.hint', { course: cancelTarget ? courseName(cancelTarget.course_id) : '' }) }}
        </p>
        <label>{{ t('calendar.cancelDialog.reason') }}</label>
        <InputText v-model="cancelReason" :placeholder="t('calendar.cancelDialog.reasonPlaceholder')" />
      </div>
      <template #footer>
        <Button :label="t('calendar.cancelDialog.keep')" text @click="showCancelDialog = false" />
        <Button
          :label="t('calendar.cancelDialog.confirm')"
          severity="danger"
          :loading="cancelling"
          @click="confirmCancel"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showSeriesDialog"
      :header="t('calendar.series.title')"
      modal
      :style="{ width: '440px' }"
    >
      <div class="form">
        <p class="series-hint">
          {{ t('calendar.series.scope', { course: seriesCourseName }) }}
        </p>

        <label>{{ t('calendar.series.time') }}</label>
        <DatePicker v-model="seriesForm.time" timeOnly hourFormat="24" />

        <label>{{ t('calendar.series.capacity') }}</label>
        <InputNumber v-model="seriesForm.capacity" :min="1" showButtons />

        <div class="checkbox-row">
          <Checkbox v-model="seriesForm.overrideLocation" inputId="soverride" binary />
          <label for="soverride" class="checkbox-label">
            {{ t('calendar.series.changeLocation') }}
          </label>
        </div>
        <template v-if="seriesForm.overrideLocation">
          <div class="checkbox-row">
            <Checkbox v-model="seriesForm.is_online" inputId="sonline" binary />
            <label for="sonline" class="checkbox-label">{{ t('calendar.series.isOnline') }}</label>
          </div>
          <template v-if="seriesForm.is_online">
            <label>{{ t('calendar.series.onlineUrl') }}</label>
            <InputText v-model="seriesForm.online_url" placeholder="https://…" />
          </template>
          <template v-else>
            <label>{{ t('calendar.series.location') }}</label>
            <InputText v-model="seriesForm.location" />
          </template>
        </template>
      </div>
      <template #footer>
        <Button
          :label="t('calendar.series.cancelSeries')"
          icon="pi pi-trash"
          severity="danger"
          text
          :disabled="savingSeries"
          @click="askCancelSeries"
        />
        <span class="footer-spacer" />
        <Button :label="t('calendar.series.close')" text @click="showSeriesDialog = false" />
        <Button
          :label="t('calendar.series.save')"
          :loading="savingSeries"
          @click="saveSeries"
        />
      </template>
    </Dialog>

    <!-- Confirm cancelling the whole series -->
    <Dialog
      v-model:visible="showSeriesCancelConfirm"
      :header="t('calendar.series.cancelSeries')"
      modal
      :style="{ width: '420px' }"
    >
      <div class="form">
        <p class="series-hint">{{ t('calendar.series.cancelConfirm') }}</p>
        <label>{{ t('calendar.cancelDialog.reason') }}</label>
        <InputText v-model="seriesCancelReason" :placeholder="t('calendar.cancelDialog.reasonPlaceholder')" />
      </div>
      <template #footer>
        <Button :label="t('calendar.cancelDialog.keep')" text @click="showSeriesCancelConfirm = false" />
        <Button
          :label="t('calendar.series.cancelSeries')"
          severity="danger"
          :loading="savingSeries"
          @click="deleteSeries"
        />
      </template>
    </Dialog>
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
.controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
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
  color: var(--p-primary-600, #059669);
}
.grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 1rem;
}
.grid--month .day {
  min-height: 5.5rem;
}
.grid--month .slot {
  font-size: 0.8rem;
}
.day.outside-month {
  opacity: 0.5;
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
  border-color: var(--p-primary-500, #10b981);
  background: var(--p-primary-50, #ecfdf5);
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
  border-color: var(--p-primary-500, #10b981);
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
.slot-place {
  font-size: 0.75rem;
  color: #6b7280;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.slot-place.online {
  color: var(--p-primary-600, #059669);
}
.join-link {
  font-size: 0.78rem;
  color: var(--p-primary-600, #059669);
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  text-decoration: none;
}
.join-link:hover {
  text-decoration: underline;
}
.occupancy {
  font-size: 0.78rem;
  color: #6b7280;
}
.waitlist {
  color: #d97706;
}
.cancel-btn {
  margin-top: 0.25rem;
  align-self: flex-start;
  padding: 0;
}
.slot-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.form label {
  font-weight: 600;
  margin-top: 0.4rem;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.6rem;
}
.checkbox-label {
  font-weight: 600;
  margin-top: 0;
}
.series-hint {
  color: #6b7280;
  font-size: 0.88rem;
  margin: 0;
}
.footer-spacer {
  flex: 1;
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
