import { api } from './client'
import type { AIInsight, FillForecast } from '@/types'

export async function listInsights(): Promise<AIInsight[]> {
  const { data } = await api.get<AIInsight[]>('/ai/insights')
  return data
}

export async function generateInsights(): Promise<AIInsight[]> {
  const { data } = await api.post<AIInsight[]>('/ai/insights/generate')
  return data
}

export async function getForecast(daysAhead = 14): Promise<FillForecast[]> {
  const { data } = await api.get<FillForecast[]>('/ai/forecast', {
    params: { days_ahead: daysAhead },
  })
  return data
}

export async function askAssistant(question: string): Promise<AIInsight> {
  const { data } = await api.post<AIInsight>('/ai/assistant', { question })
  return data
}
