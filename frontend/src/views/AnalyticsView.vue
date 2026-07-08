<script setup lang="ts">
import { ref, onMounted } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Card from 'primevue/card'

import { getCommunityPulse, getTeacherReach } from '@/api/analytics'
import type { CommunityPulse, TeacherReach } from '@/types'

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
    error.value = 'Die Übersicht konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>Gemeinschaft</h1>
    <p class="lead">
      Ein sanfter Blick darauf, wie es eurer Gemeinschaft geht – keine Zahlen zum
      Optimieren, sondern ein Gefühl für die Menschen, die zusammen praktizieren.
    </p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">Wird geladen…</p>

    <template v-else-if="pulse">
      <div class="kpis">
        <Card><template #content><span class="k-label">Menschen, die praktizieren</span><span class="k-val">{{ pulse.people_practicing }}</span></template></Card>
        <Card><template #content><span class="k-label">Gemeinsame Praxis-Stunden</span><span class="k-val">{{ pulse.total_practices }}</span></template></Card>
        <Card><template #content><span class="k-label">Neu dazugekommen</span><span class="k-val">{{ pulse.new_members }}</span></template></Card>
        <Card><template #content><span class="k-label">Angebotene Stunden</span><span class="k-val">{{ pulse.sessions }}</span></template></Card>
      </div>

      <h2>Wen die Lehrenden begleiten</h2>
      <p class="lead">
        Wie viele Menschen eine Lehrkraft begleitet – und wie viele gerne wiederkommen.
      </p>
      <DataTable :value="teachers" dataKey="teacher_id" responsiveLayout="scroll">
        <Column field="teacher_id" header="Lehrkraft" />
        <Column field="sessions" header="Stunden" />
        <Column field="students_guided" header="Begleitete Menschen" />
        <Column field="returning_students" header="Kommen wieder" />
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
