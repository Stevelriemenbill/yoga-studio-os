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

import { listMembers, createMember, updateMember, deleteMember, inviteMember } from '@/api/members'
import type { Member, MembershipType } from '@/types'

const { t } = useI18n()

const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')

const membershipOptions = (): { label: string; value: MembershipType }[] => [
  { label: t('members.membershipTypes.none'), value: 'none' },
  { label: t('members.membershipTypes.drop_in'), value: 'drop_in' },
  { label: t('members.membershipTypes.punch_card'), value: 'punch_card' },
  { label: t('members.membershipTypes.unlimited'), value: 'unlimited' },
]

function membershipLabel(value: string): string {
  return membershipOptions().find((o) => o.value === value)?.label ?? value
}

const showDialog = ref(false)
const saving = ref(false)
const editingId = ref<string | null>(null)
const form = ref<{
  first_name: string
  last_name: string
  email: string
  phone: string
  membership_type: MembershipType
  credits: number
}>({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  membership_type: 'none',
  credits: 0,
})

function fmtScore(v: number): string {
  return (v ?? 0).toFixed(2)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    members.value = await listMembers()
  } catch {
    error.value = t('members.errors.loadFailed')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = {
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    membership_type: 'none',
    credits: 0,
  }
  showDialog.value = true
}

function openEdit(m: Member) {
  editingId.value = m.id
  form.value = {
    first_name: m.first_name,
    last_name: m.last_name,
    email: m.email ?? '',
    phone: m.phone ?? '',
    membership_type: m.membership_type,
    credits: m.credits,
  }
  showDialog.value = true
}

async function save() {
  saving.value = true
  error.value = ''
  const payload = {
    first_name: form.value.first_name,
    last_name: form.value.last_name,
    email: form.value.email || undefined,
    phone: form.value.phone || undefined,
    membership_type: form.value.membership_type,
    credits: form.value.credits,
  }
  try {
    if (editingId.value) {
      await updateMember(editingId.value, payload)
    } else {
      await createMember(payload)
    }
    showDialog.value = false
    await load()
  } catch {
    error.value = t('members.errors.saveFailed')
  } finally {
    saving.value = false
  }
}

async function remove(m: Member) {
  if (!confirm(t('members.confirmDelete', { name: `${m.first_name} ${m.last_name}` }))) return
  error.value = ''
  try {
    await deleteMember(m.id)
    await load()
  } catch {
    error.value = t('members.errors.deleteFailed')
  }
}

const inviting = ref<string | null>(null)

async function invite(m: Member) {
  error.value = ''
  notice.value = ''
  if (!m.email) {
    error.value = t('members.errors.noEmail', { name: m.first_name })
    return
  }
  inviting.value = m.id
  try {
    const { invite_url, email_delivered } = await inviteMember(m.id)
    if (email_delivered) {
      notice.value = t('members.invite.emailSent', { email: m.email })
    } else {
      // Kein echter Mailversand konfiguriert: Link ehrlich anzeigen.
      try {
        await navigator.clipboard.writeText(invite_url)
        notice.value = t('members.invite.copiedToClipboard', { email: m.email, url: invite_url })
      } catch {
        notice.value = t('members.invite.shareManually', { email: m.email, url: invite_url })
      }
    }
  } catch {
    error.value = t('members.errors.inviteFailed')
  } finally {
    inviting.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('members.title') }}</h1>
      <Button :label="t('members.newMember')" icon="pi pi-plus" @click="openCreate" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="loading">{{ t('members.loading') }}</p>

    <DataTable v-else :value="members" dataKey="id" responsiveLayout="scroll">
      <Column field="first_name" :header="t('members.columns.firstName')" />
      <Column field="last_name" :header="t('members.columns.lastName')" />
      <Column field="email" :header="t('members.columns.email')" />
      <Column :header="t('members.columns.membership')">
        <template #body="{ data }">
          <Tag :value="membershipLabel(data.membership_type)" />
        </template>
      </Column>
      <Column field="credits" :header="t('members.columns.credits')" />
      <Column :header="t('members.columns.reliability')">
        <template #body="{ data }">{{ fmtScore(data.reliability_score) }}</template>
      </Column>
      <Column :header="t('members.columns.account')">
        <template #body="{ data }">
          <Tag v-if="data.user_id" :value="t('members.activated')" severity="success" />
          <Button
            v-else
            :label="t('members.inviteButton')"
            icon="pi pi-envelope"
            size="small"
            text
            :loading="inviting === data.id"
            :disabled="!data.email"
            @click="invite(data)"
          />
        </template>
      </Column>
      <Column :header="t('members.columns.actions')">
        <template #body="{ data }">
          <Button icon="pi pi-pencil" size="small" text @click="openEdit(data)" />
          <Button
            icon="pi pi-trash"
            size="small"
            text
            severity="danger"
            @click="remove(data)"
          />
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="showDialog"
      :header="editingId ? t('members.dialog.editTitle') : t('members.dialog.createTitle')"
      modal
      :style="{ width: '460px' }"
    >
      <div class="form">
        <label>{{ t('members.form.firstName') }}</label>
        <InputText v-model="form.first_name" />
        <label>{{ t('members.form.lastName') }}</label>
        <InputText v-model="form.last_name" />
        <label>{{ t('members.form.email') }}</label>
        <InputText v-model="form.email" />
        <label>{{ t('members.form.phone') }}</label>
        <InputText v-model="form.phone" />
        <label>{{ t('members.form.membership') }}</label>
        <Dropdown
          v-model="form.membership_type"
          :options="membershipOptions()"
          optionLabel="label"
          optionValue="value"
        />
        <label>{{ t('members.form.credits') }}</label>
        <InputNumber v-model="form.credits" :min="0" />
      </div>
      <template #footer>
        <Button :label="t('members.form.cancel')" text @click="showDialog = false" />
        <Button :label="t('members.form.save')" :loading="saving" @click="save" />
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
.error {
  color: #dc2626;
}
.notice {
  color: var(--p-primary-700, #047857);
  background: var(--p-primary-50, #ecfdf5);
  border: 1px solid var(--p-primary-200, #a7f3d0);
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
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
