import { api } from './client'
import type {
  LoginRequest,
  Me,
  RegistrationResult,
  StudioRegistration,
  ThemeSettings,
  Token,
  User,
} from '@/types'

export async function register(
  payload: StudioRegistration,
): Promise<RegistrationResult> {
  const { data } = await api.post<RegistrationResult>('/auth/register', payload)
  return data
}

export async function login(payload: LoginRequest): Promise<Token> {
  const { data } = await api.post<Token>('/auth/login', payload)
  return data
}

export async function fetchMe(): Promise<Me> {
  const { data } = await api.get<Me>('/auth/me')
  return data
}

export async function updateTheme(
  payload: Partial<ThemeSettings>,
): Promise<ThemeSettings> {
  const { data } = await api.patch<ThemeSettings>('/auth/theme', payload)
  return data
}

export interface InvitedMember {
  first_name: string
  last_name: string
  email: string
  studio_name: string
}

export interface AcceptInviteResult {
  user: User
  token: Token
}

export async function previewInvite(token: string): Promise<InvitedMember> {
  const { data } = await api.get<InvitedMember>(
    `/auth/invite/${encodeURIComponent(token)}`,
  )
  return data
}

export async function acceptInvite(
  token: string,
  password: string,
): Promise<AcceptInviteResult> {
  const { data } = await api.post<AcceptInviteResult>('/auth/invite/accept', {
    token,
    password,
  })
  return data
}

export interface InvitedStaff {
  email: string
  full_name: string | null
  role: string
  studio_name: string
}

export async function previewStaffInvite(token: string): Promise<InvitedStaff> {
  const { data } = await api.get<InvitedStaff>(
    `/auth/staff-invite/${encodeURIComponent(token)}`,
  )
  return data
}

export async function acceptStaffInvite(
  token: string,
  password: string,
): Promise<AcceptInviteResult> {
  const { data } = await api.post<AcceptInviteResult>(
    '/auth/staff-invite/accept',
    { token, password },
  )
  return data
}
