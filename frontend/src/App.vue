<template>
  <!-- 登录页：不显示侧边栏布局 -->
  <div v-if="$route.path === '/login'" :class="{ 'theme-light': isLight }">
    <router-view />
  </div>

  <div v-else class="flex h-screen overflow-hidden" :class="{ 'theme-light': isLight }">
    <!-- 侧边栏 -->
    <aside class="w-56 flex-shrink-0 flex flex-col border-r" :style="sidebarStyle">
      <!-- Logo -->
      <div class="h-16 flex items-center px-4 border-b" :style="`border-color:var(--border)`">
        <div class="flex items-center gap-2">
          <svg width="30" height="28" viewBox="0 0 64 58" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink:0">
            <path d="M 7 52 C 5 38, 7 18, 17 10 C 24 5, 31 9, 30 22"
                  :stroke="isLight ? '#7B4A2F' : '#C49A6C'" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M 30 22 C 29 9, 36 5, 43 10 C 53 18, 55 38, 53 52"
                  :stroke="isLight ? '#7B4A2F' : '#C49A6C'" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M 46 40 L 53 52"
                  :stroke="isLight ? '#7B4A2F' : '#C49A6C'" stroke-width="6" stroke-linecap="round"/>
            <ellipse cx="28" cy="36" rx="9" ry="13" :fill="isLight ? '#7B4A2F' : '#C49A6C'" transform="rotate(-8 28 36)"/>
            <path d="M 29 23 Q 32 36 29 49"
                  stroke="rgba(255,255,255,0.38)" stroke-width="1.8" fill="none" stroke-linecap="round"/>
          </svg>
          <span :style="`font-family:'Cinzel',Georgia,serif; font-size:11.5px; font-weight:600; letter-spacing:0.10em; color:${isLight ? '#7B4A2F' : '#C49A6C'}; text-transform:uppercase; flex-shrink:0;`">MAYRICHBE</span>
        </div>
      </div>

      <!-- 导航 -->
      <nav class="flex-1 p-3 flex flex-col gap-0.5 overflow-y-auto">
        <p class="nav-section-label">概览</p>
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">仪表盘</router-link>
        <router-link to="/analytics" class="nav-item" :class="{ active: $route.path === '/analytics' }">数据统计</router-link>

        <p class="nav-section-label mt-2">内容管理</p>
        <router-link to="/accounts" class="nav-item" :class="{ active: $route.path === '/accounts' }">账号管理</router-link>
        <router-link to="/publish-status" class="nav-item" :class="{ active: $route.path === '/publish-status' }">发布状态</router-link>
        <router-link to="/materials" class="nav-item" :class="{ active: $route.path === '/materials' }">素材库</router-link>

        <p class="nav-section-label mt-2">发布</p>
        <router-link to="/calendar" class="nav-item" :class="{ active: $route.path === '/calendar' }">发布日历</router-link>
        <router-link to="/schedule" class="nav-item" :class="{ active: $route.path === '/schedule' }">任务列表</router-link>
        <router-link to="/profile-editor" class="nav-item" :class="{ active: $route.path === '/profile-editor' }">批量改资料</router-link>
        <router-link to="/inbox" class="nav-item" :class="{ active: $route.path === '/inbox' }">消息中心</router-link>
        <router-link to="/traffic" class="nav-item" :class="{ active: $route.path === '/traffic' }">自动截流</router-link>
        <router-link to="/logs" class="nav-item" :class="{ active: $route.path === '/logs' }">发布日志</router-link>

        <p class="nav-section-label mt-2">其他</p>
        <router-link to="/toolbox" class="nav-item" :class="{ active: $route.path === '/toolbox' }">工具箱</router-link>
        <router-link to="/guide" class="nav-item" :class="{ active: $route.path === '/guide' }">使用说明</router-link>
        <router-link v-if="isAdmin" to="/users" class="nav-item" :class="{ active: $route.path === '/users' }">用户管理</router-link>
      </nav>

      <!-- 底部：用户信息 + 主题切换 + 状态 -->
      <div class="p-3 border-t flex flex-col gap-2" :style="`border-color:var(--border)`">
        <!-- 当前用户 + 退出 -->
        <div v-if="currentUsername" class="flex items-center justify-between px-3 py-2 rounded-lg text-xs" :style="`background:var(--bg-base); border:1px solid var(--border)`">
          <span style="color:var(--text-muted)">{{ currentUsername }}</span>
          <button class="logout-btn" @click="handleLogout">退出</button>
        </div>
        <!-- 主题切换 -->
        <button
          class="flex items-center justify-between w-full px-3 py-2 rounded-lg text-xs transition-all"
          :style="`background:var(--bg-base); border:1px solid var(--border); color:var(--text-muted)`"
          @click="toggleTheme"
        >
          <span>{{ isLight ? '🌙 深色模式' : '☀️ 亮色模式' }}</span>
          <span class="opacity-60">切换</span>
        </button>
        <!-- 时区切换 -->
        <button
          class="flex items-center justify-between w-full px-3 py-2 rounded-lg text-xs transition-all"
          :style="`background:var(--bg-base); border:1px solid var(--border); color:var(--text-muted)`"
          @click="toggleTimezone"
        >
          <span>{{ tzOffset === 9 ? '🕘 +9 東京時間' : '🕗 +8 北京时间' }}</span>
          <span class="opacity-60">切换</span>
        </button>
        <!-- API 状态 -->
        <div class="flex items-center gap-2 px-1">
          <div class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="backendOnline ? 'bg-green-500' : 'bg-red-500'"></div>
          <span class="text-xs" style="color:var(--text-faint)">{{ backendOnline ? 'API 已连接' : 'API 离线' }}</span>
        </div>
      </div>
    </aside>

    <!-- 主内容 -->
    <div class="flex-1 flex flex-col overflow-hidden" :style="`background:var(--bg-base)`">
      <!-- Header -->
      <header class="h-14 flex items-center justify-between px-6 border-b flex-shrink-0" :style="`background:var(--bg-surface2); border-color:var(--border)`">
        <div>
          <h1 class="text-sm font-semibold" style="color:var(--text-primary)">{{ pageTitle }}</h1>
          <p class="text-xs" style="color:var(--text-faint)">{{ pageDesc }}</p>
        </div>
        <span class="text-xs px-2 py-1 rounded" :style="`background:var(--bg-surface); color:var(--text-faint); border:1px solid var(--border)`">
          {{ currentDate }}
        </span>
      </header>

      <!-- 页面内容 -->
      <main class="flex-1 overflow-y-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import dayjs from 'dayjs'
