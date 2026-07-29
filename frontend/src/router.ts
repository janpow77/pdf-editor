import { createRouter, createWebHistory } from 'vue-router'

import LandingView from '@/views/LandingView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: LandingView },
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
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
