import { api } from './client'
import type {
  AttendanceStatus,
  CheckIn,
  MemberPass,
  TrainingDashboard,
  TrainingHours,
} from '@/types'

// --- Check-in ---
export async function getMemberPass(memberId: string): Promise<MemberPass> {
  const { data } = await api.get<MemberPass>(`/checkin/pass/${memberId}`)
  return data
}

export async function checkInQr(payload: {
  qr_payload: string
  session_id?: string | null
  device_id?: string | null
}): Promise<CheckIn> {
  const { data } = await api.post<CheckIn>('/checkin/qr', payload)
  return data
}

export async function checkInManual(payload: {
  member_id: string
  session_id?: string | null
}): Promise<CheckIn> {
  const { data } = await api.post<CheckIn>('/checkin/manual', payload)
  return data
}

// --- Attendance ---
export async function setAttendance(
  sessionId: string,
  payload: { member_id: string; status: AttendanceStatus },
): Promise<unknown> {
  const { data } = await api.put(`/attendance/session/${sessionId}`, payload)
  return data
}

// --- Training ---
export async function getTrainingDashboard(
  traineeId: string,
): Promise<TrainingDashboard> {
  const { data } = await api.get<TrainingDashboard>(
    `/training/dashboard/${traineeId}`,
  )
  return data
}

export async function listTrainingHours(
  traineeId: string,
): Promise<TrainingHours[]> {
  const { data } = await api.get<TrainingHours[]>(`/training/hours/${traineeId}`)
  return data
}

export async function logTrainingHours(payload: {
  trainee_id: string
  area: string
  hours: number
  entry_date: string
  note?: string | null
}): Promise<TrainingHours> {
  const { data } = await api.post<TrainingHours>('/training/hours', payload)
  return data
}

export function trainingCsvUrl(traineeId: string): string {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
  return `${base}/training/export/${traineeId}.csv`
}
