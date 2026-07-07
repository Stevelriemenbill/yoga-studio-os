<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Card from 'primevue/card'

import { listInsights, generateInsights, getForecast, askAssistant } from '@/api/ai'
import type { AIInsight, FillForecast } from '@/types'

const insights = ref<AIInsight[]>([])
const answers = ref<AIInsight[]>([])
const forecasts = ref<FillForecast[]>([])
const question = ref('')
const asking = ref(false)
const generating = ref(false)
const loadingForecast = ref(false)
const loading = ref(false)
const error = ref('')

function pct(x: number): string {
  return (x * 100).toFixed(0) + '%'
}
function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString('de-DE')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    insights.value = await listInsights()
  } catch {
    error.value = 'Insights konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

async function ask() {
  if (!question.value.trim()) return
  asking.value = true
  error.value = ''
  try {
    const insight = await askAssistant(question.value)
    answers.value.unshift(insight)
    question.value = ''
  } catch {
    error.value = 'Frage konnte nicht beantwortet werden.'
  } finally {
    asking.value = false
  }
}

async function refresh() {
  generating.value = true
  error.value = ''
  try {
    insights.value = await generateInsights()
  } catch {
    error.value = 'Insights konnten nicht aktualisiert werden.'
  } finally {
    generating.value = false
  }
}

async function loadForecast() {
  loadingForecast.value = true
  error.value = ''
  try {
    forecasts.value = await getForecast()
  } catch {
    error.value = 'Prognose konnte nicht geladen werden.'
  } finally {
    loadingForecast.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>KI-Assistent</h1>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>Frage stellen</template>
      <template #content>
        <div class="ask">
          <Textarea v-model="question" rows="2" autoResize placeholder="Deine Frage…" />
          <Button label="Fragen" :loading="asking" @click="ask" />
        </div>
        <div class="cards">
          <Card v-for="a in answers" :key="a.id" class="insight">
            <template #title>{{ a.title }}</template>
            <template #content><p>{{ a.body }}</p></template>
          </Card>
        </div>
      </template>
    </Card>

    <div class="header">
      <h2>Insights</h2>
      <Button label="Insights aktualisieren" icon="pi pi-refresh" outlined :loading="generating" @click="refresh" />
    </div>
    <p v-if="loading">Wird geladen…</p>
    <div v-else class="cards">
      <Card v-for="i in insights" :key="i.id" class="insight">
        <template #title>
          <div class="insight-head">
            <span>{{ i.title }}</span>
            <Tag :value="i.type" />
          </div>
        </template>
        <template #content>
          <p>{{ i.body }}</p>
          <small class="muted">{{ fmtDateTime(i.created_at) }}</small>
        </template>
      </Card>
    </div>

    <div class="header">
      <h2>Prognose</h2>
      <Button label="Prognose laden" icon="pi pi-chart-line" outlined :loading="loadingForecast" @click="loadForecast" />
    </div>
    <DataTable :value="forecasts" dataKey="session_id" responsiveLayout="scroll">
      <Column header="Beginn">
        <template #body="{ data }">{{ fmtDateTime(data.starts_at) }}</template>
      </Column>
      <Column header="Prognose Auslastung">
        <template #body="{ data }">{{ pct(data.predicted_fill_rate) }}</template>
      </Column>
      <Column header="Voll">
        <template #body="{ data }">
          <Tag v-if="data.likely_full" value="Wahrsch. voll" severity="success" />
          <span v-else>—</span>
        </template>
      </Column>
      <Column header="Unterbucht">
        <template #body="{ data }">
          <Tag v-if="data.likely_underbooked" value="Unterbucht" severity="warning" />
          <span v-else>—</span>
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.error {
  color: #dc2626;
}
.block {
  margin-bottom: 1rem;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.ask {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}
.ask :deep(textarea) {
  flex: 1;
}
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.insight-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}
.muted {
  color: #6b7280;
}
</style>
