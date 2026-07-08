<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import {
  listJoinRequests,
  approveJoinRequest,
  declineJoinRequest,
  type JoinRequest,
} from '@/api/join'
import { useAuthStore } from '@/stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()

const joinLink = computed(() =>
  auth.studioSlug ? `${window.location.origin}/join/${auth.studioSlug}` : '',
)
const linkCopied = ref(false)

async function copyLink() {
  if (!joinLink.value) return
  try {
    await navigator.clipboard.writeText(joinLink.value)
    linkCopied.value = true
    setTimeout(() => (linkCopied.value = false), 2500)
  } catch {
    /* clipboard unavailable */
  }
}

const requests = ref<JoinRequest[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const busyId = ref<string | null>(null)

const pending = computed(() =>
  requests.value.filter((r) => r.status === 'pending'),
)
const reviewed = computed(() =>
  requests.value.filter((r) => r.status !== 'pending'),
)

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString(locale.value)
}

function statusSeverity(status: string): string {
  if (status === 'approved') return 'success'
  if (status === 'declined') return 'danger'
  return 'warn'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    requests.value = await listJoinRequests()
  } catch {
    error.value = t('joinRequests.errors.loadFailed')
  } finally {
    loading.value = false
  }
}

async function approve(r: JoinRequest) {
  error.value = ''
  notice.value = ''
  busyId.value = r.id
  try {
    const result = await approveJoinRequest(r.id)
    if (result.email_delivered) {
      notice.value = t('joinRequests.approved.emailSent', { email: r.email })
    } else {
      try {
        await navigator.clipboard.writeText(result.invite_url)
        notice.value = t('joinRequests.approved.copiedToClipboard', {
          email: r.email,
          url: result.invite_url,
        })
      } catch {
        notice.value = t('joinRequests.approved.shareManually', {
          email: r.email,
          url: result.invite_url,
        })
      }
    }
    await load()
  } catch {
    error.value = t('joinRequests.errors.approveFailed')
  } finally {
    busyId.value = null
  }
}

async function decline(r: JoinRequest) {
  if (!confirm(t('joinRequests.confirmDecline', { name: `${r.first_name} ${r.last_name}` })))
    return
  error.value = ''
  busyId.value = r.id
  try {
    await declineJoinRequest(r.id)
    await load()
  } catch {
    error.value = t('joinRequests.errors.declineFailed')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>{{ t('joinRequests.title') }}</h1>
    </div>
    <p class="subtitle">{{ t('joinRequests.subtitle') }}</p>

    <div v-if="joinLink" class="share">
      <span class="share-label">{{ t('joinRequests.shareLabel') }}</span>
      <code class="share-link">{{ joinLink }}</code>
      <Button
        :icon="linkCopied ? 'pi pi-check' : 'pi pi-copy'"
        :label="linkCopied ? t('joinRequests.copied') : t('joinRequests.copyLink')"
        size="small"
        text
        @click="copyLink"
      />
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="loading">{{ t('joinRequests.loading') }}</p>

    <template v-else>
      <h2>{{ t('joinRequests.pending') }} ({{ pending.length }})</h2>
      <p v-if="!pending.length" class="muted">{{ t('joinRequests.noPending') }}</p>
      <DataTable v-else :value="pending" dataKey="id" responsiveLayout="scroll">
        <Column :header="t('joinRequests.columns.name')">
          <template #body="{ data }">{{ data.first_name }} {{ data.last_name }}</template>
        </Column>
        <Column field="email" :header="t('joinRequests.columns.email')" />
        <Column field="phone" :header="t('joinRequests.columns.phone')">
          <template #body="{ data }">{{ data.phone || '—' }}</template>
        </Column>
        <Column field="message" :header="t('joinRequests.columns.message')">
          <template #body="{ data }">
            <span class="message">{{ data.message || '—' }}</span>
          </template>
        </Column>
        <Column :header="t('joinRequests.columns.received')">
          <template #body="{ data }">{{ fmtDate(data.created_at) }}</template>
        </Column>
        <Column :header="t('joinRequests.columns.actions')">
          <template #body="{ data }">
            <Button
              icon="pi pi-check"
              size="small"
              :label="t('joinRequests.approve')"
              :loading="busyId === data.id"
              @click="approve(data)"
            />
            <Button
              icon="pi pi-times"
              size="small"
              text
              severity="danger"
              :label="t('joinRequests.decline')"
              :disabled="busyId === data.id"
              @click="decline(data)"
            />
          </template>
        </Column>
      </DataTable>

      <template v-if="reviewed.length">
        <h2 class="reviewed-heading">{{ t('joinRequests.reviewed') }}</h2>
        <DataTable :value="reviewed" dataKey="id" responsiveLayout="scroll">
          <Column :header="t('joinRequests.columns.name')">
            <template #body="{ data }">{{ data.first_name }} {{ data.last_name }}</template>
          </Column>
          <Column field="email" :header="t('joinRequests.columns.email')" />
          <Column :header="t('joinRequests.columns.status')">
            <template #body="{ data }">
              <Tag
                :value="t('joinRequests.status.' + data.status)"
                :severity="statusSeverity(data.status)"
              />
            </template>
          </Column>
          <Column :header="t('joinRequests.columns.received')">
            <template #body="{ data }">{{ fmtDate(data.created_at) }}</template>
          </Column>
        </DataTable>
      </template>
    </template>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.subtitle {
  color: #64748b;
  margin-top: -0.5rem;
}
.share {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  background: var(--p-primary-50, #ecfdf5);
  border: 1px solid var(--p-primary-200, #a7f3d0);
  padding: 0.5rem 0.85rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}
.share-label {
  font-weight: 600;
  color: var(--p-primary-700, #047857);
}
.share-link {
  font-family: monospace;
  word-break: break-all;
}
.reviewed-heading {
  margin-top: 2rem;
}
.error {
  color: #dc2626;
}
.muted {
  color: #94a3b8;
}
.message {
  display: inline-block;
  max-width: 320px;
  white-space: pre-wrap;
}
.notice {
  color: var(--p-primary-700, #047857);
  background: var(--p-primary-50, #ecfdf5);
  border: 1px solid var(--p-primary-200, #a7f3d0);
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  word-break: break-all;
}
</style>
