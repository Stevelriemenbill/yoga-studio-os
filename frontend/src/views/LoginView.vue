<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Message from 'primevue/message'

import { useI18n } from 'vue-i18n'

import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const tenantSlug = ref('')
const email = ref('')
const password = ref('')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  error.value = null
  loading.value = true
  try {
    await auth.login({
      tenant_slug: tenantSlug.value.trim(),
      email: email.value.trim(),
      password: password.value,
    })
    const redirect = (route.query.redirect as string) || '/'
    await router.push(redirect)
  } catch (e: unknown) {
    error.value = extractError(e)
  } finally {
    loading.value = false
  }
}

function extractError(e: unknown): string {
  const err = e as { response?: { data?: { detail?: string } } }
  return err.response?.data?.detail ?? t('auth.login.failed')
}
</script>

<template>
  <div class="auth-page">
    <Card class="auth-card">
      <template #title>{{ t('auth.login.title') }}</template>
      <template #subtitle>{{ t('common.appName') }}</template>
      <template #content>
        <form class="auth-form" @submit.prevent="submit">
          <label>
            {{ t('auth.studioSlug') }}
            <InputText v-model="tenantSlug" placeholder="zen-flow" autocomplete="organization" />
          </label>
          <label>
            {{ t('auth.email') }}
            <InputText v-model="email" type="email" autocomplete="email" />
          </label>
          <label>
            {{ t('auth.password') }}
            <Password v-model="password" :feedback="false" toggle-mask fluid />
          </label>
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <Button type="submit" :label="t('auth.login.title')" :loading="loading" />
          <RouterLink to="/register">{{ t('auth.login.registerLink') }}</RouterLink>
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
  max-width: 400px;
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
