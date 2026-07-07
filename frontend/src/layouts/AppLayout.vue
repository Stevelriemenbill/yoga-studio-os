<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

interface NavItem {
  label: string
  icon: string
  to: string
}

const nav = computed<NavItem[]>(() => [
  { label: 'Dashboard', icon: 'pi pi-home', to: '/' },
  { label: 'Kurse', icon: 'pi pi-calendar', to: '/courses' },
  { label: 'Mitglieder', icon: 'pi pi-users', to: '/members' },
  { label: 'Buchungen', icon: 'pi pi-ticket', to: '/bookings' },
  { label: 'Check-in', icon: 'pi pi-qrcode', to: '/checkin' },
  { label: 'Ausbildung', icon: 'pi pi-graduation-cap', to: '/training' },
  { label: 'Events', icon: 'pi pi-star', to: '/events' },
  { label: 'Analytics', icon: 'pi pi-chart-bar', to: '/analytics' },
  { label: 'Automatisierung', icon: 'pi pi-bolt', to: '/automations' },
  { label: 'KI-Assistent', icon: 'pi pi-sparkles', to: '/assistant' },
  { label: 'Benachrichtigungen', icon: 'pi pi-bell', to: '/notifications' },
])

async function logout() {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">◎</span>
        <span>Studio OS</span>
      </div>
      <nav class="nav">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="active"
          exact-active-class="active"
        >
          <i :class="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="main">
      <header class="topbar">
        <span class="user" v-if="auth.user">
          {{ auth.user.full_name ?? auth.user.email }}
        </span>
        <Button label="Abmelden" icon="pi pi-sign-out" text @click="logout" />
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: #f9fafb;
}
.sidebar {
  width: 240px;
  background: #0f172a;
  color: #e2e8f0;
  display: flex;
  flex-direction: column;
  padding: 1rem 0.75rem;
  position: sticky;
  top: 0;
  height: 100vh;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.15rem;
  padding: 0.5rem 0.75rem 1.25rem;
}
.logo {
  color: #10b981;
  font-size: 1.4rem;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  overflow-y: auto;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.92rem;
  transition: background 0.15s;
}
.nav-item:hover {
  background: #1e293b;
}
.nav-item.active {
  background: #10b981;
  color: #fff;
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.user {
  color: #475569;
  font-size: 0.9rem;
}
.content {
  padding: 1.75rem;
  flex: 1;
}
</style>
