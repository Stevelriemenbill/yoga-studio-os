<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Card from 'primevue/card'

import { listInsights, generateInsights, askAssistant } from '@/api/care'
import type { AIInsight } from '@/types'

const { t, locale } = useI18n()

const insights = ref<AIInsight[]>([])
const answers = ref<AIInsight[]>([])
const question = ref('')
const asking = ref(false)
const generating = ref(false)
const loading = ref(false)
const error = ref('')

const suggestions = computed(() => [
  t('assistant.suggestionCare'),
  t('assistant.suggestionMilestone'),
  t('assistant.suggestionNew'),
])

const typeLabel = computed<Record<string, string>>(() => ({
  care: t('assistant.typeCare'),
  milestone: t('assistant.typeMilestone'),
  assistant_answer: t('assistant.typeAnswer'),
}))

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString(locale.value === 'de' ? 'de-DE' : 'en-US')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    insights.value = await listInsights()
  } catch {
    error.value = t('assistant.loadError')
  } finally {
    loading.value = false
  }
}

async function ask(preset?: string) {
  const q = (preset ?? question.value).trim()
  if (!q) return
  asking.value = true
  error.value = ''
  try {
    const insight = await askAssistant(q)
    answers.value.unshift(insight)
    question.value = ''
  } catch {
    error.value = t('assistant.askError')
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
    error.value = t('assistant.refreshError')
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('assistant.title') }}</h1>
    <p class="lead">
      {{ t('assistant.lead') }}
    </p>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>{{ t('assistant.askMe') }}</template>
      <template #content>
        <div class="ask">
          <Textarea v-model="question" rows="2" autoResize :placeholder="t('assistant.questionPlaceholder')" />
          <Button :label="t('assistant.ask')" :loading="asking" @click="ask()" />
        </div>
        <div class="chips">
          <Button
            v-for="s in suggestions"
            :key="s"
            :label="s"
            text
            size="small"
            @click="ask(s)"
          />
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
      <h2>{{ t('assistant.insightsHeading') }}</h2>
      <Button :label="t('assistant.refresh')" icon="pi pi-refresh" outlined :loading="generating" @click="refresh" />
    </div>
    <p v-if="loading">{{ t('assistant.loading') }}</p>
    <p v-else-if="insights.length === 0" class="muted">
      {{ t('assistant.noInsights') }}
    </p>
    <div v-else class="cards">
      <Card v-for="i in insights" :key="i.id" class="insight">
        <template #title>
          <div class="insight-head">
            <span>{{ i.title }}</span>
            <Tag :value="typeLabel[i.type] ?? i.type" />
          </div>
        </template>
        <template #content>
          <p>{{ i.body }}</p>
          <small class="muted">{{ fmtDateTime(i.created_at) }}</small>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 1100px;
  margin: 0 auto;
}
.lead {
  color: #6b7280;
  margin-bottom: 1.25rem;
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
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  margin-top: 0.5rem;
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
