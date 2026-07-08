import { api } from './client'
import type {
  Booking,
  Course,
  MemberPass,
  ParticipationHistory,
  SessionWithStats,
  Member,
  StudioEvent,
  EventRegistration,
} from '@/types'

/** Load the schedule the current member can browse and book. */
export async function listSchedule(params?: {
  start?: string
  end?: string
}): Promise<SessionWithStats[]> {
  const { data } = await api.get<SessionWithStats[]>('/sessions', { params })
  return data
}

/** Courses (used to resolve course names for the schedule). */
export async function listCourses(): Promise<Course[]> {
  const { data } = await api.get<Course[]>('/courses')
  return data
}

/** The member profile linked to the current login. */
export async function myProfile(): Promise<Member> {
  const { data } = await api.get<Member>('/me/profile')
  return data
}

/** All of the current member's bookings. */
export async function myBookings(): Promise<Booking[]> {
  const { data } = await api.get<Booking[]>('/me/bookings')
  return data
}

/** The current member's participation history and accumulated hours. */
export async function myParticipation(): Promise<ParticipationHistory> {
  const { data } = await api.get<ParticipationHistory>('/me/participation')
  return data
}

/** Book the current member into a session (member id derived server-side). */
export async function bookSession(sessionId: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/me/bookings/${sessionId}`)
  return data
}

/** Cancel one of the current member's own bookings. */
export async function cancelMyBooking(bookingId: string): Promise<Booking> {
  const { data } = await api.post<Booking>(`/me/bookings/${bookingId}/cancel`)
  return data
}

/** The current member's signed QR check-in pass. */
export async function myPass(): Promise<MemberPass> {
  const { data } = await api.get<MemberPass>('/me/pass')
  return data
}

/** Published events the current member can register for. */
export async function listMyEvents(): Promise<StudioEvent[]> {
  const { data } = await api.get<StudioEvent[]>('/me/events')
  return data
}

/** The current member's own event registrations. */
export async function myEventRegistrations(): Promise<EventRegistration[]> {
  const { data } = await api.get<EventRegistration[]>('/me/events/registrations')
  return data
}

/** Register the current member for a published event. */
export async function registerForEvent(
  eventId: string,
): Promise<EventRegistration> {
  const { data } = await api.post<EventRegistration>(
    `/me/events/${eventId}/register`,
  )
  return data
}

/** Cancel one of the current member's own event registrations. */
export async function cancelMyEventRegistration(
  registrationId: string,
): Promise<EventRegistration> {
  const { data } = await api.post<EventRegistration>(
    `/me/events/registrations/${registrationId}/cancel`,
  )
  return data
}
