<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
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

import {
  listEvents,
  createEvent,
  listRegistrations,
  registerForEvent,
  confirmPayment,
  cancelRegistration,
} from '@/api/events'
import { listMembers } from '@/api/members'
import type { StudioEvent, EventRegistration, EventType, Member } from '@/types'

const { t, locale } = useI18n()

const events = ref<StudioEvent[]>([])
const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')

const typeOptions: { label: string; value: EventType }[] = [
  { label: t('events.types.workshop'), value: 'workshop' },
  { label: t('events.types.retreat'), value: 'retreat' },
  { label: t('events.types.special'), value: 'special' },
]

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US')
}
function eur(cents: number): string {
  return (cents / 100).toFixed(2) + ' €'
}

// Create event
const showEventDialog = ref(false)
const savingEvent = ref(false)
const eventForm = ref<{
  name: string
  type: EventType
  starts_at: Date | null
  ends_at: Date | null
  location: string
  capacity: number
  price_eur: number
  requires_deposit: boolean
  deposit_eur: number
}>({
  name: '',
  type: 'workshop',
  starts_at: null,
  ends_at: null,
  location: '',
  capacity: 20,
  price_eur: 0,
  requires_deposit: false,
  deposit_eur: 0,
})

// Registrations
const showRegDialog = ref(false)
const activeEvent = ref<StudioEvent | null>(null)
const registrations = ref<EventRegistration[]>([])
const regMemberId = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    events.value = await listEvents()
    members.value = await listMembers()
  } catch {
    error.value = t('events.errors.loadEvents')
  } finally {
    loading.value = false
  }
}

function openEventDialog() {
  eventForm.value = {
    name: '',
    type: 'workshop',
    starts_at: null,
    ends_at: null,
    location: '',
    capacity: 20,
    price_eur: 0,
    requires_deposit: false,
    deposit_eur: 0,
  }
  showEventDialog.value = true
}

async function saveEvent() {
  if (!eventForm.value.starts_at || !eventForm.value.ends_at) return
  savingEvent.value = true
  error.value = ''
  try {
    await createEvent({
      name: eventForm.value.name,
      type: eventForm.value.type,
      starts_at: eventForm.value.starts_at.toISOString(),
      ends_at: eventForm.value.ends_at.toISOString(),
      location: eventForm.value.location || undefined,
      capacity: eventForm.value.capacity,
      price_cents: Math.round(eventForm.value.price_eur * 100),
      requires_deposit: eventForm.value.requires_deposit,
      deposit_cents: Math.round(eventForm.value.deposit_eur * 100),
    })
    showEventDialog.value = false
    await load()
  } catch {
    error.value = t('events.errors.saveEvent')
  } finally {
    savingEvent.value = false
  }
}

async function openRegistrations(ev: StudioEvent) {
  activeEvent.value = ev
  regMemberId.value = ''
  showRegDialog.value = true
  await loadRegistrations()
}

async function loadRegistrations() {
  if (!activeEvent.value) return
  error.value = ''
  try {
    registrations.value = await listRegistrations(activeEvent.value.id)
  } catch {
    error.value = t('events.errors.loadRegistrations')
  }
}

async function doRegister() {
  if (!activeEvent.value || !regMemberId.value) return
  error.value = ''
  try {
    await registerForEvent(activeEvent.value.id, regMemberId.value)
    regMemberId.value = ''
    await loadRegistrations()
  } catch {
    error.value = t('events.errors.register')
  }
}

async function doPay(reg: EventRegistration) {
  if (!activeEvent.value) return
  error.value = ''
  try {
    await confirmPayment(reg.id, activeEvent.value.deposit_cents)
    await loadRegistrations()
  } catch {
    error.value = t('events.errors.payment')
  }
}

