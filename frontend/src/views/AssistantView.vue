<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Button from 'primevue/button'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Card from 'primevue/card'

import { listInsights, generateInsights, askAssistant } from '@/api/care'
import type { AIInsight } from '@/types'

const insights = ref<AIInsight[]>([])
const answers = ref<AIInsight[]>([])
const question = ref('')
const asking = ref(false)
const generating = ref(false)
const loading = ref(false)
const error = ref('')

const suggestions = [
  'Um wen sollten wir uns gerade kümmern?',
  'Wer feiert bald einen Meilenstein?',
  'Wer ist neu dazugekommen?',
]

const typeLabel: Record<string, string> = {
  care: 'Fürsorge',
  milestone: 'Meilenstein',
  assistant_answer: 'Antwort',
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
    error.value = 'Hinweise konnten nicht geladen werden.'
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
    error.value = 'Die Frage konnte nicht beantwortet werden.'
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
    error.value = 'Hinweise konnten nicht aktualisiert werden.'
  } finally {
    generating.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>Begleiter:in</h1>
    <p class="lead">
      Ein ruhiger Gefährte, der dir hilft, deine Schüler:innen zu begleiten –
      wer gerade Aufmerksamkeit braucht, wer bald etwas zu feiern hat, wer neu ist.
    </p>

    <p v-if="error" class="error">{{ error }}</p>

    <Card class="block">
      <template #title>Frag mich</template>
      <template #content>
        <div class="ask">
          <Textarea v-model="question" rows="2" autoResize placeholder="Deine Frage zur Begleitung…" />
          <Button label="Fragen" :loading="asking" @click="ask()" />
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
      <h2>Hinweise zur Begleitung</h2>
      <Button label="Aktualisieren" icon="pi pi-refresh" outlined :loading="generating" @click="refresh" />
    </div>
    <p v-if="loading">Wird geladen…</p>
    <p v-else-if="insights.length === 0" class="muted">
      Zurzeit gibt es keine Hinweise – eure Gemeinschaft praktiziert beständig.
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
