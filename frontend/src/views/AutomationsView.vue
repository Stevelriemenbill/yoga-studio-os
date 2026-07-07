<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import InputSwitch from 'primevue/inputswitch'

import {
  listAutomations,
  createAutomation,
  updateAutomation,
  runAutomations,
} from '@/api/automations'
import type { AutomationRule, AutomationTrigger, NotificationChannel } from '@/types'

const rules = ref<AutomationRule[]>([])
const loading = ref(false)
const error = ref('')
const message = ref('')

const triggerOptions: { label: string; value: AutomationTrigger }[] = [
  { label: 'Inaktive Tage', value: 'inactive_days' },
  { label: 'Nach Buchung', value: 'after_booking' },
  { label: 'Vor Session', value: 'before_session' },
  { label: 'Nach No-Show', value: 'after_no_show' },
  { label: 'Mitgliedschaft läuft ab', value: 'membership_expiring' },
]

const channelOptions: { label: string; value: NotificationChannel }[] = [
  { label: 'E-Mail', value: 'email' },
  { label: 'Push', value: 'push' },
  { label: 'WhatsApp', value: 'whatsapp' },
]

const showDialog = ref(false)
const saving = ref(false)
const form = ref<{
  name: string
  trigger: AutomationTrigger
  threshold_days: number
  channel: NotificationChannel
  message_template: string
}>({
  name: '',
  trigger: 'inactive_days',
  threshold_days: 7,
  channel: 'email',
  message_template: '',
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    rules.value = await listAutomations()
  } catch {
    error.value = 'Regeln konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

function openDialog() {
  form.value = {
    name: '',
    trigger: 'inactive_days',
    threshold_days: 7,
    channel: 'email',
    message_template: '',
  }
  showDialog.value = true
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    await createAutomation({
      name: form.value.name,
      trigger: form.value.trigger,
      threshold_days: form.value.threshold_days,
      channel: form.value.channel,
      message_template: form.value.message_template,
    })
    showDialog.value = false
    await load()
  } catch {
    error.value = 'Regel konnte nicht gespeichert werden.'
  } finally {
    saving.value = false
  }
}

async function toggleActive(rule: AutomationRule) {
  error.value = ''
  try {
    await updateAutomation(rule.id, { is_active: rule.is_active })
  } catch {
    error.value = 'Status konnte nicht geändert werden.'
    rule.is_active = !rule.is_active
  }
}

async function runNow() {
  error.value = ''
  message.value = ''
  try {
    const result = await runAutomations()
    message.value = `${result.total_enqueued} Nachrichten eingereiht.`
  } catch {
    error.value = 'Ausführung fehlgeschlagen.'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>Automatisierungen</h1>
      <div class="actions">
        <Button label="Jetzt ausführen" icon="pi pi-play" outlined @click="runNow" />
        <Button label="Neue Regel" icon="pi pi-plus" @click="openDialog" />
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message" class="success">{{ message }}</p>
    <p v-if="loading">Wird geladen…</p>

    <DataTable v-else :value="rules" dataKey="id" responsiveLayout="scroll">
      <Column field="name" header="Name" />
      <Column field="trigger" header="Auslöser" />
      <Column field="threshold_days" header="Schwelle (Tage)" />
      <Column header="Kanal">
        <template #body="{ data }"><Tag :value="data.channel" /></template>
      </Column>
      <Column header="Aktiv">
        <template #body="{ data }">
          <InputSwitch v-model="data.is_active" @change="toggleActive(data)" />
        </template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="showDialog" header="Neue Regel" modal :style="{ width: '480px' }">
      <div class="form">
        <label>Name</label>
        <InputText v-model="form.name" />
        <label>Auslöser</label>
        <Dropdown
          v-model="form.trigger"
          :options="triggerOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>Schwelle (Tage)</label>
        <InputNumber v-model="form.threshold_days" :min="0" />
        <label>Kanal</label>
        <Dropdown
          v-model="form.channel"
          :options="channelOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>Nachrichtenvorlage</label>
        <Textarea v-model="form.message_template" rows="4" autoResize />
        <small class="hint">Platzhalter: {first_name}, {last_name}</small>
      </div>
      <template #footer>
        <Button label="Abbrechen" text @click="showDialog = false" />
        <Button label="Speichern" :loading="saving" @click="save" />
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
.form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.form label {
  font-weight: 600;
  margin-top: 0.4rem;
}
.hint {
  color: #6b7280;
}
</style>