async function doCancelReg(reg: EventRegistration) {
  error.value = ''
  try {
    await cancelRegistration(reg.id)
    await loadRegistrations()
  } catch {
    error.value = t('events.errors.cancel')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('events.title') }}</h1>
      <Button :label="t('events.newEvent')" icon="pi pi-plus" @click="openEventDialog" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">{{ t('events.loading') }}</p>

    <DataTable v-else :value="events" dataKey="id" responsiveLayout="scroll">
      <Column field="name" :header="t('events.columns.name')" />
      <Column :header="t('events.columns.type')">
        <template #body="{ data }"><Tag :value="data.type" /></template>
      </Column>
      <Column :header="t('events.columns.start')">
        <template #body="{ data }">{{ fmtDateTime(data.starts_at) }}</template>
      </Column>
      <Column field="capacity" :header="t('events.columns.capacity')" />
      <Column :header="t('events.columns.price')">
        <template #body="{ data }">{{ eur(data.price_cents) }}</template>
      </Column>
      <Column :header="t('events.columns.published')">
        <template #body="{ data }">
          <Tag
            :value="data.is_published ? t('events.status.yes') : t('events.status.no')"
            :severity="data.is_published ? 'success' : 'warning'"
          />
        </template>
      </Column>
      <Column :header="t('events.columns.actions')">
        <template #body="{ data }">
          <Button :label="t('events.actions.registrations')" size="small" text @click="openRegistrations(data)" />
        </template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="showEventDialog" :header="t('events.newEvent')" modal :style="{ width: '480px' }">
      <div class="form">
        <label>{{ t('events.form.name') }}</label>
        <InputText v-model="eventForm.name" />
        <label>{{ t('events.form.type') }}</label>
        <Dropdown
          v-model="eventForm.type"
          :options="typeOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>{{ t('events.form.start') }}</label>
        <DatePicker v-model="eventForm.starts_at" showTime hourFormat="24" />
        <label>{{ t('events.form.end') }}</label>
        <DatePicker v-model="eventForm.ends_at" showTime hourFormat="24" />
        <label>{{ t('events.form.location') }}</label>
        <InputText v-model="eventForm.location" />
        <label>{{ t('events.form.capacity') }}</label>
        <InputNumber v-model="eventForm.capacity" :min="0" />
        <label>{{ t('events.form.price') }}</label>
        <InputNumber v-model="eventForm.price_eur" :min="0" :maxFractionDigits="2" />
        <div class="check">
          <Checkbox v-model="eventForm.requires_deposit" :binary="true" inputId="dep" />
          <label for="dep">{{ t('events.form.requiresDeposit') }}</label>
        </div>
        <label>{{ t('events.form.deposit') }}</label>
        <InputNumber v-model="eventForm.deposit_eur" :min="0" :maxFractionDigits="2" />
      </div>
      <template #footer>
        <Button :label="t('events.actions.cancel')" text @click="showEventDialog = false" />
        <Button
          :label="t('events.actions.save')"
          :loading="savingEvent"
          :disabled="!eventForm.starts_at || !eventForm.ends_at"
          @click="saveEvent"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showRegDialog"
      :header="t('events.registrationsFor', { name: activeEvent?.name ?? '' })"
      modal
      :style="{ width: '640px' }"
    >
      <div class="reg-form">
        <Dropdown
          v-model="regMemberId"
          :options="memberOptions"
          optionLabel="label"
          optionValue="value"
          :placeholder="t('events.selectMember')"
          filter
        />
        <Button :label="t('events.actions.register')" :disabled="!regMemberId" @click="doRegister" />
      </div>

      <DataTable :value="registrations" dataKey="id" responsiveLayout="scroll">
        <Column field="member_id" :header="t('events.columns.member')" />
        <Column :header="t('events.columns.status')">
          <template #body="{ data }"><Tag :value="data.status" /></template>
        </Column>
        <Column :header="t('events.columns.paid')">
          <template #body="{ data }">{{ eur(data.amount_paid_cents) }}</template>
        </Column>
        <Column :header="t('events.columns.actions')">
          <template #body="{ data }">
            <Button :label="t('events.actions.pay')" size="small" text @click="doPay(data)" />
            <Button
              :label="t('events.actions.cancelRegistration')"
              size="small"
              text
              severity="danger"
              @click="doCancelReg(data)"
            />
          </template>
        </Column>
      </DataTable>
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
.form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.form label {
  font-weight: 600;
  margin-top: 0.4rem;
}
.check {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  margin-top: 0.4rem;
}
.reg-form {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-bottom: 1rem;
}
</style>
