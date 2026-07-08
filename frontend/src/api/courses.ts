import { api } from './client'
import type { Course, CourseSession, Room, SessionWithStats } from '@/types'

// --- Rooms ---
export async function listRooms(): Promise<Room[]> {
  const { data } = await api.get<Room[]>('/rooms')
  return data
}

export async function createRoom(payload: {
  name: string
  capacity?: number
}): Promise<Room> {
  const { data } = await api.post<Room>('/rooms', payload)
  return data
}

// --- Courses ---
export interface CoursePayload {
  name: string
  description?: string | null
  category?: string | null
  level?: Course['level']
  room_id?: string | null
  teacher_id?: string | null
  max_participants?: number
  min_participants?: number
  duration_minutes?: number
}

export async function listCourses(): Promise<Course[]> {
  const { data } = await api.get<Course[]>('/courses')
  return data
}

export async function getCourse(id: string): Promise<Course> {
  const { data } = await api.get<Course>(`/courses/${id}`)
  return data
}

export async function createCourse(payload: CoursePayload): Promise<Course> {
  const { data } = await api.post<Course>('/courses', payload)
  return data
}

export async function updateCourse(
  id: string,
  payload: Partial<CoursePayload>,
): Promise<Course> {
  const { data } = await api.patch<Course>(`/courses/${id}`, payload)
  return data
}

export async function deleteCourse(id: string): Promise<void> {
  await api.delete(`/courses/${id}`)
}

// --- Sessions ---
export interface SessionPayload {
  course_id: string
  starts_at: string
  teacher_id?: string | null
  room_id?: string | null
  capacity?: number | null
}

export async function createSession(
  courseId: string,
  payload: SessionPayload,
): Promise<CourseSession> {
  const { data } = await api.post<CourseSession>(
    `/courses/${courseId}/sessions`,
    payload,
  )
  return data
}

// --- Recurring schedule ---
export interface RecurrencePayload {
  course_id: string
  /** Weekdays: 0=Mon .. 6=Sun. */
  weekdays: number[]
  /** "HH:MM:SS" local time. */
  start_time: string
  /** "YYYY-MM-DD". */
  start_date: string
  /** Provide exactly one of end_date or count. */
  end_date?: string
  count?: number
}

/** Generate many sessions for a course from a weekly recurrence. */
export async function scheduleRecurring(
  courseId: string,
  payload: RecurrencePayload,
): Promise<CourseSession[]> {
  const { data } = await api.post<CourseSession[]>(
    `/courses/${courseId}/schedule`,
    payload,
  )
  return data
}

/** List sessions (with booking stats) in an optional date range. */
export async function listSessions(params?: {
  start?: string
  end?: string
}): Promise<SessionWithStats[]> {
  const { data } = await api.get<SessionWithStats[]>('/sessions', { params })
  return data
}
