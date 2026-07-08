<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

import { useAuthStore } from '@/stores/auth'
import { NAV_GROUPS, canAccess, type NavGroup } from '@/config/navigation'

const auth = useAuthStore()
const router = useRouter()

const ROLE_LABELS: Record<string, string> = {
  studio_admin: 'Studio-Admin',
  studio_manager: 'Manager',
  teacher: 'Lehrkraft',
  reception: 'Empfang',
  member: 'Mitglied',
  trainee: 'Auszubildende:r',
}

const roleLabel = computed(() =>
  auth.user ? (ROLE_LABELS[auth.user.role] ?? auth.user.role) : '',
)

const displayName = computed(
  () => auth.user?.full_name ?? auth.user?.email ?? '',
)

const initials = computed(() => {
  const name = auth.user?.full_name ?? auth.user?.email ?? '?'
  return name
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
})

// Only groups that have at least one item visible to the current role.
const visibleGroups = computed<NavGroup[]>(() => {
  const role = auth.user?.role
  return NAV_GROUPS.map((g) => ({
    label: g.label,
    items: g.items.filter((i) => canAccess(i, role)),
  })).filter((g) => g.items.length > 0)
})

const pageTitle = computed(() => {
  const path = router.currentRoute.value.path
  for (const g of NAV_GROUPS) {
    const match = g.items.find((i) => i.to === path)
    if (match) return match.label
  }
  return 'Studio OS'
})

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
        <div v-for="group in visibleGroups" :key="group.label" class="nav-group">
          <span class="nav-group__label">{{ group.label }}</span>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-item"
            active-class="active"
            exact-active-class="active"
            v-tooltip.right="item.hint"
          >
            <i :class="item.icon" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>

      <div class="sidebar__footer" v-if="auth.user">
        <div class="user-card">
          <span class="avatar">{{ initials }}</span>
          <span class="user-card__meta">
            <span class="user-card__name">{{ displayName }}</span>
            <span class="user-card__role">{{ roleLabel }}</span>
          </span>
        </div>
        <Button
          class="logout-btn"
          label="Abmelden"
          icon="pi pi-sign-out"
          severity="secondary"
          text
          @click="logout"
        />
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <h1 class="page-title">{{ pageTitle }}</h1>
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
  background: #f8fafc;
}
.sidebar {
  width: 256px;
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
  padding: 0.5rem 0.75rem 1rem;
}
.logo {
  color: #10b981;
  font-size: 1.4rem;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
  overflow-y: auto;
  flex: 1;
  padding-top: 0.25rem;
}
.nav-group {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.nav-group__label {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
  padding: 0 0.75rem 0.35rem;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.92rem;
  transition: background 0.15s, color 0.15s;
}
.nav-item i {
  width: 1.1rem;
  text-align: center;
}
.nav-item:hover {
  background: #1e293b;
  color: #f1f5f9;
}
.nav-item.active {
  background: #10b981;
  color: #fff;
  font-weight: 600;
}
.sidebar__footer {
  border-top: 1px solid #1e293b;
  padding-top: 0.75rem;
  margin-top: 0.5rem;
}
.user-card {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.35rem 0.75rem 0.6rem;
}
.avatar {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: #10b981;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 700;
  flex-shrink: 0;
}
.user-card__meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.user-card__name {
  font-size: 0.85rem;
  color: #f1f5f9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-card__role {
  font-size: 0.72rem;
  color: #94a3b8;
}
.logout-btn {
  width: 100%;
  justify-content: flex-start;
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
  gap: 1rem;
  padding: 0 1.75rem;
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.page-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}
.content {
  padding: 1.75rem;
  flex: 1;
}
</style>
