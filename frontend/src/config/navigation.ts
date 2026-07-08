import type { UserRole } from '@/types'

export interface NavItem {
  /** i18n key for the label, e.g. `nav.dashboard`. */
  labelKey: string
  icon: string
  to: string
  /** Roles allowed to see this item. Empty = everyone authenticated. */
  roles?: UserRole[]
  /** i18n key for the tooltip / description. */
  hintKey?: string
}

export interface NavGroup {
  /** i18n key for the group label, e.g. `nav.groups.studio`. */
  labelKey: string
  items: NavItem[]
}

const STAFF: UserRole[] = ['studio_admin', 'studio_manager', 'reception', 'teacher']
const MANAGERS: UserRole[] = ['studio_admin', 'studio_manager']
const FRONT_DESK: UserRole[] = ['studio_admin', 'studio_manager', 'reception']
const ADMIN: UserRole[] = ['studio_admin']
const MEMBERS: UserRole[] = ['member', 'trainee']

/**
 * Navigation grouped by the jobs users come to do, not by feature.
 * Labels/hints are i18n keys resolved at render time.
 */
export const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: 'nav.groups.studio',
    items: [
      { labelKey: 'nav.dashboard', icon: 'pi pi-home', to: '/', hintKey: 'nav.hints.dashboard' },
    ],
  },
  {
    labelKey: 'nav.groups.operations',
    items: [
      { labelKey: 'nav.calendar', icon: 'pi pi-calendar', to: '/calendar', hintKey: 'nav.hints.calendar' },
      { labelKey: 'nav.schedule', icon: 'pi pi-calendar', to: '/courses', roles: STAFF, hintKey: 'nav.hints.schedule' },
      { labelKey: 'nav.bookings', icon: 'pi pi-ticket', to: '/bookings', roles: STAFF, hintKey: 'nav.hints.bookings' },
      { labelKey: 'nav.checkin', icon: 'pi pi-qrcode', to: '/checkin', roles: STAFF, hintKey: 'nav.hints.checkin' },
      { labelKey: 'nav.events', icon: 'pi pi-star', to: '/events', roles: STAFF, hintKey: 'nav.hints.events' },
    ],
  },
  {
    labelKey: 'nav.groups.community',
    items: [
      { labelKey: 'nav.members', icon: 'pi pi-users', to: '/members', roles: FRONT_DESK, hintKey: 'nav.hints.members' },
      { labelKey: 'nav.joinRequests', icon: 'pi pi-user-plus', to: '/join-requests', roles: FRONT_DESK, hintKey: 'nav.hints.joinRequests' },
      { labelKey: 'nav.team', icon: 'pi pi-id-card', to: '/users', roles: ADMIN, hintKey: 'nav.hints.team' },
      { labelKey: 'nav.training', icon: 'pi pi-graduation-cap', to: '/training', roles: STAFF, hintKey: 'nav.hints.training' },
    ],
  },
  {
    labelKey: 'nav.groups.guidance',
    items: [
      { labelKey: 'nav.care', icon: 'pi pi-heart', to: '/care', roles: STAFF, hintKey: 'nav.hints.care' },
      { labelKey: 'nav.assistant', icon: 'pi pi-sparkles', to: '/assistant', roles: STAFF, hintKey: 'nav.hints.assistant' },
      { labelKey: 'nav.community', icon: 'pi pi-chart-line', to: '/analytics', roles: MANAGERS, hintKey: 'nav.hints.community' },
      { labelKey: 'nav.automations', icon: 'pi pi-bolt', to: '/automations', roles: MANAGERS, hintKey: 'nav.hints.automations' },
      { labelKey: 'nav.notifications', icon: 'pi pi-bell', to: '/notifications', roles: STAFF, hintKey: 'nav.hints.notifications' },
    ],
  },
  {
    labelKey: 'nav.groups.myArea',
    items: [
      { labelKey: 'nav.mySchedule', icon: 'pi pi-calendar-plus', to: '/me/schedule', roles: MEMBERS, hintKey: 'nav.hints.mySchedule' },
      { labelKey: 'nav.myEvents', icon: 'pi pi-star', to: '/me/events', roles: MEMBERS, hintKey: 'nav.hints.myEvents' },
      { labelKey: 'nav.myBookings', icon: 'pi pi-ticket', to: '/me/bookings', roles: MEMBERS, hintKey: 'nav.hints.myBookings' },
      { labelKey: 'nav.myHistory', icon: 'pi pi-history', to: '/me/history', roles: MEMBERS, hintKey: 'nav.hints.myHistory' },
      { labelKey: 'nav.myPass', icon: 'pi pi-qrcode', to: '/me/pass', roles: MEMBERS, hintKey: 'nav.hints.myPass' },
    ],
  },
  {
    labelKey: 'nav.groups.account',
    items: [
      { labelKey: 'nav.messages', icon: 'pi pi-comments', to: '/messages', hintKey: 'nav.hints.messages' },
      { labelKey: 'nav.settings', icon: 'pi pi-cog', to: '/settings', hintKey: 'nav.hints.settings' },
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

/** Flat map of path -> i18n label key, used for page titles. */
export const ROUTE_TITLE_KEYS: Record<string, string> = Object.fromEntries(
  NAV_GROUPS.flatMap((g) => g.items).map((i) => [i.to, i.labelKey]),
)
