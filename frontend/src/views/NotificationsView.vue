<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Card from 'primevue/card'

import {
  listNotifications,
  createNotification,
  sendReminders,
  processNotifications,
} from '@/api/notifications'
import { listMembers } from '@/api/members'
import type { AppNotification, NotificationChannel, Member } from '@/types'

const notifications = ref<AppNotification[]>([])
const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')
const message = ref('')

const channelOptions: { label: string; value: NotificationChannel }[] = [
  { label: 'E-Mail', value: 'email' },
  { label: 'Push', value: 'push' },
  { label: 'WhatsApp', value: 'whatsapp' },
]

const memberOptions = computed(() => [
  { label: '— Kein Mitglied —', value: '' },
  ...members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
])

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString('de-DE') : '—'
}
function truncate(text: string, n = 60): string {
  return text.length > n ? text.slice(0, n) + '…' : text
}

// Create
const showDialog = ref(false)
const saving = ref(false)
const form = ref<{
  channel: NotificationChannel
  member_id: string
  subject: string
  body: string
}>({
  channel: 'email',
  member_id: '',
  subject: '',
  body: '',
})

// Reminders
const reminderSessionId = ref('')
const reminderChannel = ref<NotificationChannel>('email')

async function load() {
  loading.value = true
  error.value = ''
  try {
    notifications.value = await listNotifications()
    members.value = await listMembers()
  } catch {
    error.value = 'Nachrichten konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

function openDialog() {
  form.value = { channel: 'email', member_id: '', subject: '', body: '' }
  showDialog.value = true
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    await createNotification({
      channel: form.value.channel,
      member_id: form.value.member_id || undefined,
      subject: form.value.subject || undefined,
      body: form.value.body,
    })
    showDialog.value = false
    await load()
  } catch {
    error.value = 'Nachricht konnte nicht gespeichert werden.'
  } finally {
    saving.value = false
  }
}

async function process() {
  error.value = ''
  message.value = ''
  try {
    const result = await processNotifications()
    message.value = `${result.sent} Nachrichten gesendet.`
    await load()
  } catch {
    error.value = 'Verarbeitung fehlgeschlagen.'
  }
}

async function doSendReminders() {
  if (!reminderSessionId.value) return
  error.value = ''
  message.value = ''
  try {
    const result = await sendReminders({
      session_id: reminderSessionId.value,
      channel: reminderChannel.value,
    })
    message.value = `${result.length} Erinnerungen eingereiht.`
    await load()
  } catch {
    error.value = 'Erinnerungen konnten nicht gesendet werden.'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>Nachrichten</h1>
      <div class="actions">
        <Button label="Warteschlange verarbeiten" icon="pi pi-cog" outlined @click="process" />
        <Button label="Neue Nachricht" icon="pi pi-plus" @click="openDialog" />
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message" class="success">{{ message }}</p>

    <Card class="block">
      <template #title>Erinnerungen senden</template>
      <template #content>
        <div class="row">
          <InputText v-model="reminderSessionId" placeholder="Session-ID" />
          <Dropdown
            v-model="reminderChannel"
            :options="channelOptions"
            optionLabel="label"
            optionValue="value"
          />
          <Button label="Senden" :disabled="!reminderSessionId" @click="doSendReminders" />
        </div>
      </template>
    </Card>

    <p v-if="loading">Wird geladen…</p>
    <DataTable v-else :value="notifications" dataKey="id" responsiveLayout="scroll">
      <Column header="Kanal">
        <template #body="{ data }"><Tag :value="data.channel" /></template>
      </Column>
      <Column field="subject" header="Betreff" />
      <Column header="Inhalt">
        <template #body="{ data }">{{ truncate(data.body) }}</template>
      </Column>
      <Column header="Status">
        <template #body="{ data }"><Tag :value="data.status" /></template>
      </Column>
      <Column header="Geplant für">
        <template #body="{ data }">{{ fmtDateTime(data.scheduled_for) }}</template>
      </Column>
      <Column header="Gesendet am">
        <template #body="{ data }">{{ fmtDateTime(data.sent_at) }}</template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="showDialog" header="Neue Nachricht" modal :style="{ width: '480px' }">
      <div class="form">
        <label>Kanal</label>
        <Dropdown
          v-model="form.channel"
          :options="channelOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>Mitglied (optional)</label>
        <Dropdown
          v-model="form.member_id"
          :options="memberOptions"
          optionLabel="label"
          optionValue="value"
          filter
        />
        <label>Betreff</label>
        <InputText v-model="form.subject" />
        <label>Inhalt</label>
        <Textarea v-model="form.body" rows="4" autoResize />
      </div>
      <template #footer>
        <Button label="Abbrechen" text @click="showDialog = false" />
        <Button label="Speichern" :loading="saving" :disabled="!form.body" @click="save" />
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
.actions {
  display: flex;
  gap: 0.5rem;
}
.error {
  color: #dc2626;
}
.success {
  color: #16a34a;
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
