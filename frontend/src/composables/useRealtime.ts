import { onUnmounted, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

export interface LiveEvent {
  tenant_id: string
  type: string
  payload: Record<string, unknown>
  ts: string
}

function wsBaseUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
  return base.replace(/^http/, 'ws')
}

/**
 * Subscribe to the tenant live-event stream. Automatically reconnects with
 * backoff and cleans up on component unmount.
 */
export function useRealtime(onEvent: (event: LiveEvent) => void) {
  const auth = useAuthStore()
  const connected = ref(false)
  let socket: WebSocket | null = null
  let retry = 0
  let stopped = false
  let timer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    if (stopped || !auth.accessToken) return
    socket = new WebSocket(`${wsBaseUrl()}/ws?token=${auth.accessToken}`)

    socket.onopen = () => {
      connected.value = true
      retry = 0
    }
    socket.onmessage = (evt) => {
      try {
        onEvent(JSON.parse(evt.data) as LiveEvent)
      } catch {
        // ignore malformed frames
      }
    }
    socket.onclose = () => {
      connected.value = false
      if (!stopped) {
        retry += 1
        const delay = Math.min(1000 * 2 ** retry, 30000)
        timer = setTimeout(connect, delay)
      }
    }
    socket.onerror = () => socket?.close()
  }

  connect()

  onUnmounted(() => {
    stopped = true
    if (timer) clearTimeout(timer)
    socket?.close()
  })

  return { connected }
}
