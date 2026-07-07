import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export const api: AxiosInstance = axios.create({ baseURL })

let accessToken: string | null = null
let refreshToken: string | null = null
let onAuthFailure: (() => void) | null = null
let onTokenRefresh: ((access: string, refresh: string) => void) | null = null

export function setTokens(access: string | null, refresh: string | null): void {
  accessToken = access
  refreshToken = refresh
}

export function configureAuthHandlers(handlers: {
  onAuthFailure: () => void
  onTokenRefresh: (access: string, refresh: string) => void
}): void {
  onAuthFailure = handlers.onAuthFailure
  onTokenRefresh = handlers.onTokenRefresh
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

let isRefreshing = false

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    // Attempt a single silent refresh on 401 for non-auth endpoints.
    if (
      status === 401 &&
      refreshToken &&
      !original._retry &&
      !original.url?.includes('/auth/')
    ) {
      original._retry = true
      if (!isRefreshing) {
        isRefreshing = true
        try {
          const { data } = await axios.post(`${baseURL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          accessToken = data.access_token
          refreshToken = data.refresh_token
          onTokenRefresh?.(data.access_token, data.refresh_token)
        } catch {
          onAuthFailure?.()
          isRefreshing = false
          return Promise.reject(error)
        }
        isRefreshing = false
      }
      original.headers.Authorization = `Bearer ${accessToken}`
      return api(original)
    }

    return Promise.reject(error)
  },
)
