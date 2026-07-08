import { api } from './client'
import type { CommunityPulse, TeacherReach } from '@/types'

export async function getCommunityPulse(): Promise<CommunityPulse> {
  const { data } = await api.get<CommunityPulse>('/analytics/pulse')
  return data
}

export async function getTeacherReach(): Promise<TeacherReach[]> {
  const { data } = await api.get<TeacherReach[]>('/analytics/teachers')
  return data
}
