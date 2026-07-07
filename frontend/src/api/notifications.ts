import { api } from './client'
import type { AppNotification, NotificationChannel } from '@/types'

export async function listNotifications(): Promise<AppNotification[]> {
  const { data } = await api.get<AppNotification[]>('/notifications')
  return data
}

export async function createNotification(payload: {
  channel: NotificationChannel
  body: string
  member_id?: string | null
  subject?: string | null
  scheduled_for?: string | null
}): Promise<AppNotification> {
  const { data } = await api.post<AppNotification>('/notifications', payload)
  return data
}

export async function sendReminders(payload: {
  session_id: string
  channel?: NotificationChannel
}): Promise<AppNotification[]> {
  const { data } = await api.post<AppNotification[]>(
    '/notifications/reminders',
    payload,
  )
  return data
}

export async function processNotifications(): Promise<{ sent: number }> {
  const { data } = await api.post<{ sent: number }>('/notifications/process')
  return data
}
