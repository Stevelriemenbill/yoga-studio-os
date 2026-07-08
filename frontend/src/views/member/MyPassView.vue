<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

import { myPass } from '@/api/me'
import type { MemberPass } from '@/types'

const { t } = useI18n()

const pass = ref<MemberPass | null>(null)
const loading = ref(false)
const error = ref('')

const qrImageUrl = computed(() => {
  if (!pass.value) return ''
  const data = encodeURIComponent(pass.value.qr_payload)
  return `https://api.qrserver.com/v1/create-qr-code/?size=280x280&data=${data}`
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    pass.value = await myPass()
  } catch {
    error.value = t('myArea.loadError')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <h1>{{ t('myArea.passTitle') }}</h1>
    <p class="lead">{{ t('myArea.passLead') }}</p>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">{{ t('common.loading') }}</p>

    <div v-else-if="pass" class="pass-card">
      <img :src="qrImageUrl" :alt="t('myArea.passTitle')" width="280" height="280" />
      <code class="payload">{{ pass.qr_payload }}</code>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 600px;
  margin: 0 auto;
  text-align: center;
}
.lead {
  color: #6b7280;
  margin-bottom: 1.5rem;
}
.error {
  color: #dc2626;
}
.pass-card {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}
.payload {
  font-size: 0.7rem;
  color: #9ca3af;
  word-break: break-all;
  max-width: 280px;
}
</style>
