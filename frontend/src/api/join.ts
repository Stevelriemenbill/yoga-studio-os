import { api } from './client'

export interface PublicStudio {
  name: string
  slug: string
}

export interface JoinRequestPayload {
  first_name: string
  last_name: string
  email: string
  phone?: string
  message?: string
}

export interface JoinRequest {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string | null
  message: string | null
  status: 'pending' | 'approved' | 'declined'
  created_at: string
  reviewed_at: string | null
}

export interface ApproveResult {
  invite_url: string
  token: string
  email_delivered: boolean
}

export async function getPublicStudio(slug: string): Promise<PublicStudio> {
  const { data } = await api.get<PublicStudio>(
    `/join/${encodeURIComponent(slug)}`,
  )
  return data
}

export async function submitJoinRequest(
  slug: string,
  payload: JoinRequestPayload,
): Promise<JoinRequest> {
  const { data } = await api.post<JoinRequest>(
    `/join/${encodeURIComponent(slug)}`,
    payload,
  )
  return data
}

export async function listJoinRequests(): Promise<JoinRequest[]> {
  const { data } = await api.get<JoinRequest[]>('/join-requests')
  return data
}

export async function approveJoinRequest(id: string): Promise<ApproveResult> {
  const { data } = await api.post<ApproveResult>(`/join-requests/${id}/approve`)
  return data
}

export async function declineJoinRequest(id: string): Promise<JoinRequest> {
  const { data } = await api.post<JoinRequest>(`/join-requests/${id}/decline`)
  return data
}
