<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

import { listCourses, createCourse, createSession, listRooms } from '@/api/courses'
import type { Course, Room, CourseLevel } from '@/types'

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
const form = ref<{
  name: string
  category: string
  level: CourseLevel
  max_participants: number
  duration_minutes: number
}>({
  name: '',
  category: '',
  level: 'all',
  max_participants: 12,
  duration_minutes: 60,
})

const showSessionDialog = ref(false)
const savingSession = ref(false)
const sessionCourse = ref<Course | null>(null)
const sessionStartsAt = ref<Date | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    courses.value = await listCourses()
    rooms.value = await listRooms()
  } catch {
    error.value = t('courses.errors.loadCourses')
  } finally {
    loading.value = false
  }
}

function openCourseDialog() {
  form.value = {
    name: '',
    category: '',
    level: 'all',
    max_participants: 12,
    duration_minutes: 60,
  }
  showCourseDialog.value = true
}

async function saveCourse() {
  savingCourse.value = true
  error.value = ''
  try {
    await createCourse({
      name: form.value.name,
      category: form.value.category || undefined,
      level: form.value.level,
      max_participants: form.value.max_participants,
      duration_minutes: form.value.duration_minutes,
    })
    showCourseDialog.value = false
    await load()
  } catch {
    error.value = t('courses.errors.saveCourse')
  } finally {
    savingCourse.value = false
  }
}

function openSessionDialog(course: Course) {
  sessionCourse.value = course
  sessionStartsAt.value = null
  showSessionDialog.value = true
}

async function saveSession() {
  if (!sessionCourse.value || !sessionStartsAt.value) return
  savingSession.value = true
  error.value = ''
  try {
    await createSession(sessionCourse.value.id, {
      course_id: sessionCourse.value.id,
      starts_at: sessionStartsAt.value.toISOString(),
    })
    showSessionDialog.value = false
    await load()
  } catch {
    error.value = t('courses.errors.saveSession')
  } finally {
    savingSession.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('courses.title') }}</h1>
      <Button :label="t('courses.newCourse')" icon="pi pi-plus" @click="openCourseDialog" />
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
      <Column :header="t('courses.columns.actions')">
        <template #body="{ data }">
          <Button
            :label="t('courses.actions.session')"
            icon="pi pi-calendar-plus"
            size="small"
            text
            @click="openSessionDialog(data)"
          />
        </template>
      </Column>
    </DataTable>
    </template>

    <Dialog v-model:visible="showCourseDialog" :header="t('courses.newCourse')" modal :style="{ width: '460px' }">
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
</style>
