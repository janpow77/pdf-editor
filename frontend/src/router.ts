import { createRouter, createWebHistory } from 'vue-router'

import { fetchMe, isAdmin, isAuthenticated, user } from '@/lib/auth'
import LandingView from '@/views/LandingView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/registrieren',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
    },
    {
      path: '/passwort-vergessen',
      name: 'passwort-vergessen',
      component: () => import('@/views/PasswortVergessenView.vue'),
    },
    {
      path: '/passwort-reset',
      name: 'passwort-reset',
      component: () => import('@/views/PasswortResetView.vue'),
    },
    {
      path: '/email-bestaetigen',
      name: 'email-bestaetigen',
      component: () => import('@/views/EmailBestaetigenView.vue'),
    },
    {
      path: '/konto',
      name: 'account',
      component: () => import('@/views/AccountView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminUsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/impressum',
      name: 'impressum',
      component: () => import('@/views/ImpressumView.vue'),
    },
    {
      path: '/datenschutz',
      name: 'datenschutz',
      component: () => import('@/views/DatenschutzView.vue'),
    },
    {
      path: '/lizenzen',
      name: 'lizenzen',
      component: () => import('@/views/LizenzenView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  if (isAuthenticated.value && !user.value) {
    await fetchMe()
  }
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !isAdmin.value) {
    return { path: '/' }
  }
  return true
})
