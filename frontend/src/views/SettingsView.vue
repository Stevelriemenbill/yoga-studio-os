<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import Tag from 'primevue/tag'
import SelectButton from 'primevue/selectbutton'

import { useAuthStore } from '@/stores/auth'
import { SUPPORTED_LOCALES, setLocale, type AppLocale } from '@/i18n'
import {
  SUPPORTED_THEME_PRESETS,
  SUPPORTED_THEME_MODES,
  presetColor,
  type ThemeMode,
  type ThemePreset,
} from '@/theme'

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

// --- Theme (studio-wide, admin only) ---
const selectedPreset = ref<ThemePreset>(
  (auth.user?.theme_preset as ThemePreset) ?? 'emerald',
)
const selectedMode = ref<ThemeMode>(
  (auth.user?.theme_mode as ThemeMode) ?? 'light',
)
const themeSaved = ref(false)
const themeError = ref('')

const presetOptions = SUPPORTED_THEME_PRESETS.map((value) => ({
  value,
  label: t(`settings.presets.${value}`),
  color: presetColor(value),
}))
const modeOptions = SUPPORTED_THEME_MODES.map((value) => ({
  value,
  label: t(`settings.modes.${value}`),
}))

async function saveTheme() {
  themeError.value = ''
  try {
    await auth.setTheme(selectedPreset.value, selectedMode.value)
    themeSaved.value = true
    window.setTimeout(() => {
      themeSaved.value = false
    }, 2500)
  } catch {
    themeError.value = t('settings.themeError')
  }
}
</script>

<template>
  <div class="page">
    <h1>{{ t('settings.title') }}</h1>

    <Card v-if="auth.isAdmin" class="block">
      <template #title>{{ t('settings.themeSection') }}</template>
      <template #content>
        <p class="hint">{{ t('settings.themeHint') }}</p>

        <div class="field">
          <label>{{ t('settings.themeModeLabel') }}</label>
          <SelectButton
            v-model="selectedMode"
            :options="modeOptions"
            optionLabel="label"
            optionValue="value"
            :allowEmpty="false"
          />
        </div>

        <div class="field">
          <label>{{ t('settings.themePresetLabel') }}</label>
          <div class="swatches">
            <button
              v-for="opt in presetOptions"
              :key="opt.value"
              type="button"
              class="swatch"
              :class="{ selected: selectedPreset === opt.value }"
              :style="{ background: opt.color }"
              :title="opt.label"
              @click="selectedPreset = opt.value"
            >
              <i v-if="selectedPreset === opt.value" class="pi pi-check" />
            </button>
          </div>
        </div>

        <div class="theme-actions">
          <button type="button" class="save-btn" @click="saveTheme">
            {{ t('settings.themeSave') }}
          </button>
          <small v-if="themeSaved" class="saved">{{ t('settings.themeSaved') }}</small>
          <small v-if="themeError" class="error">{{ themeError }}</small>
        </div>
      </template>
    </Card>

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
        <p v-if="auth.studioName">
          <strong>{{ t('settings.studio') }}:</strong> {{ auth.studioName }}
        </p>
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
  margin-bottom: 1rem;
}
.field label {
  font-size: 0.85rem;
  color: #374151;
  font-weight: 600;
}
.hint {
  color: #6b7280;
}
.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.swatch {
  width: 2.2rem;
  height: 2.2rem;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: grid;
  place-items: center;
  color: #fff;
  padding: 0;
  transition: transform 0.1s, box-shadow 0.1s;
}
.swatch:hover {
  transform: scale(1.08);
}
.swatch.selected {
  border-color: #0f172a;
  box-shadow: 0 0 0 2px #fff inset;
}
.theme-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.save-btn {
  background: var(--p-primary-color, #10b981);
  color: var(--p-primary-contrast-color, #fff);
  border: none;
  border-radius: 8px;
  padding: 0.55rem 1.1rem;
  font-weight: 600;
  cursor: pointer;
}
.saved {
  color: #10b981;
  font-weight: 600;
}
.error {
  color: #ef4444;
  font-weight: 600;
}
</style>
