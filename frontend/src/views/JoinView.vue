<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Message from 'primevue/message'

import {
  getPublicStudio,
  submitJoinRequest,
  type PublicStudio,
} from '@/api/join'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const route = useRoute()

const slug = String(route.params.slug ?? '')
const loading = ref(true)
const studio = ref<PublicStudio | null>(null)
const submitting = ref(false)
const submitted = ref(false)
const error = ref<string | null>(null)

const form = ref({
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  message: '',
})

function extractError(e: unknown, fallback: string): string {
  const err = e as { response?: { data?: { detail?: string } } }
  return err.response?.data?.detail ?? fallback
}

onMounted(async () => {
  try {
    studio.value = await getPublicStudio(slug)
  } catch (e: unknown) {
    error.value = extractError(e, t('join.studioNotFound'))
  } finally {
    loading.value = false
  }
})

async function submit() {
  error.value = null
  if (!form.value.first_name || !form.value.last_name || !form.value.email) {
    error.value = t('join.errors.required')
    return
  }
  submitting.value = true
  try {
    await submitJoinRequest(slug, {
      first_name: form.value.first_name,
      last_name: form.value.last_name,
      email: form.value.email,
      phone: form.value.phone || undefined,
      message: form.value.message || undefined,
    })
    submitted.value = true
  } catch (e: unknown) {
    error.value = extractError(e, t('join.errors.submitFailed'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="join-page">
    <Card class="join-card">
      <template #title>{{ t('join.title') }}</template>
      <template #subtitle>
        {{ studio ? studio.name : t('common.appName') }}
      </template>
      <template #content>
        <p v-if="loading">{{ t('join.loading') }}</p>

        <Message v-else-if="!studio" severity="error" :closable="false">
          {{ error ?? t('join.studioNotFound') }}
        </Message>

        <Message v-else-if="submitted" severity="success" :closable="false">
          {{ t('join.success', { studio: studio.name }) }}
        </Message>

        <form v-else class="join-form" @submit.prevent="submit">
          <p class="intro">{{ t('join.intro', { studio: studio.name }) }}</p>
          <div class="row">
            <label>
              {{ t('join.form.firstName') }}
              <InputText v-model="form.first_name" fluid />
            </label>
            <label>
              {{ t('join.form.lastName') }}
              <InputText v-model="form.last_name" fluid />
            </label>
          </div>
          <label>
            {{ t('join.form.email') }}
            <InputText v-model="form.email" type="email" fluid />
          </label>
          <label>
            {{ t('join.form.phone') }}
            <InputText v-model="form.phone" fluid />
          </label>
          <label>
            {{ t('join.form.message') }}
            <Textarea v-model="form.message" rows="4" autoResize fluid />
          </label>
          <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
          <Button type="submit" :label="t('join.form.submit')" :loading="submitting" />
        </form>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.join-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  padding: 1rem;
}
.join-card {
  width: 100%;
  max-width: 460px;
}
.join-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}
.join-form .row {
  display: flex;
  gap: 0.75rem;
}
.join-form .row label {
  flex: 1;
}
.join-form label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.9rem;
  font-weight: 500;
}
.intro {
  margin: 0 0 0.5rem;
  color: #475569;
  font-size: 0.92rem;
}
</style>
