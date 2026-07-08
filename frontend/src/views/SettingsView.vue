<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'

import { useAuthStore } from '@/stores/auth'
import { SUPPORTED_LOCALES, setLocale, type AppLocale } from '@/i18n'

const auth = useAuthStore()
const { t, locale } = useI18n()

const selectedLocale = ref<AppLocale>(locale.value as AppLocale)
const saved = ref(false)

const languageOptions = SUPPORTED_LOCALES.map((code) => ({
  value: code,
  label: t(`languages.${code}`),
}))

function onLanguageChange(value: AppLocale) {
  setLocale(value)
  selectedLocale.value = value
  saved.value = true
  window.setTimeout(() => {
    saved.value = false
  }, 2500)
}
</script>

<template>
  <div class="page">
    <h1>{{ t('settings.title') }}</h1>

    <Card class="block">
      <template #title>{{ t('settings.languageSection') }}</template>
      <template #content>
        <div class="field">
          <label for="language">{{ t('settings.languageLabel') }}</label>
          <Dropdown
            id="language"
            v-model="selectedLocale"
            :options="languageOptions"
            optionLabel="label"
            optionValue="value"
            @change="onLanguageChange($event.value)"
          />
          <small class="hint">{{ t('settings.languageHint') }}</small>
          <small v-if="saved" class="saved">{{ t('settings.languageSaved') }}</small>
        </div>
      </template>
    </Card>

    <Card v-if="auth.user" class="block">
      <template #title>{{ t('settings.account') }}</template>
      <template #content>
        <p><strong>{{ t('settings.email') }}:</strong> {{ auth.user.email }}</p>
        <p>
          <strong>{{ t('settings.role') }}:</strong>
          <Tag :value="t(`roles.${auth.user.role}`)" severity="success" />
        </p>
      </template>
    </Card>
  </div>
</template>

<style scoped>
.page {
  max-width: 640px;
  margin: 0 auto;
}
.block {
  margin-bottom: 1rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  max-width: 320px;
}
.field label {
  font-size: 0.85rem;
  color: #374151;
  font-weight: 600;
}
.hint {
  color: #6b7280;
}
.saved {
  color: #10b981;
  font-weight: 600;
}
</style>
