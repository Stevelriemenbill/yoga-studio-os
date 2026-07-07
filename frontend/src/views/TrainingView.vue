<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import DatePicker from 'primevue/datepicker'
import ProgressBar from 'primevue/progressbar'
import Card from 'primevue/card'

import { listMembers } from '@/api/members'
import {
  getTrainingDashboard,
  listTrainingHours,
  logTrainingHours,
  trainingCsvUrl,
} from '@/api/training'
import type { Member, TrainingDashboard, TrainingHours } from '@/types'

const members = ref<Member[]>([])
const traineeId = ref('')
const dashboard = ref<TrainingDashboard | null>(null)
const hours = ref<TrainingHours[]>([])
const loading = ref(false)
const error = ref('')

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

const csvUrl = computed(() => (traineeId.value ? trainingCsvUrl(traineeId.value) : '#'))

const logForm = ref<{
  area: string
  hours: number
  entry_date: Date | null
  note: string
}>({
  area: '',
  hours: 1,
  entry_date: new Date(),
  note: '',
})

function pctProgress(p: number | null): number {
  return Math.round((p ?? 0) * 100)
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString('de-DE')
}

async function loadMembers() {
  try {
    members.value = await listMembers()
  } catch {
    error.value = 'Mitglieder konnten nicht geladen werden.'
  }
}

async function loadTrainee() {
  if (!traineeId.value) return
  loading.value = true
  error.value = ''
  try {
    dashboard.value = await getTrainingDashboard(traineeId.value)
    hours.value = await listTrainingHours(traineeId.value)
  } catch {
    error.value = 'Ausbildungsdaten konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function submitLog() {
  if (!traineeId.value || !logForm.value.area || !logForm.value.entry_date) return
  error.value = ''
  try {
    await logTrainingHours({
      trainee_id: traineeId.value,
      area: logForm.value.area,
      hours: logForm.value.hours,
      entry_date: logForm.value.entry_date.toISOString().slice(0, 10),
      note: logForm.value.note || undefined,
    })
    logForm.value = { area: '', hours: 1, entry_date: new Date(), note: '' }
    await loadTrainee()
  } catch {
    error.value = 'Stunden konnten nicht gespeichert werden.'
  }
}

onMounted(loadMembers)
</script>

<template>
  <div class="page">
    <h1>Ausbildung</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #content>
        <div class="row">
          <Dropdown
            v-model="traineeId"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Auszubildende:n wählen"
            filter
          />
          <Button label="Laden" :loading="loading" :disabled="!traineeId" @click="loadTrainee" />
          <a v-if="traineeId" :href="csvUrl" download class="csv-link">
            <Button label="CSV exportieren" icon="pi pi-download" text />
          </a>
        </div>
      </template>
    </Card>

    <template v-if="dashboard">
      <h2>Fortschritt: {{ dashboard.total_completed }} / {{ dashboard.total_required }} Stunden</h2>

      <DataTable :value="dashboard.breakdown" responsiveLayout="scroll">
        <Column field="area" header="Bereich" />
        <Column field="completed_hours" header="Absolviert" />
        <Column field="required_hours" header="Erforderlich" />
        <Column header="Fortschritt">
          <template #body="{ data }">
            <ProgressBar :value="pctProgress(data.progress)" />
          </template>
        </Column>
      </DataTable>

      <h2>Erfasste Stunden</h2>
      <DataTable :value="hours" dataKey="id" responsiveLayout="scroll">
        <Column field="area" header="Bereich" />
        <Column field="hours" header="Stunden" />
        <Column header="Datum">
          <template #body="{ data }">{{ fmtDate(data.entry_date) }}</template>
        </Column>
        <Column field="note" header="Notiz" />
      </DataTable>

      <Card class="block">
        <template #title>Stunden erfassen</template>
        <template #content>
          <div class="form">
            <label>Bereich</label>
            <InputText v-model="logForm.area" />
            <label>Stunden</label>
            <InputNumber v-model="logForm.hours" :min="0" :maxFractionDigits="2" />
            <label>Datum</label>
            <DatePicker v-model="logForm.entry_date" dateFormat="dd.mm.yy" />
            <label>Notiz</label>
            <Textarea v-model="logForm.note" rows="2" autoResize />
            <Button label="Speichern" :disabled="!logForm.area" @click="submitLog" />
          </div>
        </template>
      </Card>
    </template>
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
.csv-link {
  text-decoration: none;
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
</style>
