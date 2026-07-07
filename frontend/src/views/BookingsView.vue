<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import Checkbox from 'primevue/checkbox'
import Card from 'primevue/card'

import {
  listSessionBookings,
  listWaitlist,
  createBooking,
  cancelBooking,
  acceptOffer,
  declineOffer,
} from '@/api/bookings'
import { listMembers } from '@/api/members'
import type { Booking, WaitlistEntry, Member } from '@/types'

const sessionId = ref('')
const members = ref<Member[]>([])
const bookings = ref<Booking[]>([])
const waitlist = ref<WaitlistEntry[]>([])
const loading = ref(false)
const error = ref('')

const bookingForm = ref<{ member_id: string; drop_in: boolean }>({
  member_id: '',
  drop_in: false,
})

const memberOptions = computed(() =>
  members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
)

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString('de-DE') : '—'
}

async function loadMembers() {
  try {
    members.value = await listMembers()
  } catch {
    error.value = 'Mitglieder konnten nicht geladen werden.'
  }
}

async function loadSession() {
  if (!sessionId.value) return
  loading.value = true
  error.value = ''
  try {
    bookings.value = await listSessionBookings(sessionId.value)
    waitlist.value = await listWaitlist(sessionId.value)
  } catch {
    error.value = 'Buchungen konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function submitBooking() {
  if (!sessionId.value || !bookingForm.value.member_id) return
  error.value = ''
  try {
    await createBooking({
      session_id: sessionId.value,
      member_id: bookingForm.value.member_id,
      drop_in: bookingForm.value.drop_in,
    })
    bookingForm.value = { member_id: '', drop_in: false }
    await loadSession()
  } catch {
    error.value = 'Buchung fehlgeschlagen.'
  }
}

async function doCancel(b: Booking) {
  error.value = ''
  try {
    await cancelBooking(b.id)
    await loadSession()
  } catch {
    error.value = 'Stornierung fehlgeschlagen.'
  }
}

async function doAccept(w: WaitlistEntry) {
  error.value = ''
  try {
    await acceptOffer(w.id)
    await loadSession()
  } catch {
    error.value = 'Annahme fehlgeschlagen.'
  }
}

async function doDecline(w: WaitlistEntry) {
  error.value = ''
  try {
    await declineOffer(w.id)
    await loadSession()
  } catch {
    error.value = 'Ablehnung fehlgeschlagen.'
  }
}

onMounted(loadMembers)
</script>

<template>
  <div class="page">
    <h1>Buchungen</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>Session laden</template>
      <template #content>
        <div class="row">
          <InputText v-model="sessionId" placeholder="Session-ID" />
          <Button label="Buchungen laden" :loading="loading" @click="loadSession" />
        </div>
      </template>
    </Card>

    <Card class="block">
      <template #title>Neue Buchung</template>
      <template #content>
        <div class="row">
          <Dropdown
            v-model="bookingForm.member_id"
            :options="memberOptions"
            optionLabel="label"
            optionValue="value"
            placeholder="Mitglied wählen"
            filter
          />
          <div class="check">
            <Checkbox v-model="bookingForm.drop_in" :binary="true" inputId="dropin" />
            <label for="dropin">Drop-in</label>
          </div>
          <Button
            label="Buchen"
            :disabled="!sessionId || !bookingForm.member_id"
            @click="submitBooking"
          />
        </div>
      </template>
    </Card>

    <h2>Buchungen</h2>
    <DataTable :value="bookings" dataKey="id" responsiveLayout="scroll">
      <Column field="member_id" header="Mitglied" />
      <Column header="Status">
        <template #body="{ data }"><Tag :value="data.status" /></template>
      </Column>
      <Column field="source" header="Quelle" />
      <Column header="Gebucht am">
        <template #body="{ data }">{{ fmtDateTime(data.booked_at) }}</template>
      </Column>
      <Column header="Aktionen">
        <template #body="{ data }">
          <Button
            label="Stornieren"
            size="small"
            text
            severity="danger"
            @click="doCancel(data)"
          />
        </template>
      </Column>
    </DataTable>

    <h2>Warteliste</h2>
    <DataTable :value="waitlist" dataKey="id" responsiveLayout="scroll">
      <Column field="member_id" header="Mitglied" />
      <Column header="Status">
        <template #body="{ data }"><Tag :value="data.status" /></template>
      </Column>
      <Column field="priority" header="Priorität" />
      <Column header="Beigetreten">
        <template #body="{ data }">{{ fmtDateTime(data.joined_at) }}</template>
      </Column>
      <Column header="Aktionen">
        <template #body="{ data }">
          <Button label="Annehmen" size="small" text @click="doAccept(data)" />
          <Button
            label="Ablehnen"
            size="small"
            text
            severity="danger"
            @click="doDecline(data)"
          />
        </template>
      </Column>
    </DataTable>
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
.check {
  display: flex;
  gap: 0.4rem;
  align-items: center;
}
</style>
