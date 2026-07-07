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

import { listMembers, createMember, updateMember, deleteMember } from '@/api/members'
import type { Member, MembershipType } from '@/types'

const members = ref<Member[]>([])
const loading = ref(false)
const error = ref('')

const membershipOptions: { label: string; value: MembershipType }[] = [
  { label: 'Keine', value: 'none' },
  { label: 'Unbegrenzt', value: 'unlimited' },
  { label: 'Guthaben', value: 'credits' },
  { label: 'Testphase', value: 'trial' },
]

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
    error.value = 'Mitglieder konnten nicht geladen werden.'
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
    error.value = 'Mitglied konnte nicht gespeichert werden.'
  } finally {
    saving.value = false
  }
}

async function remove(m: Member) {
  if (!confirm(`Mitglied ${m.first_name} ${m.last_name} löschen?`)) return
  error.value = ''
  try {
    await deleteMember(m.id)
    await load()
  } catch {
    error.value = 'Mitglied konnte nicht gelöscht werden.'
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>Mitglieder</h1>
      <Button label="Neues Mitglied" icon="pi pi-plus" @click="openCreate" />
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">Wird geladen…</p>

    <DataTable v-else :value="members" dataKey="id" responsiveLayout="scroll">
      <Column field="first_name" header="Vorname" />
      <Column field="last_name" header="Nachname" />
      <Column field="email" header="E-Mail" />
      <Column header="Mitgliedschaft">
        <template #body="{ data }">
          <Tag :value="data.membership_type" />
        </template>
      </Column>
      <Column field="credits" header="Guthaben" />
      <Column header="Zuverlässigkeit">
        <template #body="{ data }">{{ fmtScore(data.reliability_score) }}</template>
      </Column>
      <Column header="Aktionen">
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
      :header="editingId ? 'Mitglied bearbeiten' : 'Neues Mitglied'"
      modal
      :style="{ width: '460px' }"
    >
      <div class="form">
        <label>Vorname</label>
        <InputText v-model="form.first_name" />
        <label>Nachname</label>
        <InputText v-model="form.last_name" />
        <label>E-Mail</label>
        <InputText v-model="form.email" />
        <label>Telefon</label>
        <InputText v-model="form.phone" />
        <label>Mitgliedschaft</label>
        <Dropdown
          v-model="form.membership_type"
          :options="membershipOptions"
          optionLabel="label"
          optionValue="value"
        />
        <label>Guthaben</label>
        <InputNumber v-model="form.credits" :min="0" />
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
</style>
