import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { ROUTE_ROLES } from '@/config/navigation'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/invite/:token',
      name: 'accept-invite',
      component: () => import('@/views/AcceptInviteView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'calendar',
          name: 'calendar',
          component: () => import('@/views/ScheduleCalendarView.vue'),
        },
        {
          path: 'courses',
          name: 'courses',
          component: () => import('@/views/CoursesView.vue'),
        },
        {
          path: 'members',
          name: 'members',
          component: () => import('@/views/MembersView.vue'),
        },
        {
          path: 'bookings',
          name: 'bookings',
          component: () => import('@/views/BookingsView.vue'),
        },
        {
          path: 'checkin',
          name: 'checkin',
          component: () => import('@/views/CheckinView.vue'),
        },
        {
          path: 'training',
          name: 'training',
          component: () => import('@/views/TrainingView.vue'),
        },
        {
          path: 'events',
          name: 'events',
          component: () => import('@/views/EventsView.vue'),
        },
        {
          path: 'care',
          name: 'care',
          component: () => import('@/views/CareView.vue'),
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: () => import('@/views/AnalyticsView.vue'),
        },
        {
          path: 'automations',
          name: 'automations',
          component: () => import('@/views/AutomationsView.vue'),
        },
        {
          path: 'assistant',
          name: 'assistant',
          component: () => import('@/views/AssistantView.vue'),
        },
        {
          path: 'notifications',
          name: 'notifications',
          component: () => import('@/views/NotificationsView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
        },
        {
          path: 'me/schedule',
          name: 'my-schedule',
          component: () => import('@/views/member/MyScheduleView.vue'),
        },
        {
          path: 'me/bookings',
          name: 'my-bookings',
          component: () => import('@/views/member/MyBookingsView.vue'),
        },
        {
          path: 'me/pass',
          name: 'my-pass',
          component: () => import('@/views/member/MyPassView.vue'),
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    await auth.initialize()
  }

  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.public && auth.isAuthenticated && to.name !== 'accept-invite') {
    return { name: 'dashboard' }
  }

  // Role-based access: redirect to dashboard if the user's role
  // is not permitted for the target path.
  if (!to.meta.public && auth.isAuthenticated) {
    const allowed = ROUTE_ROLES[to.path]
    const role = auth.user?.role
    if (allowed && allowed.length > 0 && (!role || !allowed.includes(role))) {
      return { name: 'dashboard' }
    }
  }

  return true
})

export default router
