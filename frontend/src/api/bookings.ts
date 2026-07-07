import { api } from './client'
import type { Booking, WaitlistEntry } from '@/types'

export async function createBooking(payload: {
  session_id: string
  member_id: string
  drop_in?: boolean
}): Promise<Booking> {
  const { data } = await api.post<Booking>('/bookings', payload)
  return data
}

export async function listSessionBookings(sessionId: string): Promise<Booking[]> {
  const { data } = await api.get<Booking[]>(`/bookings/session/${sessionId}`)
  return data
}

export async function cancelBooking(bookingId: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/cancel`)
  return data
}

export async function rebookBooking(
  bookingId: string,
  newSessionId: string,
): Promise<Booking> {
  const { data } = await api.post<Booking>(`/bookings/${bookingId}/rebook`, {
    new_session_id: newSessionId,
  })
  return data
}

// --- Waitlist ---
export async function joinWaitlist(payload: {
  session_id: string
  member_id: string
  priority?: number
}): Promise<WaitlistEntry> {
  const { data } = await api.post<WaitlistEntry>('/waitlist', payload)
  return data
}

export async function listWaitlist(sessionId: string): Promise<WaitlistEntry[]> {
  const { data } = await api.get<WaitlistEntry[]>(`/waitlist/session/${sessionId}`)
  return data
}

export async function acceptOffer(entryId: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/waitlist/${entryId}/accept`)
  return data
}

export async function declineOffer(entryId: string): Promise<WaitlistEntry> {
  const { data } = await api.post<WaitlistEntry>(`/waitlist/${entryId}/decline`)
  return data
}
