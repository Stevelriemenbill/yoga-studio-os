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

import {
  listStaff,
  inviteStaff,
  revokeStaffInvite,
  type StaffListEntry,
  type StaffInviteRole,
} from '@/api/users'

const { t } = useI18n()

const entries = ref<StaffListEntry[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')

const showDialog = ref(false)
const saving = ref(false)
const form = ref<{ email: string; full_name: string; role: StaffInviteRole }>({
  email: '',
  full_name: '',
  role: 'teacher',
})

const roleOptions = (): { label: string; value: StaffInviteRole }[] => [
  { label: t('users.roles.teacher'), value: 'teacher' },
  { label: t('users.roles.studio_manager'), value: 'studio_manager' },
  { label: t('users.roles.reception'), value: 'reception' },
]

function roleLabel(value: string): string {
  return roleOptions().find((o) => o.value === value)?.label ?? value
}

function statusSeverity(status: string): string {
  if (status === 'active') return 'success'
  if (status === 'pending') return 'warn'
  return 'secondary'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    entries.value = await listStaff()
  } catch {
    error.value = t('users.errors.loadFailed')
  } finally {
    loading.value = false
  }
}

function openInvite() {
  form.value = { email: '', full_name: '', role: 'teacher' }
  showDialog.value = true
}

async function submit() {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    const result = await inviteStaff({
      email: form.value.email,
      full_name: form.value.full_name || undefined,
      role: form.value.role,
    })
    showDialog.value = false
    if (result.email_delivered) {
      notice.value = t('users.invite.emailSent', { email: form.value.email })
    } else {
      try {
        await navigator.clipboard.writeText(result.invite_url)
        notice.value = t('users.invite.copiedToClipboard', {
          email: form.value.email,
          url: result.invite_url,
        })
      } catch {
        notice.value = t('users.invite.shareManually', {
          email: form.value.email,
          url: result.invite_url,
        })
      }
    }
    await load()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err.response?.data?.detail ?? t('users.errors.inviteFailed')
  } finally {
    saving.value = false
  }
}

async function revoke(entry: StaffListEntry) {
  if (!confirm(t('users.confirmRevoke', { email: entry.email }))) return
  error.value = ''
  try {
    await revokeStaffInvite(entry.id)
    await load()
  } catch {
    error.value = t('users.errors.revokeFailed')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('users.title') }}</h1>
      <Button :label="t('users.inviteButton')" icon="pi pi-user-plus" @click="openInvite" />
    </div>
    <p class="subtitle">{{ t('users.subtitle') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="loading">{{ t('users.loading') }}</p>

    <DataTable v-else :value="entries" dataKey="id" responsiveLayout="scroll">
      <Column field="full_name" :header="t('users.columns.name')">
        <template #body="{ data }">{{ data.full_name || '—' }}</template>
      </Column>
      <Column field="email" :header="t('users.columns.email')" />
      <Column :header="t('users.columns.role')">
        <template #body="{ data }">
          <Tag :value="roleLabel(data.role)" />
        </template>
      </Column>
      <Column :header="t('users.columns.status')">
        <template #body="{ data }">
          <Tag
            :value="t('users.status.' + data.status)"
            :severity="statusSeverity(data.status)"
          />
        </template>
      </Column>
      <Column :header="t('users.columns.actions')">
        <template #body="{ data }">
          <Button
            v-if="data.kind === 'invite'"
            icon="pi pi-times"
            size="small"
            text
            severity="danger"
            :label="t('users.revoke')"
            @click="revoke(data)"
          />
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="showDialog"
      :header="t('users.dialog.title')"
      modal
      :style="{ width: '440px' }"
    >
      <div class="form">
        <label>{{ t('users.form.email') }}</label>
        <InputText v-model="form.email" type="email" />
        <label>{{ t('users.form.fullName') }}</label>
        <InputText v-model="form.full_name" />
        <label>{{ t('users.form.role') }}</label>
        <Dropdown
          v-model="form.role"
          :options="roleOptions()"
          optionLabel="label"
          optionValue="value"
        />
      </div>
      <template #footer>
        <Button :label="t('users.form.cancel')" text @click="showDialog = false" />
        <Button
          :label="t('users.form.send')"
          icon="pi pi-envelope"
          :loading="saving"
          :disabled="!form.email"
          @click="submit"
        />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.page {
  max-width: 1000px;
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
.error {
  color: #dc2626;
}
.notice {
  color: var(--p-primary-700, #047857);
  background: var(--p-primary-50, #ecfdf5);
  border: 1px solid var(--p-primary-200, #a7f3d0);
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  word-break: break-all;
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
