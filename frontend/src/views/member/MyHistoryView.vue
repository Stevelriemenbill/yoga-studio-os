<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

import { myParticipation } from '@/api/me'
import type { ParticipationHistory } from '@/types'

const { t, locale } = useI18n()

const history = ref<ParticipationHistory | null>(null)
const loading = ref(false)
const error = ref('')

const dtfLocale = computed(() => (locale.value === 'de' ? 'de-DE' : 'en-US'))

function fmtWhen(iso: string): string {
  return new Date(iso).toLocaleString(dtfLocale.value, {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function fmtHours(h: number): string {
  return `${h.toLocaleString(dtfLocale.value, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })} h`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    history.value = await myParticipation()
  } catch {
    error.value = t('myArea.history.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('myArea.history.title') }}</h1>
    <p class="lead">{{ t('myArea.history.lead') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>

    <template v-else-if="history">
      <div class="stats">
        <div class="stat">
          <span class="stat-value">{{ history.total_sessions }}</span>
          <span class="stat-label">{{ t('myArea.history.sessions') }}</span>
        </div>
        <div class="stat">
          <span class="stat-value">{{ fmtHours(history.total_hours) }}</span>
          <span class="stat-label">{{ t('myArea.history.totalHours') }}</span>
        </div>
        <div class="stat training">
          <span class="stat-value">{{ fmtHours(history.training_hours) }}</span>
          <span class="stat-label">{{ t('myArea.history.trainingHours') }}</span>
        </div>
      </div>

      <p v-if="history.entries.length === 0" class="muted">
        {{ t('myArea.history.empty') }}
      </p>
      <DataTable
        v-else
        :value="history.entries"
        dataKey="session_id"
        responsiveLayout="scroll"
        paginator
        :rows="15"
      >
        <Column :header="t('myArea.history.course')">
          <template #body="{ data }">
            {{ data.course_name }}
            <Tag
              v-if="data.counts_for_training"
              class="training-tag"
              :value="t('myArea.history.training')"
              severity="info"
            />
          </template>
        </Column>
        <Column :header="t('myArea.history.when')">
          <template #body="{ data }">{{ fmtWhen(data.starts_at) }}</template>
        </Column>
        <Column :header="t('myArea.history.hours')">
          <template #body="{ data }">{{ fmtHours(data.hours) }}</template>
        </Column>
      </DataTable>
    </template>
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
.muted {
  color: #6b7280;
}
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.stat {
  flex: 1;
  min-width: 8rem;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.stat.training {
  background: var(--p-primary-50, #ecfdf5);
  border-color: var(--p-primary-200, #a7f3d0);
}
.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: #0f172a;
}
.stat-label {
  font-size: 0.85rem;
  color: #6b7280;
}
.training-tag {
  margin-left: 0.5rem;
}
</style>
