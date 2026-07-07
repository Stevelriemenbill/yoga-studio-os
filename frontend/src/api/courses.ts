import { api } from './client'
import type { Course, CourseSession, Room } from '@/types'

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
