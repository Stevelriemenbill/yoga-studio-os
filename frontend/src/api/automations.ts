import { api } from './client'
import type { AutomationRule, AutomationRunResult, AutomationTrigger, NotificationChannel } from '@/types'

export async function listAutomations(): Promise<AutomationRule[]> {
  const { data } = await api.get<AutomationRule[]>('/automations')
  return data
}

export async function createAutomation(payload: {
  name: string
  trigger: AutomationTrigger
  threshold_days?: number
  channel?: NotificationChannel
  message_template: string
  is_active?: boolean
}): Promise<AutomationRule> {
  const { data } = await api.post<AutomationRule>('/automations', payload)
  return data
}

export async function updateAutomation(
  id: string,
  payload: Partial<{
    name: string
    threshold_days: number
    channel: NotificationChannel
    message_template: string
    is_active: boolean
  }>,
): Promise<AutomationRule> {
  const { data } = await api.patch<AutomationRule>(`/automations/${id}`, payload)
  return data
}

export async function runAutomations(): Promise<AutomationRunResult> {
  const { data } = await api.post<AutomationRunResult>('/automations/run')
  return data
}
