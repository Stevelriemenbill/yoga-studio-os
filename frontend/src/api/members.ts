import { api } from './client'
import type { Member } from '@/types'

export interface MemberPayload {
  first_name: string
  last_name: string
  email?: string | null
  phone?: string | null
  notes?: string | null
  membership_type?: Member['membership_type']
  membership_valid_until?: string | null
  credits?: number
}

export async function listMembers(): Promise<Member[]> {
  const { data } = await api.get<Member[]>('/members')
  return data
}

export async function getMember(id: string): Promise<Member> {
  const { data } = await api.get<Member>(`/members/${id}`)
  return data
}

export async function createMember(payload: MemberPayload): Promise<Member> {
  const { data } = await api.post<Member>('/members', payload)
  return data
}

export async function updateMember(
  id: string,
  payload: Partial<MemberPayload>,
): Promise<Member> {
  const { data } = await api.patch<Member>(`/members/${id}`, payload)
  return data
}

export async function deleteMember(id: string): Promise<void> {
  await api.delete(`/members/${id}`)
}
