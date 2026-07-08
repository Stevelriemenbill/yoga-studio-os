<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import {
  listMyEvents,
  myEventRegistrations,
  registerForEvent,
} from '@/api/me'
import type { StudioEvent, EventRegistration } from '@/types'

const { t, locale } = useI18n()

const events = ref<StudioEvent[]>([])
const registrations = ref<EventRegistration[]>([])
const loading = ref(false)
const busyId = ref<string | null>(null)
const error = ref('')
const info = ref('')

/** Map of event_id -> the member's active registration status (if any). */
const regByEvent = computed(() => {
  const map = new Map<string, EventRegistration>()
  for (const r of registrations.value) {
    if (r.status !== 'cancelled') map.set(r.event_id, r)
  }
  return map
})

function fmtWhen(iso: string): string {
  return new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function fmtPrice(cents: number): string {
  if (cents <= 0) return t('myArea.free')
  return new Intl.NumberFormat(locale.value === 'de' ? 'de-DE' : 'en-US', {
    style: 'currency',
    currency: 'EUR',
  }).format(cents / 100)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [evs, regs] = await Promise.all([listMyEvents(), myEventRegistrations()])
    events.value = evs
    registrations.value = regs
  } catch {
    error.value = t('myArea.loadError')
  } finally {
    loading.value = false
  }
}

async function register(event: StudioEvent) {
  busyId.value = event.id
  error.value = ''
  info.value = ''
  try {
    const reg = await registerForEvent(event.id)
    registrations.value = [reg, ...registrations.value]
    info.value = t('myArea.registerSuccess')
  } catch {
    error.value = t('myArea.registerError')
  } finally {
    busyId.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('myArea.eventsTitle') }}</h1>
    <p class="lead">{{ t('myArea.eventsLead') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="info" class="info">{{ info }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>
    <p v-else-if="events.length === 0" class="muted">{{ t('myArea.noEvents') }}</p>

    <DataTable v-else :value="events" dataKey="id" responsiveLayout="scroll">
      <Column :header="t('myArea.event')">
        <template #body="{ data }">
          <div class="event-name">{{ data.name }}</div>
          <Tag :value="t(`myArea.eventTypes.${data.type}`)" severity="secondary" />
        </template>
      </Column>
      <Column :header="t('myArea.when')">
        <template #body="{ data }">{{ fmtWhen(data.starts_at) }}</template>
      </Column>
      <Column :header="t('myArea.location')">
        <template #body="{ data }">{{ data.location || '—' }}</template>
      </Column>
      <Column :header="t('myArea.price')">
        <template #body="{ data }">{{ fmtPrice(data.price_cents) }}</template>
      </Column>
      <Column :header="t('myArea.action')">
        <template #body="{ data }">
          <Tag
            v-if="regByEvent.get(data.id)?.status === 'confirmed'"
            severity="success"
            :value="t('myArea.registered')"
          />
          <Tag
            v-else-if="regByEvent.get(data.id)?.status === 'waitlisted'"
            severity="warn"
            :value="t('myArea.waitlisted')"
          />
          <Tag
            v-else-if="regByEvent.get(data.id)?.status === 'pending'"
            severity="info"
            :value="t('myArea.pendingPayment')"
          />
          <Button
            v-else
            :label="t('myArea.register')"
            size="small"
            :loading="busyId === data.id"
            @click="register(data)"
          />
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.page {
  max-width: 900px;
  margin: 0 auto;
}
.lead {
  color: #6b7280;
  margin-bottom: 1.25rem;
}
.error {
  color: #dc2626;
}
.info {
  color: var(--p-primary-600, #059669);
}
.muted {
  color: #6b7280;
}
.event-name {
  font-weight: 600;
  margin-bottom: 0.25rem;
}
</style>
