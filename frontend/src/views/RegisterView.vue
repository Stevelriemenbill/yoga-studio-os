<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Message from 'primevue/message'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const studioName = ref('')
const studioSlug = ref('')
const adminFullName = ref('')
const adminEmail = ref('')
const adminPassword = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function onNameInput() {
  if (!studioSlug.value) studioSlug.value = slugify(studioName.value)
}

async function submit() {
  error.value = null
  loading.value = true
  try {
    await auth.register({
      studio_name: studioName.value.trim(),
      studio_slug: slugify(studioSlug.value),
      admin_email: adminEmail.value.trim(),
      admin_password: adminPassword.value,
      admin_full_name: adminFullName.value.trim() || null,
    })
    await router.push('/')
  } catch (e: unknown) {
    error.value = extractError(e)
  } finally {
    loading.value = false
  }
}

function extractError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: unknown } } }
  const detail = err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  return 'Registrierung fehlgeschlagen'
}
</script>

<template>
  <div class="auth-page">
    <Card class="auth-card">
      <template #title>Studio registrieren</template>
      <template #subtitle>Erstelle dein Studio und Admin-Konto</template>
      <template #content>
        <form class="auth-form" @submit.prevent="submit">
          <label>
            Studio-Name
            <InputText v-model="studioName" @input="onNameInput" />
          </label>
          <label>
            Studio-Kürzel (URL)
            <InputText v-model="studioSlug" placeholder="zen-flow" />
          </label>
          <label>
            Dein Name
            <InputText v-model="adminFullName" />
          </label>
          <label>
            E-Mail
            <InputText v-model="adminEmail" type="email" autocomplete="email" />
          </label>
          <label>
            Passwort (min. 8 Zeichen)
            <Password v-model="adminPassword" toggle-mask fluid />
          </label>
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <Button type="submit" label="Studio erstellen" :loading="loading" />
          <RouterLink to="/login">Zurück zur Anmeldung</RouterLink>
        </form>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  padding: 1rem;
}
.auth-card {
  width: 100%;
  max-width: 440px;
}
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.auth-form label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  font-weight: 500;
}
</style>
