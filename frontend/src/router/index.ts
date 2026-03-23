import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'
import { getAccessToken } from '@/api'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
    { path: '/', component: () => import('@/views/DashboardView.vue') },
    { path: '/accounts', component: () => import('@/views/AccountsView.vue') },
    { path: '/monitor', component: () => import('@/views/AccountsMonitorView.vue') },
    { path: '/publish-status', component: () => import('@/views/PublishStatusView.vue') },
    { path: '/materials', component: () => import('@/views/MaterialsView.vue') },
    { path: '/schedule', component: () => import('@/views/ScheduleView.vue') },
    { path: '/calendar', component: () => import('@/views/CalendarView.vue') },
    { path: '/analytics', component: () => import('@/views/AnalyticsView.vue') },
    { path: '/profile-editor', component: () => import('@/views/ProfileEditorView.vue') },
    { path: '/inbox', component: () => import('@/views/InboxView.vue') },
    { path: '/traffic', component: () => import('@/views/TrafficView.vue') },
    { path: '/logs', component: () => import('@/views/LogsView.vue') },
    { path: '/guide', component: () => import('@/views/GuideView.vue') },
    { path: '/users', component: () => import('@/views/UsersView.vue') },
    { path: '/toolbox', component: () => import('@/views/ToolboxView.vue') },
  ],
})

// 导航守卫：无 token 时检查是否需要登录
router.beforeEach(async (to) => {
  // 公开页面直接放行
  if (to.meta.public) return true

  // 已有 token，放行
  const token = getAccessToken()
  if (token) return true

  // 无 token，调用 /auth/check 看是否需要登录
  try {
    const resp = await axios.get('/api/v1/auth/check')
    if (!resp.data.auth_required) return true  // 后端未设密码，不需要登录
  } catch {
    // 后端不可达时放行，让页面自己处理离线状态
    return true
  }

  // 需要登录，跳转到登录页（记住来源路径）
  return { path: '/login', query: { redirect: to.fullPath } }
})

export default router
