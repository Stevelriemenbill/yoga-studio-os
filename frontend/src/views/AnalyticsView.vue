<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Card from 'primevue/card'

import { getCommunityPulse, getTeacherReach } from '@/api/analytics'
import type { CommunityPulse, TeacherReach } from '@/types'

const { t } = useI18n()

const pulse = ref<CommunityPulse | null>(null)
const teachers = ref<TeacherReach[]>([])
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    pulse.value = await getCommunityPulse()
    teachers.value = await getTeacherReach()
  } catch {
    error.value = t('analytics.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('analytics.title') }}</h1>
    <p class="lead">
      {{ t('analytics.lead') }}
    </p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">{{ t('analytics.loading') }}</p>

    <template v-else-if="pulse">
      <div class="kpis">
        <Card><template #content><span class="k-label">{{ t('analytics.peoplePracticing') }}</span><span class="k-val">{{ pulse.people_practicing }}</span></template></Card>
        <Card><template #content><span class="k-label">{{ t('analytics.sharedPracticeHours') }}</span><span class="k-val">{{ pulse.total_practices }}</span></template></Card>
        <Card><template #content><span class="k-label">{{ t('analytics.newMembers') }}</span><span class="k-val">{{ pulse.new_members }}</span></template></Card>
        <Card><template #content><span class="k-label">{{ t('analytics.sessionsOffered') }}</span><span class="k-val">{{ pulse.sessions }}</span></template></Card>
      </div>

      <h2>{{ t('analytics.teachersHeading') }}</h2>
      <p class="lead">
        {{ t('analytics.teachersLead') }}
      </p>
      <DataTable :value="teachers" dataKey="teacher_id" responsiveLayout="scroll">
        <Column field="teacher_id" :header="t('analytics.colTeacher')" />
        <Column field="sessions" :header="t('analytics.colSessions')" />
        <Column field="students_guided" :header="t('analytics.colStudentsGuided')" />
        <Column field="returning_students" :header="t('analytics.colReturning')" />
      </DataTable>
    </template>
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
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.k-label {
  display: block;
  color: #6b7280;
  font-size: 0.85rem;
}
.k-val {
  display: block;
  font-size: 1.6rem;
  font-weight: 700;
}
</style>
