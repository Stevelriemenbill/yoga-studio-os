<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Checkbox from 'primevue/checkbox'
import Textarea from 'primevue/textarea'

import {
  listCourses,
  createCourse,
  updateCourse,
  createSession,
  listRooms,
  scheduleRecurring,
  listCourseAttachments,
  uploadCourseAttachment,
  deleteCourseAttachment,
} from '@/api/courses'
import type { Course, CourseAttachment, Room, CourseLevel, TrainingCohort } from '@/types'
import { listCohorts } from '@/api/training'

const { t } = useI18n()

const courses = ref<Course[]>([])
const rooms = ref<Room[]>([])
const loading = ref(false)
const error = ref('')

const levelOptions: { label: string; value: CourseLevel }[] = [
  { label: t('courses.levels.all'), value: 'all' },
  { label: t('courses.levels.beginner'), value: 'beginner' },
  { label: t('courses.levels.intermediate'), value: 'intermediate' },
  { label: t('courses.levels.advanced'), value: 'advanced' },
]

const showCourseDialog = ref(false)
const savingCourse = ref(false)
const editingCourseId = ref<string | null>(null)
const form = ref<{
  name: string
  category: string
  level: CourseLevel
  max_participants: number
  duration_minutes: number
  counts_for_training: boolean
  location: string
  is_online: boolean
  online_url: string
  registration_info: string
}>({
  name: '',
  category: '',
  level: 'all',
  max_participants: 12,
  duration_minutes: 60,
  counts_for_training: false,
  location: '',
  is_online: false,
  online_url: '',
  registration_info: '',
})

// Attachments for the course being edited.
const attachments = ref<CourseAttachment[]>([])
const uploadingFile = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const showSessionDialog = ref(false)
const savingSession = ref(false)
const sessionCourse = ref<Course | null>(null)
const sessionStartsAt = ref<Date | null>(null)
const sessionOverrideLocation = ref(false)
const sessionForm = ref<{
  is_online: boolean
  location: string
  online_url: string
}>({ is_online: false, location: '', online_url: '' })

// --- Recurring series ---
const showSeriesDialog = ref(false)
const savingSeries = ref(false)
const seriesCourse = ref<Course | null>(null)
const weekdayLabels = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const
const series = ref<{
  weekdays: number[]
  time: Date | null
  startDate: Date | null
  endMode: 'date' | 'count'
  endDate: Date | null
  count: number
  intervalWeeks: number
  cohortId: string | null
}>({
  weekdays: [],
  time: null,
  startDate: null,
  endMode: 'date',
  endDate: null,
  count: 8,
  intervalWeeks: 1,
  cohortId: null,
})
const seriesResult = ref<number | null>(null)
const cohorts = ref<TrainingCohort[]>([])

const seriesValid = computed(() => {
  const s = series.value
  if (!s.weekdays.length || !s.time || !s.startDate) return false
  if (s.endMode === 'date') return !!s.endDate
  return s.count >= 1
})

function toggleWeekday(day: number) {
  const list = series.value.weekdays
  const idx = list.indexOf(day)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(day)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    courses.value = await listCourses()
    rooms.value = await listRooms()
    try {
      cohorts.value = await listCohorts()
    } catch {
      cohorts.value = []
    }
  } catch {
    error.value = t('courses.errors.loadCourses')
  } finally {
    loading.value = false
  }
}

function openCourseDialog(course?: Course) {
  attachments.value = []
  if (course) {
    editingCourseId.value = course.id
    form.value = {
      name: course.name,
      category: course.category ?? '',
      level: course.level,
      max_participants: course.max_participants,
      duration_minutes: course.duration_minutes,
      counts_for_training: course.counts_for_training,
      location: course.location ?? '',
      is_online: course.is_online,
      online_url: course.online_url ?? '',
      registration_info: course.registration_info ?? '',
    }
    loadAttachments(course.id)
  } else {
    editingCourseId.value = null
    form.value = {
      name: '',
      category: '',
      level: 'all',
      max_participants: 12,
      duration_minutes: 60,
      counts_for_training: false,
      location: '',
      is_online: false,
      online_url: '',
      registration_info: '',
    }
  }
  showCourseDialog.value = true
}

async function loadAttachments(courseId: string) {
  try {
    attachments.value = await listCourseAttachments(courseId)
  } catch {
    /* non-critical */
  }
}

async function saveCourse() {
  savingCourse.value = true
  error.value = ''
  try {
    const payload = {
      name: form.value.name,
      category: form.value.category || undefined,
      level: form.value.level,
      max_participants: form.value.max_participants,
      duration_minutes: form.value.duration_minutes,
      counts_for_training: form.value.counts_for_training,
      location: form.value.location || null,
      is_online: form.value.is_online,
      online_url: form.value.online_url || null,
      registration_info: form.value.registration_info || null,
    }
    if (editingCourseId.value) {
      await updateCourse(editingCourseId.value, payload)
    } else {
      await createCourse(payload)
    }
    showCourseDialog.value = false
    await load()
  } catch {
    error.value = t('courses.errors.saveCourse')
  } finally {
    savingCourse.value = false
  }
}

