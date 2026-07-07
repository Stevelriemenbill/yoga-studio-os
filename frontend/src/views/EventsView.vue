<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
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

const events = ref<StudioEvent[]>([])
const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')

const typeOptions: { label: string; value: EventType }[] = [
  { label: 'Workshop', value: 'workshop' },
  { label: 'Retreat', value: 'retreat' },
  { label: 'Special', value: 'special' },
]

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('de-DE')
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
    error.value = 'Events konnten nicht geladen werden.'
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
    error.value = 'Event konnte nicht gespeichert werden.'
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
    error.value = 'Anmeldungen konnten nicht geladen werden.'
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
    error.value = 'Anmeldung fehlgeschlagen.'
  }
}

async function doPay(reg: EventRegistration) {
  if (!activeEvent.value) return
  error.value = ''
  try {
    await confirmPayment(reg.id, activeEvent.value.deposit_cents)
    await loadRegistrations()
  } catch {
    error.value = 'Zahlung fehlgeschlagen.'
  }
}

async function doCancelReg(reg: EventRegistration) {
  error.value = ''
  try {
    await cancelRegistration(reg.id)
    await loadRegistrations()
  } catch {
    error.value = 'Stornierung fehlgeschlagen.'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>Events</h1>
      <Button label="Neues Event" icon="pi pi-plus" @click="openEventDialog" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">Wird geladen…</p>

    <DataTable v-else :value="events" dataKey="id" responsiveLayout="scroll">
      <Column field="name" header="Name" />
      <Column header="Typ">
        <template #body="{ data }"><Tag :value="data.type" /></template>
      </Column>
      <Column header="Beginn">
        <template #body="{ data }">{{ fmtDateTime(data.starts_at) }}</template>
      </Column>
      <Column field="capacity" header="Kapazität" />
      <Column header="Preis">
        <template #body="{ data }">{{ eur(data.price_cents) }}</template>
      </Column>
      <Column header="Veröffentlicht">
        <template #body="{ data }">
          <Tag
            :value="data.is_published ? 'Ja' : 'Nein'"
            :severity="data.is_published ? 'success' : 'warning'"
          />
        </template>
      </Column>
      <Column header="Aktionen">
        <template #body="{ data }">
          <Button label="Anmeldungen" size="small" text @click="openRegistrations(data)" />
        </template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="showEventDialog" header="Neues Event" modal :style="{ width: '480px' }">
      <div class="form">
        <label>Name</label>
        <InputText v-model="eventForm.name" />
        <label>Typ</label>
        <Dropdown
          v-model="eventForm.type"
          :options="typeOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>Beginn</label>
        <DatePicker v-model="eventForm.starts_at" showTime hourFormat="24" />
        <label>Ende</label>
        <DatePicker v-model="eventForm.ends_at" showTime hourFormat="24" />
        <label>Ort</label>
        <InputText v-model="eventForm.location" />
        <label>Kapazität</label>
        <InputNumber v-model="eventForm.capacity" :min="0" />
        <label>Preis (€)</label>
        <InputNumber v-model="eventForm.price_eur" :min="0" :maxFractionDigits="2" />
        <div class="check">
          <Checkbox v-model="eventForm.requires_deposit" :binary="true" inputId="dep" />
          <label for="dep">Anzahlung erforderlich</label>
        </div>
        <label>Anzahlung (€)</label>
        <InputNumber v-model="eventForm.deposit_eur" :min="0" :maxFractionDigits="2" />
      </div>
      <template #footer>
        <Button label="Abbrechen" text @click="showEventDialog = false" />
        <Button
          label="Speichern"
          :loading="savingEvent"
          :disabled="!eventForm.starts_at || !eventForm.ends_at"
          @click="saveEvent"
        />
      </template>
    </Dialog>

    <Dialog
      v-model:visible="showRegDialog"
      :header="`Anmeldungen: ${activeEvent?.name ?? ''}`"
      modal
      :style="{ width: '640px' }"
    >
      <div class="reg-form">
        <Dropdown
          v-model="regMemberId"
          :options="memberOptions"
          optionLabel="label"
          optionValue="value"
          placeholder="Mitglied wählen"
          filter
        />
        <Button label="Anmelden" :disabled="!regMemberId" @click="doRegister" />
      </div>

      <DataTable :value="registrations" dataKey="id" responsiveLayout="scroll">
        <Column field="member_id" header="Mitglied" />
        <Column header="Status">
          <template #body="{ data }"><Tag :value="data.status" /></template>
        </Column>
        <Column header="Bezahlt">
          <template #body="{ data }">{{ eur(data.amount_paid_cents) }}</template>
        </Column>
        <Column header="Aktionen">
          <template #body="{ data }">
            <Button label="Bezahlen" size="small" text @click="doPay(data)" />
            <Button
              label="Stornieren"
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
