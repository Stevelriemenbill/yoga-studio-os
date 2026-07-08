import { api } from './client'
import type { UserRole } from '@/types'

export interface StaffListEntry {
  kind: 'user' | 'invite'
  id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  status: string
}

export interface StaffInviteRead {
  id: string
  email: string
  full_name: string | null
  role: UserRole
  status: string
  created_at: string
  accepted_at: string | null
}

export interface StaffInviteResult {
  invite: StaffInviteRead
  invite_url: string
  email_delivered: boolean
}

export type StaffInviteRole = 'teacher' | 'studio_manager' | 'reception'

export async function listStaff(): Promise<StaffListEntry[]> {
  const { data } = await api.get<StaffListEntry[]>('/users')
  return data
}

export async function inviteStaff(payload: {
  email: string
  full_name?: string
  role: StaffInviteRole
}): Promise<StaffInviteResult> {
  const { data } = await api.post<StaffInviteResult>('/users/invite', payload)
  return data
}

export async function revokeStaffInvite(inviteId: string): Promise<void> {
  await api.delete(`/users/invite/${inviteId}`)
}