import { clearAuth, authApi, getAccessToken } from '@/api'
import { getTzOffset, setTzOffset } from '@/composables/timezone'

const route = useRoute()
const router = useRouter()
const backendOnline = ref(false)
const isLight = ref(localStorage.getItem('theme') === 'light')
const tzOffset = ref(getTzOffset())
function toggleTimezone() {
  const next = tzOffset.value === 9 ? 8 : 9
  tzOffset.value = next
  setTzOffset(next)
}
const currentUsername = ref(localStorage.getItem('sm_username') || '')
const isAdmin = ref(localStorage.getItem('sm_is_admin') === '1')

const sidebarStyle = computed(() =>
  isLight.value
    ? 'background:rgba(235,235,240,0.92); border-color:rgba(0,0,0,0.08)'
    : 'background:#0a1628; border-color:var(--border-light)'
)

function toggleTheme() {
  isLight.value = !isLight.value
  localStorage.setItem('theme', isLight.value ? 'light' : 'dark')
}

function handleLogout() {
  clearAuth()
  currentUsername.value = ''
  isAdmin.value = false
  router.push('/login')
}

const pageMeta: Record<string, { title: string; desc: string }> = {
  '/': { title: '仪表盘', desc: '总览所有账号与发布状态' },
  '/accounts': { title: '账号管理', desc: '管理 Instagram 和 YouTube 账号' },
  '/publish-status': { title: '发布状态', desc: '确认所有账号发布成功并查看实时数据' },
  '/monitor': { title: '多账号监控', desc: '查看账号实时状态和最新帖子' },
  '/materials': { title: '素材库', desc: '上传和管理发布内容' },
  '/schedule': { title: '任务列表', desc: '查看和管理所有发布任务' },
  '/calendar': { title: '发布日历', desc: '按日历视图查看发布计划' },
  '/analytics': { title: '数据统计', desc: '发布成功率与账号活跃度分析' },
  '/profile-editor': { title: '批量改资料', desc: '批量修改账号简介和头像' },
  '/inbox': { title: '消息中心', desc: '集中管理所有账号的评论和私信' },
  '/traffic': { title: '自动截流', desc: '通过话题/对标账号自动互动引流' },
  '/logs': { title: '发布日志', desc: '每次发布的详细操作记录' },
  '/guide': { title: '使用说明', desc: '完整操作手册与 FAQ' },
  '/users': { title: '用户管理', desc: '管理系统用户和权限' },
  '/toolbox': { title: '工具箱', desc: '养号、通知测试等实用工具' },
}

const pageTitle = computed(() => pageMeta[route.path]?.title || 'Mayrichbe Manager')
const pageDesc = computed(() => pageMeta[route.path]?.desc || '')
const currentDate = computed(() => dayjs().format('YYYY年M月D日'))

onMounted(async () => {
  try {
    await axios.get('/health', { timeout: 4000 })
    backendOnline.value = true
  } catch {
    backendOnline.value = false
  }
  // 刷新时同步用户名
  currentUsername.value = localStorage.getItem('sm_username') || ''
  isAdmin.value = localStorage.getItem('sm_is_admin') === '1'
  // 有 token 时调 /auth/me 同步最新用户信息（admin 状态可能被后台修改）
  if (getAccessToken()) {
    try {
      const me: any = await authApi.me()
      currentUsername.value = me.username
      isAdmin.value = me.is_admin
      localStorage.setItem('sm_username', me.username)
      localStorage.setItem('sm_is_admin', me.is_admin ? '1' : '0')
    } catch {
      // token 失效会被 interceptor 处理
    }
  }
})
</script>

<style>
.nav-section-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  padding: 4px 12px 2px;
  color: var(--text-faint);
}
.logout-btn {
  background: none;
  border: none;
  color: var(--text-faint);
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s;
}
.logout-btn:hover {
  color: #f87171;
  background: rgba(248, 113, 113, 0.1);
}
</style>
