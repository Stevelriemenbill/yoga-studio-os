import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as authApi from '@/api/auth'
import { configureAuthHandlers, setTokens } from '@/api/client'
import {
  applyTheme,
  DEFAULT_MODE,
  DEFAULT_PRESET,
  type ThemeMode,
  type ThemePreset,
} from '@/theme'
import type { LoginRequest, Me, StudioRegistration, User } from '@/types'

const ACCESS_KEY = 'studio_os_access'
const REFRESH_KEY = 'studio_os_refresh'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(ACCESS_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<Me | null>(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value)
  const studioName = computed(() => user.value?.studio_name ?? '')
  const studioSlug = computed(() => user.value?.studio_slug ?? '')
  const isAdmin = computed(() => user.value?.role === 'studio_admin')

  /** Apply the studio theme carried by the `/auth/me` payload. */
  function applyUserTheme(): void {
    if (!user.value) return
    applyTheme(
      (user.value.theme_preset as ThemePreset) || DEFAULT_PRESET,
      (user.value.theme_mode as ThemeMode) || DEFAULT_MODE,
    )
  }

  function persist(access: string | null, refresh: string | null): void {
    accessToken.value = access
    refreshToken.value = refresh
    setTokens(access, refresh)
    if (access) localStorage.setItem(ACCESS_KEY, access)
    else localStorage.removeItem(ACCESS_KEY)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    else localStorage.removeItem(REFRESH_KEY)
  }

  function logout(): void {
    user.value = null
    persist(null, null)
  }

  async function loadUser(): Promise<void> {
    if (!accessToken.value) return
    try {
      user.value = await authApi.fetchMe()
      applyUserTheme()
    } catch {
      logout()
    }
  }

  async function login(payload: LoginRequest): Promise<void> {
    const token = await authApi.login(payload)
    persist(token.access_token, token.refresh_token)
    await loadUser()
  }

  async function register(payload: StudioRegistration): Promise<void> {
    const result = await authApi.register(payload)
    persist(result.token.access_token, result.token.refresh_token)
    // Registration returns a plain user; fetch full studio context + theme.
    await loadUser()
  }

  /** Establish a session from tokens obtained out-of-band (e.g. invite accept). */
  async function applySession(
    tokens: { access_token: string; refresh_token: string },
    _nextUser: User,
  ): Promise<void> {
    persist(tokens.access_token, tokens.refresh_token)
    await loadUser()
    initialized.value = true
  }

  /** Studio admin: change the studio-wide theme (persisted server-side). */
  async function setTheme(preset: ThemePreset, mode: ThemeMode): Promise<void> {
    const saved = await authApi.updateTheme({
      theme_preset: preset,
      theme_mode: mode,
    })
    if (user.value) {
      user.value.theme_preset = saved.theme_preset
      user.value.theme_mode = saved.theme_mode
    }
    applyTheme(preset, mode)
  }

  async function initialize(): Promise<void> {
    if (initialized.value) return
    setTokens(accessToken.value, refreshToken.value)
    configureAuthHandlers({
      onAuthFailure: () => logout(),
      onTokenRefresh: (access, refresh) => persist(access, refresh),
    })
    await loadUser()
    initialized.value = true
  }

  return {
    accessToken,
    refreshToken,
    user,
    initialized,
    isAuthenticated,
    studioName,
    studioSlug,
    isAdmin,
    login,
    register,
    applySession,
    logout,
    loadUser,
    setTheme,
    initialize,
  }
})
