import { createI18n } from 'vue-i18n'

import de from './locales/de'
import en from './locales/en'

export const SUPPORTED_LOCALES = ['de', 'en'] as const
export type AppLocale = (typeof SUPPORTED_LOCALES)[number]

export const DEFAULT_LOCALE: AppLocale = 'de'
const STORAGE_KEY = 'studio-os.locale'

function isSupported(value: string | null): value is AppLocale {
  return value !== null && (SUPPORTED_LOCALES as readonly string[]).includes(value)
}

function detectLocale(): AppLocale {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (isSupported(stored)) return stored
  const browser = navigator.language?.slice(0, 2).toLowerCase() ?? ''
  if (isSupported(browser)) return browser
  return DEFAULT_LOCALE
}

export const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: { de, en },
})

export function setLocale(locale: AppLocale): void {
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.setAttribute('lang', locale)
}

// Ensure <html lang> reflects the initial locale.
document.documentElement.setAttribute('lang', i18n.global.locale.value)
