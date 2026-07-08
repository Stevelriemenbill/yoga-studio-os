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
import Textarea from 'primevue/textarea'
import InputSwitch from 'primevue/inputswitch'

import {
  listAutomations,
  createAutomation,
  updateAutomation,
  runAutomations,
} from '@/api/automations'
import type { AutomationRule, AutomationTrigger, NotificationChannel } from '@/types'

const { t } = useI18n()

const rules = ref<AutomationRule[]>([])
const loading = ref(false)
const error = ref('')
const message = ref('')

const triggerOptions = (): { label: string; value: AutomationTrigger }[] => [
  { label: t('automations.triggers.inactive_days'), value: 'inactive_days' },
  { label: t('automations.triggers.after_booking'), value: 'after_booking' },
  { label: t('automations.triggers.before_session'), value: 'before_session' },
  { label: t('automations.triggers.after_no_show'), value: 'after_no_show' },
  { label: t('automations.triggers.membership_expiring'), value: 'membership_expiring' },
]

const channelOptions: { label: string; value: NotificationChannel }[] = [
  { label: t('automations.channels.email'), value: 'email' },
  { label: t('automations.channels.push'), value: 'push' },
  { label: t('automations.channels.whatsapp'), value: 'whatsapp' },
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
    error.value = t('automations.errors.loadFailed')
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
    error.value = t('automations.errors.saveFailed')
  } finally {
    saving.value = false
  }
}

async function toggleActive(rule: AutomationRule) {
  error.value = ''
  try {
    await updateAutomation(rule.id, { is_active: rule.is_active })
  } catch {
    error.value = t('automations.errors.toggleFailed')
    rule.is_active = !rule.is_active
  }
}

async function runNow() {
  error.value = ''
  message.value = ''
  try {
    const result = await runAutomations()
    message.value = t('automations.messages.enqueued', { count: result.total_enqueued })
  } catch {
    error.value = t('automations.errors.runFailed')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('automations.title') }}</h1>
      <div class="actions">
        <Button :label="t('automations.runNow')" icon="pi pi-play" outlined @click="runNow" />
        <Button :label="t('automations.newRule')" icon="pi pi-plus" @click="openDialog" />
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message" class="success">{{ message }}</p>
    <p v-if="loading">{{ t('automations.loading') }}</p>

    <DataTable v-else :value="rules" dataKey="id" responsiveLayout="scroll">
      <Column field="name" :header="t('automations.columns.name')" />
      <Column :header="t('automations.columns.trigger')">
        <template #body="{ data }">{{ t(`automations.triggers.${data.trigger}`) }}</template>
      </Column>
      <Column field="threshold_days" :header="t('automations.columns.thresholdDays')" />
      <Column :header="t('automations.columns.channel')">
        <template #body="{ data }"><Tag :value="data.channel" /></template>
      </Column>
      <Column :header="t('automations.columns.active')">
        <template #body="{ data }">
          <InputSwitch v-model="data.is_active" @change="toggleActive(data)" />
        </template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="showDialog" :header="t('automations.newRule')" modal :style="{ width: '480px' }">
      <div class="form">
        <label>{{ t('automations.form.name') }}</label>
        <InputText v-model="form.name" />
        <label>{{ t('automations.form.trigger') }}</label>
        <Dropdown
          v-model="form.trigger"
          :options="triggerOptions()"
          optionLabel="label"
          optionValue="value"
        />
        <label>{{ t('automations.form.thresholdDays') }}</label>
        <InputNumber v-model="form.threshold_days" :min="0" />
        <label>{{ t('automations.form.channel') }}</label>
        <Dropdown
          v-model="form.channel"
          :options="channelOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>{{ t('automations.form.messageTemplate') }}</label>
        <Textarea v-model="form.message_template" rows="4" autoResize />
        <small class="hint">{{ t('automations.form.placeholderHint') }}</small>
      </div>
      <template #footer>
        <Button :label="t('automations.form.cancel')" text @click="showDialog = false" />
        <Button :label="t('automations.form.save')" :loading="saving" @click="save" />
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
