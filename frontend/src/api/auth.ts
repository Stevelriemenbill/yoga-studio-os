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
