import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('@/views/DashboardView.vue') },
    { path: '/accounts', component: () => import('@/views/AccountsView.vue') },
    { path: '/materials', component: () => import('@/views/MaterialsView.vue') },
    { path: '/schedule', component: () => import('@/views/ScheduleView.vue') },
    { path: '/calendar', component: () => import('@/views/CalendarView.vue') },
    { path: '/analytics', component: () => import('@/views/AnalyticsView.vue') },
    { path: '/profile-editor', component: () => import('@/views/ProfileEditorView.vue') },
    { path: '/inbox', component: () => import('@/views/InboxView.vue') },
    { path: '/traffic', component: () => import('@/views/TrafficView.vue') },
    { path: '/logs', component: () => import('@/views/LogsView.vue') },
    { path: '/guide', component: () => import('@/views/GuideView.vue') },
  ],
})

export default router
