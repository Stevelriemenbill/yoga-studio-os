import { api } from './client'
import type {
  AIInsight,
  StudentInNeed,
  StudentJourney,
  StudentNote,
} from '@/types'

export async function listInsights(): Promise<AIInsight[]> {
  const { data } = await api.get<AIInsight[]>('/care/insights')
  return data
}

export async function generateInsights(): Promise<AIInsight[]> {
  const { data } = await api.post<AIInsight[]>('/care/insights/generate')
  return data
}

export async function getStudentsNeedingCare(quietDays = 21): Promise<StudentInNeed[]> {
  const { data } = await api.get<StudentInNeed[]>('/care/students-needing-care', {
    params: { quiet_days: quietDays },
  })
  return data
}

export async function getStudentJourney(memberId: string): Promise<StudentJourney> {
  const { data } = await api.get<StudentJourney>(`/care/journey/${memberId}`)
  return data
}

export async function askAssistant(question: string): Promise<AIInsight> {
  const { data } = await api.post<AIInsight>('/care/assistant', { question })
  return data
}

export async function listNotes(memberId: string): Promise<StudentNote[]> {
  const { data } = await api.get<StudentNote[]>(`/care/notes/${memberId}`)
  return data
}

export async function addNote(memberId: string, body: string): Promise<StudentNote> {
  const { data } = await api.post<StudentNote>(`/care/notes/${memberId}`, { body })
  return data
}

export async function deleteNote(noteId: string): Promise<void> {
  await api.delete(`/care/notes/${noteId}`)
}
