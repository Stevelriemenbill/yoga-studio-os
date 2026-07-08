import { api } from './client'
import type { Booking, Course, MemberPass, SessionWithStats, Member } from '@/types'

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
