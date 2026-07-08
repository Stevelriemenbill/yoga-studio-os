import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import * as authApi from '@/api/auth'
import { configureAuthHandlers, setTokens } from '@/api/client'
import type { LoginRequest, StudioRegistration, User } from '@/types'

const ACCESS_KEY = 'studio_os_access'
const REFRESH_KEY = 'studio_os_refresh'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem(ACCESS_KEY))
  const refreshToken = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<User | null>(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value)

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
    user.value = result.user
  }

  /** Establish a session from tokens obtained out-of-band (e.g. invite accept). */
  function applySession(
    tokens: { access_token: string; refresh_token: string },
    nextUser: User,
  ): void {
    persist(tokens.access_token, tokens.refresh_token)
    user.value = nextUser
    initialized.value = true
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
    login,
    register,
    applySession,
    logout,
    loadUser,
    initialize,
  }
})
