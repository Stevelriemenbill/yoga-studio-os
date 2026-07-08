<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import DatePicker from 'primevue/datepicker'
import Dropdown from 'primevue/dropdown'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'

import {
  listPrograms,
  createProgram,
  listCohorts,
  createCohort,
  updateCohort,
  getCohortProgress,
  listEnrollments,
  enrollMember,
  updateEnrollment,
  removeEnrollment,
} from '@/api/training'
import { listMembers } from '@/api/members'
import type {
  CohortProgress,
  CohortStatus,
  EnrollmentStatus,
  Member,
  TrainingCohort,
  TrainingEnrollment,
  TrainingProgram,
} from '@/types'

const { t, locale } = useI18n()

const programs = ref<TrainingProgram[]>([])
const cohorts = ref<TrainingCohort[]>([])
const members = ref<Member[]>([])
const selectedProgramId = ref<string>('')
const loading = ref(false)
const error = ref('')
const info = ref('')

const selectedProgram = computed(() =>
  programs.value.find((p) => p.id === selectedProgramId.value),
)

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

const statusOptions = computed<{ label: string; value: CohortStatus }[]>(() => [
  { label: t('cohorts.status.planned'), value: 'planned' },
  { label: t('cohorts.status.running'), value: 'running' },
  { label: t('cohorts.status.completed'), value: 'completed' },
])

function fmtDate(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(locale.value === 'de' ? 'de-DE' : 'en-US')
}

function cohortStatusSeverity(s: CohortStatus): string {
  if (s === 'running') return 'success'
  if (s === 'completed') return 'secondary'
  return 'info'
}

// --- Loading ---
async function loadPrograms() {
  loading.value = true
  error.value = ''
  try {
    programs.value = await listPrograms()
    if (!selectedProgramId.value && programs.value.length) {
      selectedProgramId.value = programs.value[0].id
    }
    await loadCohorts()
  } catch {
    error.value = t('cohorts.errors.loadFailed')
  } finally {
    loading.value = false
  }
}

async function loadCohorts() {
  if (!selectedProgramId.value) {
    cohorts.value = []
    return
  }
  try {
    cohorts.value = await listCohorts(selectedProgramId.value)
  } catch {
    error.value = t('cohorts.errors.loadFailed')
  }
}

// --- Create program ---
const showProgramDialog = ref(false)
const savingProgram = ref(false)
const programForm = ref({ name: '', description: '', duration_months: 24 })

function openProgramDialog() {
  programForm.value = { name: '', description: '', duration_months: 24 }
  showProgramDialog.value = true
}

async function saveProgram() {
  if (!programForm.value.name.trim()) return
  savingProgram.value = true
  error.value = ''
  try {
    const created = await createProgram({
      name: programForm.value.name.trim(),
      description: programForm.value.description || null,
      duration_months: programForm.value.duration_months,
    })
    showProgramDialog.value = false
    await loadPrograms()
    selectedProgramId.value = created.id
    await loadCohorts()
  } catch {
    error.value = t('cohorts.errors.programSaveFailed')
  } finally {
    savingProgram.value = false
  }
}

// --- Create cohort ---
const showCohortDialog = ref(false)
const savingCohort = ref(false)
const cohortForm = ref<{
  name: string
  start_date: Date | null
  end_date: Date | null
}>({ name: '', start_date: new Date(), end_date: null })

function openCohortDialog() {
  cohortForm.value = { name: '', start_date: new Date(), end_date: null }
  showCohortDialog.value = true
}

