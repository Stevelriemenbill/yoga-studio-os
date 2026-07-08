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

// --- Members ---
export type MembershipType = 'none' | 'drop_in' | 'punch_card' | 'unlimited'

export interface Member {
  id: string
  first_name: string
  last_name: string
  email: string | null
  phone: string | null
  notes: string | null
  membership_type: MembershipType
  membership_valid_until: string | null
  credits: number
  reliability_score: number
  user_id: string | null
}

// --- Courses / Rooms / Sessions ---
export type CourseLevel = 'all' | 'beginner' | 'intermediate' | 'advanced'

export interface Room {
  id: string
  name: string
  capacity: number
  is_active: boolean
}

export interface Course {
  id: string
  name: string
  description: string | null
  category: string | null
  level: CourseLevel
  room_id: string | null
  teacher_id: string | null
  max_participants: number
  min_participants: number
  duration_minutes: number
  is_active: boolean
}

export type SessionStatus = 'scheduled' | 'cancelled' | 'completed'

export interface CourseSession {
  id: string
  course_id: string
  starts_at: string
  ends_at?: string | null
  teacher_id: string | null
  room_id: string | null
  capacity: number | null
  status: SessionStatus
}

export interface SessionWithStats extends CourseSession {
  ends_at: string
  capacity: number
  overbooking_allowance: number
  booked_count: number
  waitlist_count: number
  available_spots: number
}

// --- Bookings / Waitlist ---
export type BookingStatus = 'booked' | 'cancelled' | 'attended' | 'no_show'
export type BookingSource = 'direct' | 'drop_in' | 'waitlist'

export interface Booking {
  id: string
  session_id: string
  member_id: string
  status: BookingStatus
  source: BookingSource
  booked_at: string | null
  cancelled_at: string | null
}

export type WaitlistStatus = 'waiting' | 'offered' | 'accepted' | 'expired' | 'declined'

export interface WaitlistEntry {
  id: string
  session_id: string
  member_id: string
  status: WaitlistStatus
  priority: number
  score: number
  joined_at: string
  offered_at: string | null
  offer_expires_at: string | null
}

// --- Check-in / Attendance ---
export type CheckInMethod = 'qr' | 'manual'
export type AttendanceStatus =
  | 'pending'
  | 'present'
  | 'absent'
  | 'excused'
  | 'late'

export interface Attendance {
  id: string
  session_id: string
  member_id: string
  status: AttendanceStatus
  recorded_by: string | null
}

export interface CheckIn {
  id: string
  member_id: string
  session_id: string | null
  booking_id: string | null
  checked_in_at: string
  method: CheckInMethod
  device_id: string | null
}

export interface MemberPass {
  member_id: string
  token: string
  qr_payload: string
}

// --- Training ---
export type TrainingArea = string

export interface TrainingHours {
  id: string
  trainee_id: string
  area: TrainingArea
  hours: number
  entry_date: string
  teacher_id: string | null
  session_id: string | null
  note: string | null
}

export interface AreaProgress {
  area: string
  completed_hours: number
  required_hours: number
  progress: number | null
}

export interface TrainingDashboard {
  trainee_id: string
  total_completed: number
  total_required: number
  breakdown: AreaProgress[]
}

// --- Notifications ---
export type NotificationChannel = 'email' | 'push' | 'whatsapp'
export type NotificationStatus = 'pending' | 'sent' | 'failed'

export interface AppNotification {
  id: string
  member_id: string | null
  channel: NotificationChannel
  subject: string | null
  body: string
  status: NotificationStatus
  scheduled_for: string | null
  sent_at: string | null
  template: string | null
}

// --- Analytics (sanfter Puls der Gemeinschaft) ---
export interface CommunityPulse {
  sessions: number
  people_practicing: number
  total_practices: number
  new_members: number
}

export interface TeacherReach {
  teacher_id: string
  sessions: number
  students_guided: number
  returning_students: number
}

// --- Automations ---
export type AutomationTrigger =
  | 'inactive_days'
  | 'after_booking'
  | 'before_session'
  | 'after_no_show'
  | 'membership_expiring'

export interface AutomationRule {
  id: string
  name: string
  trigger: AutomationTrigger
  threshold_days: number
  channel: NotificationChannel
  message_template: string
  is_active: boolean
}

export interface AutomationRunResult {
  total_enqueued: number
  per_rule: Record<string, number>
}

// --- Begleitung / Fürsorge ---
export type InsightType =
  | 'care'
  | 'milestone'
  | 'assistant_answer'
  | 'forecast'
  | 'recommendation'
  | 'anomaly'

export interface AIInsight {
  id: string
  type: InsightType
  title: string
  body: string
  confidence: number | null
  data: Record<string, unknown> | null
  created_at: string
}

export interface StudentInNeed {
  member_id: string
  name: string
  days_since_last_visit: number
  last_visit: string
  usual_visits_per_week: number
  total_visits: number
}

export interface PracticedStyle {
  course: string
  visits: number
}

export interface StudentJourney {
  member_id: string
  name: string
  member_since: string
  days_as_member: number
  total_practices: number
  practiced_styles: PracticedStyle[]
  weeks_practiced_recent: number
  last_visit: string | null
  days_since_last_visit: number | null
  milestones_reached: number[]
  next_milestone: number | null
  practices_to_next_milestone: number | null
}

export interface StudentNote {
  id: string
  member_id: string
  author_id: string | null
  body: string
  created_at: string
}

// --- Events ---
export type EventType = 'workshop' | 'retreat' | 'special'
export type EventRegistrationStatus = 'pending' | 'confirmed' | 'cancelled' | 'waitlisted'

export interface StudioEvent {
  id: string
  name: string
  description: string | null
  type: EventType
  starts_at: string
  ends_at: string
  location: string | null
  capacity: number
  price_cents: number
  requires_deposit: boolean
  deposit_cents: number
  teacher_id: string | null
  is_published: boolean
}

export interface EventRegistration {
  id: string
  event_id: string
  member_id: string
  status: EventRegistrationStatus
  amount_paid_cents: number
}
