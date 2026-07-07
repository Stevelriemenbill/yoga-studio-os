<script setup lang="ts">
import { computed } from 'vue'
import Card from 'primevue/card'
import Tag from 'primevue/tag'

import { useAuthStore } from '@/stores/auth'

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
</script>

<template>
  <div class="dashboard">
    <h1>Willkommen{{ auth.user?.full_name ? `, ${auth.user.full_name}` : '' }}</h1>
    <p class="subtitle">Studio Operating System &mdash; Fundament</p>

    <div class="grid">
      <Card>
        <template #title>Dein Konto</template>
        <template #content>
          <p><strong>E-Mail:</strong> {{ auth.user?.email }}</p>
          <p>
            <strong>Rolle:</strong>
            <Tag :value="roleLabel" severity="success" />
          </p>
        </template>
      </Card>

      <Card>
        <template #title>Nächste Module</template>
        <template #content>
          <ul class="module-list">
            <li>Kursverwaltung</li>
            <li>Mitgliederverwaltung</li>
            <li>Buchungssystem</li>
            <li>Intelligente Warteliste</li>
            <li>Check-in &amp; Anwesenheit</li>
          </ul>
        </template>
      </Card>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 900px;
  margin: 0 auto;
}
.subtitle {
  color: #6b7280;
  margin-top: -0.5rem;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}
.module-list {
  margin: 0;
  padding-left: 1.2rem;
  line-height: 1.9;
}
</style>