function triggerFilePick() {
  fileInput.value?.click()
}

async function onFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file || !editingCourseId.value) return
  uploadingFile.value = true
  error.value = ''
  try {
    const att = await uploadCourseAttachment(editingCourseId.value, file)
    attachments.value.push(att)
  } catch {
    error.value = t('courses.errors.upload')
  } finally {
    uploadingFile.value = false
    input.value = ''
  }
}

async function removeAttachment(att: CourseAttachment) {
  if (!editingCourseId.value) return
  try {
    await deleteCourseAttachment(editingCourseId.value, att.id)
    attachments.value = attachments.value.filter((a) => a.id !== att.id)
  } catch {
    error.value = t('courses.errors.upload')
  }
}

function fileSizeLabel(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
/** Media URLs are served at the API host root (not under /api/v1). */
const mediaHost = apiBase.replace(/\/api\/v1\/?$/, '')
function attachmentUrl(att: CourseAttachment): string {
  return att.url ? `${mediaHost}${att.url}` : '#'
}

function openSessionDialog(course: Course) {
  sessionCourse.value = course
  sessionStartsAt.value = null
  sessionOverrideLocation.value = false
  sessionForm.value = {
    is_online: course.is_online,
    location: course.location ?? '',
    online_url: course.online_url ?? '',
  }
  showSessionDialog.value = true
}

async function saveSession() {
  if (!sessionCourse.value || !sessionStartsAt.value) return
  savingSession.value = true
  error.value = ''
  try {
    const override = sessionOverrideLocation.value
    await createSession(sessionCourse.value.id, {
      course_id: sessionCourse.value.id,
      starts_at: sessionStartsAt.value.toISOString(),
      // Only send overrides when the user chose to override; otherwise
      // leave null so the session inherits the course location.
      is_online: override ? sessionForm.value.is_online : null,
      location: override && !sessionForm.value.is_online
        ? sessionForm.value.location || null
        : null,
      online_url: override && sessionForm.value.is_online
        ? sessionForm.value.online_url || null
        : null,
    })
    showSessionDialog.value = false
    await load()
  } catch {
    error.value = t('courses.errors.saveSession')
  } finally {
    savingSession.value = false
  }
}

function openSeriesDialog(course: Course) {
  seriesCourse.value = course
  seriesResult.value = null
  series.value = {
    weekdays: [],
    time: null,
    startDate: null,
    endMode: 'date',
    endDate: null,
    count: 8,
    intervalWeeks: 1,
    cohortId: null,
  }
  showSeriesDialog.value = true
}

function pad(n: number): string {
  return String(n).padStart(2, '0')
}

/** Local YYYY-MM-DD (avoids UTC shift from toISOString). */
function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Local HH:MM:SS. */
function toTimeStr(d: Date): string {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:00`
}

async function saveSeries() {
  if (!seriesCourse.value || !seriesValid.value) return
  const s = series.value
  savingSeries.value = true
  error.value = ''
  try {
    const created = await scheduleRecurring(seriesCourse.value.id, {
      course_id: seriesCourse.value.id,
      weekdays: [...s.weekdays].sort((a, b) => a - b),
      start_time: toTimeStr(s.time as Date),
      start_date: toDateStr(s.startDate as Date),
      ...(s.endMode === 'date'
        ? { end_date: toDateStr(s.endDate as Date) }
        : { count: s.count }),
      ...(s.intervalWeeks > 1 ? { interval_weeks: s.intervalWeeks } : {}),
      ...(s.cohortId ? { cohort_id: s.cohortId } : {}),
    })
    seriesResult.value = created.length
    await load()
  } catch {
    error.value = t('courses.errors.saveSeries')
  } finally {
    savingSeries.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('courses.title') }}</h1>
      <Button :label="t('courses.newCourse')" icon="pi pi-plus" @click="openCourseDialog()" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">{{ t('courses.loading') }}</p>

    <template v-else>
      <p class="rooms-info">{{ t('courses.availableRooms', { count: rooms.length }) }}</p>
      <DataTable :value="courses" dataKey="id" responsiveLayout="scroll">
      <Column field="name" :header="t('courses.columns.name')" />
      <Column field="category" :header="t('courses.columns.category')" />
      <Column field="level" :header="t('courses.columns.level')" />
      <Column field="max_participants" :header="t('courses.columns.maxParticipants')" />
      <Column :header="t('courses.columns.active')">
        <template #body="{ data }">
          <Tag
            :value="data.is_active ? t('courses.status.active') : t('courses.status.inactive')"
            :severity="data.is_active ? 'success' : 'danger'"
          />
        </template>
      </Column>
      <Column :header="t('courses.columns.training')">
        <template #body="{ data }">
          <Tag
            v-if="data.counts_for_training"
            :value="t('courses.status.trainingRelevant')"
            severity="info"
          />
          <span v-else class="muted">—</span>
        </template>
      </Column>
      <Column :header="t('courses.columns.actions')">
        <template #body="{ data }">
          <Button
            :label="t('courses.actions.edit')"
            icon="pi pi-pencil"
            size="small"
            text
            @click="openCourseDialog(data)"
          />
          <Button
            :label="t('courses.actions.session')"
            icon="pi pi-calendar-plus"
            size="small"
            text
            @click="openSessionDialog(data)"
          />
          <Button
            :label="t('courses.actions.series')"
            icon="pi pi-replay"
            size="small"
            text
            @click="openSeriesDialog(data)"
          />
        </template>
      </Column>
    </DataTable>
    </template>

    <Dialog
      v-model:visible="showCourseDialog"
      :header="editingCourseId ? t('courses.editCourse') : t('courses.newCourse')"
      modal
      :style="{ width: '520px' }"
    >
      <div class="form">
        <label>{{ t('courses.form.name') }}</label>
        <InputText v-model="form.name" />
        <label>{{ t('courses.form.category') }}</label>
        <InputText v-model="form.category" />
        <label>{{ t('courses.form.level') }}</label>
        <Dropdown
          v-model="form.level"
          :options="levelOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>{{ t('courses.form.maxParticipants') }}</label>
        <InputNumber v-model="form.max_participants" :min="1" />
        <label>{{ t('courses.form.duration') }}</label>
        <InputNumber v-model="form.duration_minutes" :min="1" />

        <div class="checkbox-row">
          <Checkbox v-model="form.is_online" inputId="online" binary />
          <label for="online" class="checkbox-label">{{ t('courses.form.isOnline') }}</label>
        </div>
        <template v-if="form.is_online">
          <label>{{ t('courses.form.onlineUrl') }}</label>
          <InputText v-model="form.online_url" placeholder="https://…" />
        </template>
        <template v-else>
          <label>{{ t('courses.form.location') }}</label>
          <InputText v-model="form.location" :placeholder="t('courses.form.locationPlaceholder')" />
        </template>

        <label>{{ t('courses.form.registrationInfo') }}</label>
        <Textarea v-model="form.registration_info" rows="3" autoResize />
        <small class="hint">{{ t('courses.form.registrationInfoHint') }}</small>

        <div class="checkbox-row">
          <Checkbox v-model="form.counts_for_training" inputId="cft" binary />
          <label for="cft" class="checkbox-label">{{ t('courses.form.countsForTraining') }}</label>
        </div>
        <small class="hint">{{ t('courses.form.countsForTrainingHint') }}</small>

        <template v-if="editingCourseId">
          <label>{{ t('courses.form.attachments') }}</label>
          <ul v-if="attachments.length" class="attachments">
            <li v-for="att in attachments" :key="att.id">
              <a :href="attachmentUrl(att)" target="_blank" rel="noopener">{{ att.filename }}</a>
              <span class="att-size">{{ fileSizeLabel(att.size_bytes) }}</span>
              <Button
                icon="pi pi-trash"
                size="small"
                text
                severity="danger"
                @click="removeAttachment(att)"
              />
            </li>
          </ul>
          <p v-else class="hint">{{ t('courses.form.noAttachments') }}</p>
          <input
            ref="fileInput"
            type="file"
            style="display: none"
            @change="onFileSelected"
          />
          <Button
            :label="t('courses.form.uploadFile')"
            icon="pi pi-upload"
            size="small"
            outlined
            :loading="uploadingFile"
            @click="triggerFilePick"
          />
        </template>
        <small v-else class="hint">{{ t('courses.form.attachmentsAfterSave') }}</small>
      </div>
      <template #footer>
        <Button :label="t('courses.actions.cancel')" text @click="showCourseDialog = false" />
        <Button :label="t('courses.actions.save')" :loading="savingCourse" @click="saveCourse" />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showSessionDialog"
      :header="t('courses.newSession')"
      modal
      :style="{ width: '420px' }"
    >
      <div class="form">
        <label>{{ t('courses.form.course') }}: {{ sessionCourse?.name }}</label>
        <label>{{ t('courses.form.startTime') }}</label>
        <DatePicker v-model="sessionStartsAt" showTime hourFormat="24" />

        <div class="checkbox-row">
          <Checkbox v-model="sessionOverrideLocation" inputId="ovr" binary />
          <label for="ovr" class="checkbox-label">{{ t('courses.form.overrideLocation') }}</label>
        </div>
        <template v-if="sessionOverrideLocation">
          <div class="checkbox-row">
            <Checkbox v-model="sessionForm.is_online" inputId="sonline" binary />
            <label for="sonline" class="checkbox-label">{{ t('courses.form.isOnline') }}</label>
          </div>
          <template v-if="sessionForm.is_online">
            <label>{{ t('courses.form.onlineUrl') }}</label>
            <InputText v-model="sessionForm.online_url" placeholder="https://…" />
          </template>
          <template v-else>
            <label>{{ t('courses.form.location') }}</label>
            <InputText v-model="sessionForm.location" :placeholder="t('courses.form.locationPlaceholder')" />
          </template>
        </template>
      </div>
      <template #footer>
        <Button :label="t('courses.actions.cancel')" text @click="showSessionDialog = false" />
        <Button
          :label="t('courses.actions.create')"
          :loading="savingSession"
          :disabled="!sessionStartsAt"
          @click="saveSession"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showSeriesDialog"
      :header="t('courses.series.title')"
      modal
      :style="{ width: '480px' }"
    >
      <div class="form">
        <label>{{ t('courses.form.course') }}: {{ seriesCourse?.name }}</label>

        <label>{{ t('courses.series.weekdays') }}</label>
        <div class="weekdays">
          <button
            v-for="(key, idx) in weekdayLabels"
            :key="key"
            type="button"
            class="weekday"
            :class="{ selected: series.weekdays.includes(idx) }"
            @click="toggleWeekday(idx)"
          >
            {{ t(`courses.weekdays.${key}`) }}
          </button>
        </div>

        <label>{{ t('courses.series.time') }}</label>
        <DatePicker v-model="series.time" timeOnly hourFormat="24" />

        <label>{{ t('courses.series.startDate') }}</label>
        <DatePicker v-model="series.startDate" dateFormat="dd.mm.yy" />

        <label>{{ t('courses.series.end') }}</label>
        <div class="end-mode">
          <label class="radio">
            <input type="radio" value="date" v-model="series.endMode" />
            {{ t('courses.series.endByDate') }}
          </label>
          <label class="radio">
            <input type="radio" value="count" v-model="series.endMode" />
            {{ t('courses.series.endByCount') }}
          </label>
        </div>
        <DatePicker
          v-if="series.endMode === 'date'"
          v-model="series.endDate"
          dateFormat="dd.mm.yy"
        />
        <InputNumber
          v-else
          v-model="series.count"
          :min="1"
          :max="200"
          showButtons
        />

        <label>{{ t('courses.series.intervalWeeks') }}</label>
        <InputNumber
          v-model="series.intervalWeeks"
          :min="1"
          :max="26"
          showButtons
          :suffix="' ' + t('courses.series.weeksSuffix')"
        />
        <small class="hint">{{ t('courses.series.intervalHint') }}</small>

        <label>{{ t('courses.series.cohort') }}</label>
        <Dropdown
          v-model="series.cohortId"
          :options="cohorts"
          optionLabel="name"
          optionValue="id"
          :placeholder="t('courses.series.noCohort')"
          showClear
        />

        <p v-if="seriesResult !== null" class="series-result">
          {{ t('courses.series.created', { count: seriesResult }) }}
        </p>
      </div>
      <template #footer>
        <Button :label="t('courses.actions.cancel')" text @click="showSeriesDialog = false" />
        <Button
          :label="t('courses.series.generate')"
          icon="pi pi-replay"
          :loading="savingSeries"
          :disabled="!seriesValid"
          @click="saveSeries"
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.error {
  color: #dc2626;
}
.rooms-info {
  color: #6b7280;
  font-size: 0.9rem;
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
.hint {
  color: #6b7280;
}
.muted {
  color: #94a3b8;
}
.attachments {
  list-style: none;
  padding: 0;
  margin: 0.2rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.attachments li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.att-size {
  color: #94a3b8;
  font-size: 0.8rem;
  margin-left: auto;
}
.weekdays {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.weekday {
  border: 1px solid #d1d5db;
  background: #fff;
  border-radius: 8px;
  padding: 0.4rem 0.6rem;
  cursor: pointer;
  font-size: 0.85rem;
  min-width: 2.6rem;
}
.weekday.selected {
  background: var(--p-primary-color, #10b981);
  color: var(--p-primary-contrast-color, #fff);
  border-color: transparent;
  font-weight: 600;
}
.end-mode {
  display: flex;
  gap: 1rem;
}
.radio {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 500 !important;
  margin-top: 0 !important;
  cursor: pointer;
}
.series-result {
  color: var(--p-primary-600, #059669);
  font-weight: 600;
  margin-top: 0.6rem;
}
</style>
