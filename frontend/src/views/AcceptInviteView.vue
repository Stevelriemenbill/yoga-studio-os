<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Password from 'primevue/password'
import Message from 'primevue/message'

import { acceptInvite, previewInvite, type InvitedMember } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const token = String(route.params.token ?? '')
const loading = ref(true)
const invite = ref<InvitedMember | null>(null)
const password = ref('')
const confirm = ref('')
const error = ref<string | null>(null)
const submitting = ref(false)

function extractError(e: unknown, fallback: string): string {
  const err = e as { response?: { data?: { detail?: string } } }
  return err.response?.data?.detail ?? fallback
}

onMounted(async () => {
  try {
    invite.value = await previewInvite(token)
  } catch (e: unknown) {
    error.value = extractError(e, 'Diese Einladung ist ungültig oder abgelaufen.')
  } finally {
    loading.value = false
  }
})

async function submit() {
  error.value = null
  if (password.value.length < 8) {
    error.value = 'Das Passwort muss mindestens 8 Zeichen lang sein.'
    return
  }
  if (password.value !== confirm.value) {
    error.value = 'Die Passwörter stimmen nicht überein.'
    return
  }
  submitting.value = true
  try {
    const result = await acceptInvite(token, password.value)
    auth.applySession(result.token, result.user)
    await router.push('/')
  } catch (e: unknown) {
    error.value = extractError(e, 'Konto konnte nicht aktiviert werden.')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <Card class="auth-card">
      <template #title>Konto aktivieren</template>
      <template #subtitle>
        {{ invite ? invite.studio_name : 'Studio OS' }}
      </template>
      <template #content>
        <p v-if="loading">Einladung wird geprüft…</p>

        <Message
          v-else-if="!invite"
          severity="error"
          :closable="false"
        >
          {{ error ?? 'Einladung ungültig.' }}
        </Message>

        <form v-else class="auth-form" @submit.prevent="submit">
          <p class="welcome">
            Hallo <strong>{{ invite.first_name }}</strong>, lege ein Passwort fest,
            um dein Konto ({{ invite.email }}) zu aktivieren.
          </p>
          <label>
            Passwort
            <Password v-model="password" toggle-mask fluid />
          </label>
          <label>
            Passwort bestätigen
            <Password v-model="confirm" :feedback="false" toggle-mask fluid />
          </label>
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <Button type="submit" label="Konto aktivieren" :loading="submitting" />
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
.welcome {
  margin: 0;
  color: #475569;
  font-size: 0.92rem;
}
</style>
