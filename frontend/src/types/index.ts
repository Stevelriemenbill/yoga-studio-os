export type UserRole =
  | 'studio_admin'
  | 'studio_manager'
  | 'teacher'
  | 'reception'
  | 'member'
  | 'trainee'

export interface User {
  id: string
  tenant_id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
}

export interface Tenant {
  id: string
  name: string
  slug: string
  is_active: boolean
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RegistrationResult {
  tenant: Tenant
  user: User
  token: Token
}

export interface LoginRequest {
  email: string
  password: string
  tenant_slug: string
}

export interface StudioRegistration {
  studio_name: string
  studio_slug: string
  admin_email: string
  admin_password: string
  admin_full_name?: string | null
}
