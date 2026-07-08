<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'

import { listSchedule, listCourses, bookSession, myBookings } from '@/api/me'
import { listCourseAttachments } from '@/api/courses'
import type { Booking, Course, CourseAttachment, SessionWithStats } from '@/types'

const { t, locale } = useI18n()

const sessions = ref<SessionWithStats[]>([])
const courses = ref<Course[]>([])
const bookedSessionIds = ref<Set<string>>(new Set())
const loading = ref(false)
const bookingId = ref<string | null>(null)
const error = ref('')
const info = ref('')

// Course info dialog
const showInfoDialog = ref(false)
const infoCourse = ref<Course | null>(null)
const infoAttachments = ref<CourseAttachment[]>([])

const apiBase = import.meta.env.VITE_API_BASE_URL ?? ''
const mediaHost = apiBase.replace(/\/api\/v1\/?$/, '')
function attachmentUrl(att: CourseAttachment): string {
  return att.url ? `${mediaHost}${att.url}` : '#'
}

const courseById = computed(() => new Map(courses.value.map((c) => [c.id, c])))

function hasInfo(courseId: string): boolean {
  const c = courseById.value.get(courseId)
  return !!c && !!c.registration_info
}

async function openInfo(courseId: string) {
  const c = courseById.value.get(courseId) ?? null
  infoCourse.value = c
  infoAttachments.value = []
  showInfoDialog.value = true
  if (c) {
    try {
      infoAttachments.value = await listCourseAttachments(c.id)
    } catch {
      /* attachments are optional */
    }
  }
}

const courseName = computed(() => {
  const map = new Map(courses.value.map((c) => [c.id, c.name]))
  return (id: string) => map.get(id) ?? '—'
})

function fmtWhen(iso: string): string {
  return new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const start = new Date()
    const end = new Date()
    end.setDate(end.getDate() + 30)
    const [sched, crs, mine] = await Promise.all([
      listSchedule({ start: start.toISOString(), end: end.toISOString() }),
      listCourses(),
      myBookings(),
    ])
    sessions.value = sched.filter((s) => s.status === 'scheduled')
    courses.value = crs
    bookedSessionIds.value = new Set(
      mine.filter((b: Booking) => b.status === 'booked').map((b) => b.session_id),
    )
  } catch {
    error.value = t('myArea.loadError')
  } finally {
    loading.value = false
  }
}

async function book(session: SessionWithStats) {
  bookingId.value = session.id
  error.value = ''
  info.value = ''
  try {
    await bookSession(session.id)
    bookedSessionIds.value = new Set([...bookedSessionIds.value, session.id])
    info.value = t('myArea.bookSuccess')
  } catch {
    error.value = t('myArea.bookError')
  } finally {
    bookingId.value = null
  }
}

function isBooked(id: string): boolean {
  return bookedSessionIds.value.has(id)
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('myArea.scheduleTitle') }}</h1>
    <p class="lead">{{ t('myArea.scheduleLead') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="info">{{ info }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>
    <p v-else-if="sessions.length === 0" class="muted">{{ t('myArea.noSessions') }}</p>

    <DataTable v-else :value="sessions" dataKey="id" responsiveLayout="scroll">
      <Column :header="t('myArea.course')">
        <template #body="{ data }">
          <span>{{ courseName(data.course_id) }}</span>
          <Button
            v-if="hasInfo(data.course_id)"
            icon="pi pi-info-circle"
            text
            rounded
            size="small"
            :aria-label="t('myArea.courseInfo')"
            @click="openInfo(data.course_id)"
          />
        </template>
      </Column>
      <Column :header="t('myArea.when')">
        <template #body="{ data }">{{ fmtWhen(data.starts_at) }}</template>
      </Column>
      <Column :header="t('myArea.place')">
        <template #body="{ data }">
          <span v-if="data.effective_is_online" class="online">
            <i class="pi pi-video" /> {{ t('myArea.online') }}
          </span>
          <span v-else-if="data.effective_location">{{ data.effective_location }}</span>
          <span v-else class="muted">—</span>
        </template>
      </Column>
      <Column :header="t('myArea.spots')">
        <template #body="{ data }">{{ data.available_spots }}</template>
      </Column>
      <Column :header="t('myArea.action')">
        <template #body="{ data }">
          <Tag v-if="isBooked(data.id)" severity="success" :value="t('myArea.booked')" />
          <Tag
            v-else-if="data.available_spots <= 0"
            severity="warn"
            :value="t('myArea.full')"
          />
          <Button
            v-else
            :label="t('myArea.book')"
            size="small"
            :loading="bookingId === data.id"
            @click="book(data)"
          />
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="showInfoDialog"
      :header="infoCourse?.name ?? t('myArea.courseInfo')"
      modal
      :style="{ width: '460px' }"
    >
      <p v-if="infoCourse?.registration_info" class="reg-info">
        {{ infoCourse.registration_info }}
      </p>
      <template v-if="infoAttachments.length">
        <h4>{{ t('myArea.attachments') }}</h4>
        <ul class="attachments">
          <li v-for="att in infoAttachments" :key="att.id">
            <a :href="attachmentUrl(att)" target="_blank" rel="noopener">
              <i class="pi pi-file" /> {{ att.filename }}
            </a>
          </li>
        </ul>
      </template>
    </Dialog>
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
.online {
  color: var(--p-primary-600, #059669);
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}
.reg-info {
  white-space: pre-wrap;
  line-height: 1.5;
}
.attachments {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.attachments a {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--p-primary-600, #059669);
  text-decoration: none;
}
.attachments a:hover {
  text-decoration: underline;
}
</style>