function toDateStr(d: Date | null): string | undefined {
  if (!d) return undefined
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function saveCohort() {
  if (!selectedProgramId.value || !cohortForm.value.name.trim() || !cohortForm.value.start_date)
    return
  savingCohort.value = true
  error.value = ''
  try {
    await createCohort({
      program_id: selectedProgramId.value,
      name: cohortForm.value.name.trim(),
      start_date: toDateStr(cohortForm.value.start_date)!,
      end_date: toDateStr(cohortForm.value.end_date) ?? null,
    })
    showCohortDialog.value = false
    await loadCohorts()
  } catch {
    error.value = t('cohorts.errors.cohortSaveFailed')
  } finally {
    savingCohort.value = false
  }
}

async function changeCohortStatus(cohort: TrainingCohort, status: CohortStatus) {
  error.value = ''
  try {
    const updated = await updateCohort(cohort.id, { status })
    cohort.status = updated.status
  } catch {
    error.value = t('cohorts.errors.cohortSaveFailed')
  }
}

// --- Cohort detail (enrollments + progress) ---
const showDetail = ref(false)
const detailCohort = ref<TrainingCohort | null>(null)
const enrollments = ref<TrainingEnrollment[]>([])
const progress = ref<CohortProgress | null>(null)
const detailLoading = ref(false)
const newEnrolleeId = ref<string | null>(null)
const enrolling = ref(false)

const progressByMember = computed(() => {
  const map = new Map<string, number>()
  progress.value?.trainees.forEach((tr) => map.set(tr.member_id, tr.training_hours))
  return map
})

const requiredHours = computed(() => progress.value?.required_hours ?? 0)

function pct(hours: number): number {
  if (requiredHours.value <= 0) return 0
  return Math.min(100, Math.round((hours / requiredHours.value) * 100))
}

async function openDetail(cohort: TrainingCohort) {
  detailCohort.value = cohort
  showDetail.value = true
  newEnrolleeId.value = null
  await loadDetail()
}

async function loadDetail() {
  if (!detailCohort.value) return
  detailLoading.value = true
  error.value = ''
  try {
    const [en, pr] = await Promise.all([
      listEnrollments(detailCohort.value.id),
      getCohortProgress(detailCohort.value.id),
    ])
    enrollments.value = en
    progress.value = pr
  } catch {
    error.value = t('cohorts.errors.detailFailed')
  } finally {
    detailLoading.value = false
  }
}

async function addEnrollment() {
  if (!detailCohort.value || !newEnrolleeId.value) return
  enrolling.value = true
  error.value = ''
  info.value = ''
  try {
    await enrollMember(detailCohort.value.id, { member_id: newEnrolleeId.value })
    newEnrolleeId.value = null
    if (detailCohort.value) detailCohort.value.enrolled_count += 1
    await loadDetail()
  } catch (e: unknown) {
    const status = (e as { response?: { status?: number } })?.response?.status
    error.value =
      status === 409
        ? t('cohorts.errors.alreadyEnrolled')
        : t('cohorts.errors.enrollFailed')
  } finally {
    enrolling.value = false
  }
}

async function changeEnrollmentStatus(en: TrainingEnrollment, status: EnrollmentStatus) {
  try {
    const updated = await updateEnrollment(en.id, status)
    en.status = updated.status
  } catch {
    error.value = t('cohorts.errors.enrollFailed')
  }
}

async function unenroll(en: TrainingEnrollment) {
  if (!window.confirm(t('cohorts.confirmUnenroll', { name: en.member_name ?? '' }))) return
  try {
    await removeEnrollment(en.id)
    if (detailCohort.value && detailCohort.value.enrolled_count > 0)
      detailCohort.value.enrolled_count -= 1
    await loadDetail()
  } catch {
    error.value = t('cohorts.errors.enrollFailed')
  }
}

const enrollmentStatusOptions = computed<
  { label: string; value: EnrollmentStatus }[]
>(() => [
  { label: t('cohorts.enrollStatus.active'), value: 'active' },
  { label: t('cohorts.enrollStatus.paused'), value: 'paused' },
  { label: t('cohorts.enrollStatus.completed'), value: 'completed' },
  { label: t('cohorts.enrollStatus.withdrawn'), value: 'withdrawn' },
])

onMounted(async () => {
  await Promise.all([loadPrograms(), loadMembersList()])
})

async function loadMembersList() {
  try {
    members.value = await listMembers()
  } catch {
    /* non-fatal */
  }
}
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('cohorts.title') }}</h1>
      <Button
        icon="pi pi-plus"
        :label="t('cohorts.newProgram')"
        size="small"
        @click="openProgramDialog"
      />
    </div>
    <p class="subtitle">{{ t('cohorts.subtitle') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="notice">{{ info }}</p>

    <Card v-if="programs.length" class="block">
      <template #content>
        <div class="row">
          <div class="field">
            <label>{{ t('cohorts.program') }}</label>
            <Dropdown
              v-model="selectedProgramId"
              :options="programs"
              optionLabel="name"
              optionValue="id"
              :placeholder="t('cohorts.selectProgram')"
              @change="loadCohorts"
            />
          </div>
          <div v-if="selectedProgram" class="program-meta">
            <span>{{ t('cohorts.duration', { months: selectedProgram.duration_months }) }}</span>
          </div>
          <span class="spacer" />
          <Button
            v-if="selectedProgramId"
            icon="pi pi-plus"
            :label="t('cohorts.newCohort')"
            size="small"
            @click="openCohortDialog"
          />
        </div>
      </template>
    </Card>

    <p v-if="!loading && !programs.length" class="muted">
      {{ t('cohorts.noPrograms') }}
    </p>

    <div v-if="cohorts.length" class="cohort-grid">
      <Card v-for="c in cohorts" :key="c.id" class="cohort-card">
        <template #title>
          <div class="cohort-title">
            <span>{{ c.name }}</span>
            <Tag
              :value="t('cohorts.status.' + c.status)"
              :severity="cohortStatusSeverity(c.status)"
            />
          </div>
        </template>
        <template #content>
          <p class="dates">
            {{ fmtDate(c.start_date) }} – {{ fmtDate(c.end_date) }}
          </p>
          <p class="enrolled">
            <i class="pi pi-users" />
            {{ t('cohorts.enrolledCount', { count: c.enrolled_count }) }}
          </p>
          <div class="card-actions">
            <Button
              icon="pi pi-list"
              :label="t('cohorts.manage')"
              size="small"
              text
              @click="openDetail(c)"
            />
            <Dropdown
              :modelValue="c.status"
              :options="statusOptions"
              optionLabel="label"
              optionValue="value"
              class="status-select"
              @update:modelValue="(v: CohortStatus) => changeCohortStatus(c, v)"
            />
          </div>
        </template>
      </Card>
    </div>
    <p v-else-if="selectedProgramId && !loading" class="muted">
      {{ t('cohorts.noCohorts') }}
    </p>

    <!-- New program -->
    <Dialog
      v-model:visible="showProgramDialog"
      :header="t('cohorts.newProgram')"
      modal
      :style="{ width: '440px' }"
    >
      <div class="form">
        <label>{{ t('cohorts.form.name') }}</label>
        <InputText v-model="programForm.name" :placeholder="t('cohorts.form.programNamePh')" />
        <label>{{ t('cohorts.form.durationMonths') }}</label>
        <InputNumber v-model="programForm.duration_months" :min="1" showButtons />
        <label>{{ t('cohorts.form.description') }}</label>
        <Textarea v-model="programForm.description" rows="2" autoResize />
      </div>
      <template #footer>
        <Button :label="t('cohorts.form.cancel')" text @click="showProgramDialog = false" />
        <Button
          :label="t('cohorts.form.save')"
          :loading="savingProgram"
          :disabled="!programForm.name.trim()"
          @click="saveProgram"
        />
      </template>
    </Dialog>

    <!-- New cohort -->
    <Dialog
      v-model:visible="showCohortDialog"
      :header="t('cohorts.newCohort')"
      modal
      :style="{ width: '440px' }"
    >
      <div class="form">
        <label>{{ t('cohorts.form.name') }}</label>
        <InputText v-model="cohortForm.name" :placeholder="t('cohorts.form.cohortNamePh')" />
        <label>{{ t('cohorts.form.startDate') }}</label>
        <DatePicker v-model="cohortForm.start_date" dateFormat="dd.mm.yy" />
        <label>{{ t('cohorts.form.endDate') }}</label>
        <DatePicker v-model="cohortForm.end_date" dateFormat="dd.mm.yy" showButtonBar />
      </div>
      <template #footer>
        <Button :label="t('cohorts.form.cancel')" text @click="showCohortDialog = false" />
        <Button
          :label="t('cohorts.form.save')"
          :loading="savingCohort"
          :disabled="!cohortForm.name.trim()"
          @click="saveCohort"
        />
      </template>
    </Dialog>

    <!-- Cohort detail -->
    <Dialog
      v-model:visible="showDetail"
      :header="detailCohort?.name"
      modal
      :style="{ width: '760px' }"
    >
      <div v-if="detailCohort" class="detail">
        <p class="detail-sub">
          {{ fmtDate(detailCohort.start_date) }} – {{ fmtDate(detailCohort.end_date) }}
          · {{ t('cohorts.requiredHours', { hours: requiredHours }) }}
        </p>

        <div class="enroll-row">
          <Dropdown
            v-model="newEnrolleeId"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            :placeholder="t('cohorts.selectMember')"
            filter
            class="enroll-select"
          />
          <Button
            icon="pi pi-user-plus"
            :label="t('cohorts.enroll')"
            size="small"
            :loading="enrolling"
            :disabled="!newEnrolleeId"
            @click="addEnrollment"
          />
        </div>

        <p v-if="detailLoading">{{ t('cohorts.loading') }}</p>
        <DataTable
          v-else
          :value="enrollments"
          dataKey="id"
          responsiveLayout="scroll"
          class="detail-table"
        >
          <Column :header="t('cohorts.columns.trainee')">
            <template #body="{ data }">{{ data.member_name ?? '—' }}</template>
          </Column>
          <Column :header="t('cohorts.columns.progress')">
            <template #body="{ data }">
              <div class="progress-cell">
                <ProgressBar :value="pct(progressByMember.get(data.member_id) ?? 0)" />
                <small>
                  {{ (progressByMember.get(data.member_id) ?? 0) }} /
                  {{ requiredHours }} {{ t('cohorts.hoursUnit') }}
                </small>
              </div>
            </template>
          </Column>
          <Column :header="t('cohorts.columns.status')">
            <template #body="{ data }">
              <Dropdown
                :modelValue="data.status"
                :options="enrollmentStatusOptions"
                optionLabel="label"
                optionValue="value"
                class="status-select"
                @update:modelValue="(v: EnrollmentStatus) => changeEnrollmentStatus(data, v)"
              />
            </template>
          </Column>
          <Column :header="t('cohorts.columns.actions')">
            <template #body="{ data }">
              <Button
                icon="pi pi-trash"
                size="small"
                text
                severity="danger"
                @click="unenroll(data)"
              />
            </template>
          </Column>
        </DataTable>
        <p v-if="!detailLoading && !enrollments.length" class="muted">
          {{ t('cohorts.noEnrollments') }}
        </p>
      </div>
      <template #footer>
        <Button :label="t('cohorts.form.close')" text @click="showDetail = false" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.subtitle {
  color: #64748b;
  margin-top: -0.5rem;
}
.block {
  margin-bottom: 1.25rem;
}
.row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.field label {
  font-weight: 600;
  font-size: 0.85rem;
}
.program-meta {
  color: #64748b;
  padding-bottom: 0.4rem;
}
.spacer {
  flex: 1;
}
.cohort-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}
.cohort-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  font-size: 1.05rem;
}
.dates {
  color: #64748b;
  margin: 0 0 0.4rem;
}
.enrolled {
  margin: 0 0 0.75rem;
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
.card-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: space-between;
}
.status-select {
  min-width: 9rem;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.form label {
  font-weight: 600;
}
.detail-sub {
  color: #64748b;
  margin-top: 0;
}
.enroll-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1rem;
}
.enroll-select {
  min-width: 18rem;
}
.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 180px;
}
.error {
  color: #dc2626;
}
.notice {
  color: var(--p-primary-700, #047857);
}
.muted {
  color: #94a3b8;
}
</style>
