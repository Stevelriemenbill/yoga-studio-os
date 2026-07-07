<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

import { useAuthStore } from '@/stores/auth'
import { useRealtime } from '@/composables/useRealtime'
import { getKpis } from '@/api/analytics'
import type { StudioKpis } from '@/types'

const auth = useAuthStore()

const roleLabels: Record<string, string> = {
  studio_admin: 'Studio-Administrator',
  studio_manager: 'Studio-Manager',
  teacher: 'Lehrer',
  reception: 'Empfang',
  member: 'Mitglied',
  trainee: 'Yogalehrer in Ausbildung',
}

const roleLabel = computed(() =>
  auth.user ? (roleLabels[auth.user.role] ?? auth.user.role) : '',
)

const kpis = ref<StudioKpis | null>(null)
const loading = ref(true)
const events = ref<string[]>([])

const { connected } = useRealtime((event) => {
  events.value.unshift(
    `${new Date(event.ts).toLocaleTimeString('de-DE')} — ${event.type}`,
  )
  events.value = events.value.slice(0, 10)
})

function pct(x: number): string {
  return `${(x * 100).toFixed(0)} %`
}

onMounted(async () => {
  try {
    kpis.value = await getKpis()
  } catch {
    // KPIs are best-effort on the dashboard.
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard">
    <div class="head">
      <div>
        <h1>Willkommen{{ auth.user?.full_name ? `, ${auth.user.full_name}` : '' }}</h1>
        <p class="subtitle">Studio Operating System</p>
      </div>
      <Tag
        :value="connected ? 'Live verbunden' : 'Offline'"
        :severity="connected ? 'success' : 'warning'"
        :icon="connected ? 'pi pi-circle-fill' : 'pi pi-circle'"
      />
    </div>

    <div v-if="kpis" class="kpis">
      <Card><template #content><span class="k-label">Auslastung</span><span class="k-val">{{ pct(kpis.utilization) }}</span></template></Card>
      <Card><template #content><span class="k-label">No-Show-Rate</span><span class="k-val">{{ pct(kpis.no_show_rate) }}</span></template></Card>
      <Card><template #content><span class="k-label">Buchungen (30 T.)</span><span class="k-val">{{ kpis.bookings }}</span></template></Card>
      <Card><template #content><span class="k-label">Kurse</span><span class="k-val">{{ kpis.sessions }}</span></template></Card>
      <Card><template #content><span class="k-label">Check-ins</span><span class="k-val">{{ kpis.check_ins }}</span></template></Card>
      <Card><template #content><span class="k-label">Neue Mitglieder</span><span class="k-val">{{ kpis.new_members }}</span></template></Card>
    </div>

    <div class="grid">
      <Card>
        <template #title>Dein Konto</template>
        <template #content>
          <p><strong>E-Mail:</strong> {{ auth.user?.email }}</p>
          <p><strong>Rolle:</strong> <Tag :value="roleLabel" severity="success" /></p>
        </template>
      </Card>

      <Card>
        <template #title>Live-Ereignisse</template>
        <template #content>
          <ul v-if="events.length" class="events">
            <li v-for="(e, i) in events" :key="i">{{ e }}</li>
          </ul>
          <p v-else class="muted">Noch keine Ereignisse. Aktivität erscheint hier in Echtzeit.</p>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 1100px;
  margin: 0 auto;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.subtitle {
  color: #6b7280;
  margin-top: -0.5rem;
}
.kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 1.5rem;
}
.k-label {
  display: block;
  color: #6b7280;
  font-size: 0.8rem;
}
.k-val {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}
.events {
  margin: 0;
  padding-left: 1.1rem;
  line-height: 1.8;
  font-size: 0.9rem;
}
.muted {
  color: #9ca3af;
}
</style>
