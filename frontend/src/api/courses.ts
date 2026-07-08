import { api } from './client'
import type {
  Course,
  CourseAttachment,
  CourseSession,
  Room,
  SessionWithStats,
} from '@/types'

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
  counts_for_training?: boolean
  location?: string | null
  is_online?: boolean
  online_url?: string | null
  registration_info?: string | null
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

// --- Course attachments ---
export async function listCourseAttachments(
  courseId: string,
): Promise<CourseAttachment[]> {
  const { data } = await api.get<CourseAttachment[]>(
    `/courses/${courseId}/attachments`,
  )
  return data
}

export async function uploadCourseAttachment(
  courseId: string,
  file: File,
): Promise<CourseAttachment> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<CourseAttachment>(
    `/courses/${courseId}/attachments`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function deleteCourseAttachment(
  courseId: string,
  attachmentId: string,
): Promise<void> {
  await api.delete(`/courses/${courseId}/attachments/${attachmentId}`)
}

// --- Sessions ---
export interface SessionPayload {
  course_id: string
  starts_at: string
  teacher_id?: string | null
  room_id?: string | null
  capacity?: number | null
  location?: string | null
  is_online?: boolean | null
  online_url?: string | null
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

export async function cancelSession(
  sessionId: string,
  reason?: string,
): Promise<SessionWithStats> {
  const { data } = await api.post<SessionWithStats>(
    `/sessions/${sessionId}/cancel`,
    { reason: reason || null },
  )
  return data
}

/** Fields that can be changed on a single session. */
export interface SessionUpdatePayload {
  /** Full ISO datetime; replaces the session's start (end shifts by duration). */
  starts_at?: string
  teacher_id?: string | null
  room_id?: string | null
  capacity?: number | null
  overbooking_allowance?: number | null
  location?: string | null
  is_online?: boolean | null
  online_url?: string | null
}

/** Update a single session (staff only). */
export async function updateSession(
  sessionId: string,
  payload: SessionUpdatePayload,
): Promise<SessionWithStats> {
  const { data } = await api.patch<SessionWithStats>(
    `/sessions/${sessionId}`,
    payload,
  )
  return data
}

// --- Series (recurrence management) ---
export interface SeriesUpdatePayload {
  /** "HH:MM:SS" local time; shifts the time-of-day of every future session. */
  start_time?: string
  teacher_id?: string | null
  room_id?: string | null
  capacity?: number | null
  location?: string | null
  is_online?: boolean | null
  online_url?: string | null
}

export interface SeriesActionResult {
  series_id: string
  affected: number
}

/** All sessions belonging to a recurrence series. */
export async function listSeriesSessions(
  seriesId: string,
): Promise<SessionWithStats[]> {
  const { data } = await api.get<SessionWithStats[]>(`/series/${seriesId}`)
  return data
}

/** Apply common changes to all future sessions of a series. */
export async function updateSeries(
  seriesId: string,
  payload: SeriesUpdatePayload,
): Promise<SeriesActionResult> {
  const { data } = await api.patch<SeriesActionResult>(
    `/series/${seriesId}`,
    payload,
  )
  return data
}

/** Cancel all future sessions of a series. */
export async function cancelSeries(
  seriesId: string,
  reason?: string,
): Promise<SeriesActionResult> {
  const { data } = await api.post<SeriesActionResult>(
    `/series/${seriesId}/cancel`,
    { reason: reason || null },
  )
  return data
}
