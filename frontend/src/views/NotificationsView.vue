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

const { t, locale } = useI18n()

const notifications = ref<AppNotification[]>([])
const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')
const message = ref('')

const channelOptions: { label: string; value: NotificationChannel }[] = [
  { label: t('notifications.channels.email'), value: 'email' },
  { label: t('notifications.channels.push'), value: 'push' },
  { label: t('notifications.channels.whatsapp'), value: 'whatsapp' },
]

const memberOptions = computed(() => [
  { label: t('notifications.noMember'), value: '' },
  ...members.value.map((m) => ({
    label: `${m.first_name} ${m.last_name}`,
    value: m.id,
  })),
])

function fmtDateTime(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US') : '—'
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
    error.value = t('notifications.errors.loadFailed')
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
    error.value = t('notifications.errors.saveFailed')
  } finally {
    saving.value = false
  }
}

async function process() {
  error.value = ''
  message.value = ''
  try {
    const result = await processNotifications()
    message.value = t('notifications.messages.sent', { count: result.sent })
    await load()
  } catch {
    error.value = t('notifications.errors.processFailed')
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
    message.value = t('notifications.messages.remindersQueued', { count: result.length })
    await load()
  } catch {
    error.value = t('notifications.errors.remindersFailed')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('notifications.title') }}</h1>
      <div class="actions">
        <Button :label="t('notifications.processQueue')" icon="pi pi-cog" outlined @click="process" />
        <Button :label="t('notifications.newMessage')" icon="pi pi-plus" @click="openDialog" />
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message" class="success">{{ message }}</p>

    <Card class="block">
      <template #title>{{ t('notifications.reminders.title') }}</template>
      <template #content>
        <div class="row">
          <InputText v-model="reminderSessionId" :placeholder="t('notifications.reminders.sessionIdPlaceholder')" />
          <Dropdown
            v-model="reminderChannel"
            :options="channelOptions"
            optionLabel="label"
            optionValue="value"
          />
          <Button :label="t('notifications.reminders.send')" :disabled="!reminderSessionId" @click="doSendReminders" />
        </div>
      </template>
    </Card>

    <p v-if="loading">{{ t('notifications.loading') }}</p>
    <DataTable v-else :value="notifications" dataKey="id" responsiveLayout="scroll">
      <Column :header="t('notifications.columns.channel')">
        <template #body="{ data }"><Tag :value="data.channel" /></template>
      </Column>
      <Column field="subject" :header="t('notifications.columns.subject')" />
      <Column :header="t('notifications.columns.content')">
        <template #body="{ data }">{{ truncate(data.body) }}</template>
      </Column>
      <Column :header="t('notifications.columns.status')">
        <template #body="{ data }"><Tag :value="data.status" /></template>
      </Column>
      <Column :header="t('notifications.columns.scheduledFor')">
        <template #body="{ data }">{{ fmtDateTime(data.scheduled_for) }}</template>
      </Column>
      <Column :header="t('notifications.columns.sentAt')">
        <template #body="{ data }">{{ fmtDateTime(data.sent_at) }}</template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="showDialog" :header="t('notifications.newMessage')" modal :style="{ width: '480px' }">
      <div class="form">
        <label>{{ t('notifications.form.channel') }}</label>
        <Dropdown
          v-model="form.channel"
          :options="channelOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>{{ t('notifications.form.member') }}</label>
        <Dropdown
          v-model="form.member_id"
          :options="memberOptions"
          optionLabel="label"
          optionValue="value"
          filter
        />
        <label>{{ t('notifications.form.subject') }}</label>
        <InputText v-model="form.subject" />
        <label>{{ t('notifications.form.content') }}</label>
        <Textarea v-model="form.body" rows="4" autoResize />
      </div>
      <template #footer>
        <Button :label="t('notifications.form.cancel')" text @click="showDialog = false" />
        <Button :label="t('notifications.form.save')" :loading="saving" :disabled="!form.body" @click="save" />
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
