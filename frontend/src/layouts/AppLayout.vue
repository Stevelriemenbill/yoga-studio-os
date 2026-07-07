<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from 'primevue/button'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function logout() {
  auth.logout()
  await router.push('/login')
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <span class="logo">◎</span>
        Studio OS
      </div>
      <Button label="Abmelden" icon="pi pi-sign-out" text @click="logout" />
    </header>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: #f9fafb;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.1rem;
}
.logo {
  color: #10b981;
  font-size: 1.4rem;
}
.content {
  padding: 2rem 1.5rem;
}
</style>
