import { api } from './client'
import type {
  LoginRequest,
  RegistrationResult,
  StudioRegistration,
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

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>('/auth/me')
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
