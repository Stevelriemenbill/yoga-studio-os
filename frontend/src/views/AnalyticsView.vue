<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Card from 'primevue/card'

import {
  getKpis,
  getHeatmap,
  getTeacherAnalytics,
  getPopularCourses,
} from '@/api/analytics'
import type {
  StudioKpis,
  HeatmapCell,
  TeacherAnalytics,
  PopularCourse,
} from '@/types'

const kpis = ref<StudioKpis | null>(null)
const heatmap = ref<HeatmapCell[]>([])
const teachers = ref<TeacherAnalytics[]>([])
const popular = ref<PopularCourse[]>([])
const loading = ref(false)
const error = ref('')

const weekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const hoursRange = Array.from({ length: 24 }, (_, i) => i)

function pct(x: number): string {
  return (x * 100).toFixed(0) + '%'
}

const heatmapIndex = computed(() => {
  const map = new Map<string, HeatmapCell>()
  for (const c of heatmap.value) {
    map.set(`${c.weekday}-${c.hour}`, c)
  }
  return map
})

function cellFor(weekday: number, hour: number): HeatmapCell | undefined {
  return heatmapIndex.value.get(`${weekday}-${hour}`)
}

function cellColor(cell: HeatmapCell | undefined): string {
  if (!cell) return '#f1f5f9'
  if (cell.level === 'green') return '#86efac'
  if (cell.level === 'yellow') return '#fde68a'
  return '#fca5a5'
}

function cellTitle(weekday: number, hour: number): string {
  const cell = cellFor(weekday, hour)
  if (!cell) return `${weekdays[weekday]} ${hour}:00 — keine Sessions`
  return `${weekdays[weekday]} ${hour}:00 — Auslastung ${pct(cell.utilization)}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    kpis.value = await getKpis()
    heatmap.value = await getHeatmap()
    teachers.value = await getTeacherAnalytics()
    popular.value = await getPopularCourses()
  } catch {
    error.value = 'Analysen konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>Analysen</h1>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">Wird geladen…</p>

    <template v-else-if="kpis">
      <div class="kpis">
        <Card><template #content><span class="k-label">Auslastung</span><span class="k-val">{{ pct(kpis.utilization) }}</span></template></Card>
        <Card><template #content><span class="k-label">No-Show-Rate</span><span class="k-val">{{ pct(kpis.no_show_rate) }}</span></template></Card>
        <Card><template #content><span class="k-label">Buchungen</span><span class="k-val">{{ kpis.bookings }}</span></template></Card>
        <Card><template #content><span class="k-label">Durchschn. Kursgröße</span><span class="k-val">{{ kpis.avg_class_size.toFixed(1) }}</span></template></Card>
        <Card><template #content><span class="k-label">Neue Mitglieder</span><span class="k-val">{{ kpis.new_members }}</span></template></Card>
        <Card><template #content><span class="k-label">Check-ins</span><span class="k-val">{{ kpis.check_ins }}</span></template></Card>
      </div>

      <h2>Auslastungs-Heatmap</h2>
      <div class="heatmap">
        <div class="hm-row hm-head">
          <div class="hm-corner"></div>
          <div v-for="h in hoursRange" :key="'h' + h" class="hm-hour">{{ h }}</div>
        </div>
        <div v-for="(wd, wi) in weekdays" :key="wd" class="hm-row">
          <div class="hm-day">{{ wd }}</div>
          <div
            v-for="h in hoursRange"
            :key="wd + '-' + h"
            class="hm-cell"
            :style="{ backgroundColor: cellColor(cellFor(wi, h)) }"
            :title="cellTitle(wi, h)"
          ></div>
        </div>
      </div>

      <h2>Lehrer</h2>
      <DataTable :value="teachers" dataKey="teacher_id" responsiveLayout="scroll">
        <Column field="teacher_id" header="Lehrer" />
        <Column field="sessions" header="Sessions" />
        <Column header="Auslastung">
          <template #body="{ data }">{{ pct(data.utilization) }}</template>
        </Column>
        <Column field="booked" header="Gebucht" />
        <Column field="no_shows" header="No-Shows" />
        <Column field="waitlist" header="Warteliste" />
        <Column field="unique_members" header="Mitglieder" />
      </DataTable>

      <h2>Beliebte Kurse</h2>
      <DataTable :value="popular" dataKey="course_id" responsiveLayout="scroll">
        <Column field="course_id" header="Kurs" />
        <Column field="bookings" header="Buchungen" />
      </DataTable>
    </template>
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
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
.heatmap {
  overflow-x: auto;
  margin-bottom: 1.5rem;
}
.hm-row {
  display: flex;
}
.hm-corner,
.hm-day {
  width: 32px;
  flex: 0 0 32px;
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hm-hour {
  width: 22px;
  flex: 0 0 22px;
  font-size: 0.65rem;
  text-align: center;
}
.hm-cell {
  width: 22px;
  height: 22px;
  flex: 0 0 22px;
  border: 1px solid #fff;
}
</style>
