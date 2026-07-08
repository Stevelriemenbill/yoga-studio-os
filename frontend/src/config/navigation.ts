import type { UserRole } from '@/types'

export interface NavItem {
  label: string
  icon: string
  to: string
  /** Roles allowed to see this item. Empty = everyone authenticated. */
  roles?: UserRole[]
  /** Short helper text shown as tooltip / description. */
  hint?: string
}

export interface NavGroup {
  label: string
  items: NavItem[]
}

const STAFF: UserRole[] = ['studio_admin', 'studio_manager', 'reception', 'teacher']
const MANAGERS: UserRole[] = ['studio_admin', 'studio_manager']
const FRONT_DESK: UserRole[] = ['studio_admin', 'studio_manager', 'reception']

/**
 * Navigation grouped by the jobs users come to do, not by feature.
 * - Studio: at-a-glance overview
 * - Betrieb: the daily front-desk / teaching workflow
 * - Community: people & their journeys
 * - Wachstum: insight & growth tooling (managers)
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Studio',
    items: [
      { label: 'Dashboard', icon: 'pi pi-home', to: '/', hint: 'Überblick & Live-Aktivität' },
    ],
  },
  {
    label: 'Betrieb',
    items: [
      { label: 'Stundenplan', icon: 'pi pi-calendar', to: '/courses', roles: STAFF, hint: 'Kurse planen' },
      { label: 'Buchungen', icon: 'pi pi-ticket', to: '/bookings', roles: STAFF, hint: 'Teilnehmer verwalten' },
      { label: 'Check-in', icon: 'pi pi-qrcode', to: '/checkin', roles: STAFF, hint: 'Anwesenheit erfassen' },
      { label: 'Events', icon: 'pi pi-star', to: '/events', roles: STAFF, hint: 'Workshops & Retreats' },
    ],
  },
  {
    label: 'Community',
    items: [
      { label: 'Mitglieder', icon: 'pi pi-users', to: '/members', roles: FRONT_DESK, hint: 'Kartei & Guthaben' },
      { label: 'Ausbildung', icon: 'pi pi-graduation-cap', to: '/training', roles: STAFF, hint: 'Trainees begleiten' },
    ],
  },
  {
    label: 'Wachstum',
    items: [
      { label: 'Analytics', icon: 'pi pi-chart-bar', to: '/analytics', roles: MANAGERS, hint: 'KPIs & Trends' },
      { label: 'Automatisierung', icon: 'pi pi-bolt', to: '/automations', roles: MANAGERS, hint: 'Regeln & Trigger' },
      { label: 'KI-Assistent', icon: 'pi pi-sparkles', to: '/assistant', roles: MANAGERS, hint: 'Fragen & Prognosen' },
      { label: 'Benachrichtigungen', icon: 'pi pi-bell', to: '/notifications', roles: STAFF, hint: 'Nachrichten & Verlauf' },
    ],
  },
]

export function canAccess(item: Pick<NavItem, 'roles'>, role: UserRole | undefined): boolean {
  if (!item.roles || item.roles.length === 0) return true
  if (!role) return false
  return item.roles.includes(role)
}

/** Flat map of path -> allowed roles, used by the router guard. */
export const ROUTE_ROLES: Record<string, UserRole[] | undefined> = Object.fromEntries(
  NAV_GROUPS.flatMap((g) => g.items).map((i) => [i.to, i.roles]),
)
