import { api } from './client'
import type {
  Attendance,
  AttendanceStatus,
  CheckIn,
  CohortProgress,
  CohortStatus,
  EnrollmentStatus,
  MemberPass,
  TrainingCohort,
  TrainingDashboard,
  TrainingEnrollment,
  TrainingHours,
  TrainingProgram,
} from '@/types'

// --- Check-in ---
export async function getMemberPass(memberId: string): Promise<MemberPass> {
  const { data } = await api.get<MemberPass>(`/checkin/pass/${memberId}`)
  return data
}

export async function checkInQr(payload: {
  token: string
  session_id: string
  device_id?: string | null
}): Promise<CheckIn> {
  const { data } = await api.post<CheckIn>('/checkin/qr', payload)
  return data
}

export async function checkInManual(payload: {
  member_id: string
  session_id: string
}): Promise<CheckIn> {
  const { data } = await api.post<CheckIn>('/checkin/manual', payload)
  return data
}

// --- Check-in time window (per-studio config) ---
export interface CheckinWindow {
  checkin_opens_before: number
  checkin_closes_after: number
  checkin_late_threshold: number
}

export async function getCheckinWindow(): Promise<CheckinWindow> {
  const { data } = await api.get<CheckinWindow>('/checkin/window')
  return data
}

export async function updateCheckinWindow(
  payload: Partial<CheckinWindow>,
): Promise<CheckinWindow> {
  const { data } = await api.patch<CheckinWindow>('/checkin/window', payload)
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

export async function listPendingAttendance(): Promise<Attendance[]> {
  const { data } = await api.get<Attendance[]>('/attendance/pending')
  return data
}

export async function confirmAttendance(
  sessionId: string,
  memberId: string,
): Promise<Attendance> {
  const { data } = await api.post<Attendance>(
    `/attendance/session/${sessionId}/confirm`,
    { member_id: memberId },
  )
  return data
}

export async function rejectAttendance(
  sessionId: string,
  memberId: string,
): Promise<Attendance> {
  const { data } = await api.post<Attendance>(
    `/attendance/session/${sessionId}/reject`,
    { member_id: memberId },
  )
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

// --- Programs ---
export async function listPrograms(): Promise<TrainingProgram[]> {
  const { data } = await api.get<TrainingProgram[]>('/training/programs')
  return data
}

export async function createProgram(payload: {
  name: string
  description?: string | null
  duration_months?: number
}): Promise<TrainingProgram> {
  const { data } = await api.post<TrainingProgram>('/training/programs', payload)
  return data
}

export async function updateProgram(
  programId: string,
  payload: Partial<{
    name: string
    description: string | null
    duration_months: number
    is_active: boolean
  }>,
): Promise<TrainingProgram> {
  const { data } = await api.patch<TrainingProgram>(
    `/training/programs/${programId}`,
    payload,
  )
  return data
}

// --- Cohorts ---
export async function listCohorts(
  programId?: string,
): Promise<TrainingCohort[]> {
  const { data } = await api.get<TrainingCohort[]>('/training/cohorts', {
    params: programId ? { program_id: programId } : undefined,
  })
  return data
}

export async function createCohort(payload: {
  program_id: string
  name: string
  start_date: string
  end_date?: string | null
  status?: CohortStatus
}): Promise<TrainingCohort> {
  const { data } = await api.post<TrainingCohort>('/training/cohorts', payload)
  return data
}

export async function updateCohort(
  cohortId: string,
  payload: Partial<{
    name: string
    start_date: string
    end_date: string | null
    status: CohortStatus
  }>,
): Promise<TrainingCohort> {
  const { data } = await api.patch<TrainingCohort>(
    `/training/cohorts/${cohortId}`,
    payload,
  )
  return data
}

export async function getCohortProgress(
  cohortId: string,
): Promise<CohortProgress> {
  const { data } = await api.get<CohortProgress>(
    `/training/cohorts/${cohortId}/progress`,
  )
  return data
}

// --- Enrollments ---
export async function listEnrollments(
  cohortId: string,
): Promise<TrainingEnrollment[]> {
  const { data } = await api.get<TrainingEnrollment[]>(
    `/training/cohorts/${cohortId}/enrollments`,
  )
  return data
}

export async function enrollMember(
  cohortId: string,
  payload: { member_id: string; enrolled_on?: string; status?: EnrollmentStatus },
): Promise<TrainingEnrollment> {
  const { data } = await api.post<TrainingEnrollment>(
    `/training/cohorts/${cohortId}/enrollments`,
    payload,
  )
  return data
}

export async function updateEnrollment(
  enrollmentId: string,
  status: EnrollmentStatus,
): Promise<TrainingEnrollment> {
  const { data } = await api.patch<TrainingEnrollment>(
    `/training/enrollments/${enrollmentId}`,
    { status },
  )
  return data
}

export async function removeEnrollment(enrollmentId: string): Promise<void> {
  await api.delete(`/training/enrollments/${enrollmentId}`)
}
