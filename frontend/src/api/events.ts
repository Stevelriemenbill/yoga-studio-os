import { api } from './client'
import type { EventRegistration, EventType, StudioEvent } from '@/types'

export interface EventPayload {
  name: string
  description?: string | null
  type?: EventType
  starts_at: string
  ends_at: string
  location?: string | null
  capacity?: number
  price_cents?: number
  requires_deposit?: boolean
  deposit_cents?: number
}

export async function listEvents(): Promise<StudioEvent[]> {
  const { data } = await api.get<StudioEvent[]>('/events')
  return data
}

export async function createEvent(payload: EventPayload): Promise<StudioEvent> {
  const { data } = await api.post<StudioEvent>('/events', payload)
  return data
}

export async function updateEvent(
  id: string,
  payload: Partial<EventPayload> & { is_published?: boolean },
): Promise<StudioEvent> {
  const { data } = await api.patch<StudioEvent>(`/events/${id}`, payload)
  return data
}

export async function listRegistrations(
  eventId: string,
): Promise<EventRegistration[]> {
  const { data } = await api.get<EventRegistration[]>(
    `/events/${eventId}/registrations`,
  )
  return data
}

export async function registerForEvent(
  eventId: string,
  memberId: string,
): Promise<EventRegistration> {
  const { data } = await api.post<EventRegistration>(
    `/events/${eventId}/register`,
    { member_id: memberId },
  )
  return data
}

export async function confirmPayment(
  registrationId: string,
  amountCents: number,
): Promise<EventRegistration> {
  const { data } = await api.post<EventRegistration>(
    `/events/registrations/${registrationId}/pay`,
    { amount_cents: amountCents },
  )
  return data
}

export async function cancelRegistration(
  registrationId: string,
): Promise<EventRegistration> {
  const { data } = await api.delete<EventRegistration>(
    `/events/registrations/${registrationId}`,
  )
  return data
}
