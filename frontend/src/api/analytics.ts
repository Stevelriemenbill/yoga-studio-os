import { api } from './client'
import type {
  HeatmapCell,
  PopularCourse,
  StudioKpis,
  TeacherAnalytics,
} from '@/types'

export async function getKpis(): Promise<StudioKpis> {
  const { data } = await api.get<StudioKpis>('/analytics/kpis')
  return data
}

export async function getHeatmap(): Promise<HeatmapCell[]> {
  const { data } = await api.get<HeatmapCell[]>('/analytics/heatmap')
  return data
}

export async function getTeacherAnalytics(): Promise<TeacherAnalytics[]> {
  const { data } = await api.get<TeacherAnalytics[]>('/analytics/teachers')
  return data
}

export async function getPopularCourses(): Promise<PopularCourse[]> {
  const { data } = await api.get<PopularCourse[]>('/analytics/popular-courses')
  return data
}
