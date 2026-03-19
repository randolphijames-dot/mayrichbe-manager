<template>
  <div class="flex flex-col gap-6">
    <!-- 新手主线引导 -->
    <div class="grid grid-cols-3 gap-4">
      <router-link to="/accounts" class="card cursor-pointer hover:shadow-lg transition-shadow">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold" style="background:var(--brand); color:white">1</div>
          <div>
            <p class="text-xs font-semibold" style="color:var(--text-primary)">第一步 · 添加账号</p>
            <p class="text-xs" style="color:var(--text-faint)">录入 INS / YT 账号，选好发布方式</p>
          </div>
        </div>
        <p class="text-xs" style="color:var(--text-muted)">建议先按「财经矩阵 / 生活矩阵」等分组管理，后面才好一键批量操作。</p>
      </router-link>
      <router-link to="/materials" class="card cursor-pointer hover:shadow-lg transition-shadow">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold" style="background:#0ea5e9; color:white">2</div>
          <div>
            <p class="text-xs font-semibold" style="color:var(--text-primary)">第二步 · 上传素材</p>
            <p class="text-xs" style="color:var(--text-faint)">把视频/图片放入素材库，按日期/话题建文件夹</p>
          </div>
        </div>
        <p class="text-xs" style="color:var(--text-muted)">上传时就可以顺手勾选要投放的账号，后面排期会更快。</p>
      </router-link>
      <router-link to="/schedule" class="card cursor-pointer hover:shadow-lg transition-shadow">
        <div class="flex items-center gap-3 mb-2">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold" style="background:#22c55e; color:white">3</div>
          <div>
            <p class="text-xs font-semibold" style="color:var(--text-primary)">第三步 · 安排定时发布</p>
            <p class="text-xs" style="color:var(--text-faint)">在素材库或发布看板里选择时间，一键生成任务</p>
          </div>
        </div>
        <p class="text-xs" style="color:var(--text-muted)">系统会用内置「定时闹钟」帮你记住全部排期，到点自动执行。</p>
      </router-link>
    </div>
    <!-- KPI 统计行 -->
    <div class="grid grid-cols-4 gap-4">
      <div class="stat-card">
        <div class="flex items-center justify-between">
          <span class="stat-label">总账号数</span>
          <Users :size="16" style="color:#0ea5e9" />
        </div>
        <div class="stat-value">{{ stats.totalAccounts }}</div>
        <div class="flex gap-3 mt-1">
          <span class="badge badge-pink">📸 {{ stats.insAccounts }} INS</span>
          <span class="badge badge-red">▶ {{ stats.ytAccounts }} YT</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex items-center justify-between">
          <span class="stat-label">素材库</span>
          <Image :size="16" style="color:#a78bfa" />
        </div>
        <div class="stat-value">{{ stats.totalMaterials }}</div>
        <span class="badge badge-blue" style="margin-top:4px">{{ stats.readyMaterials }} 就绪</span>
      </div>

      <div class="stat-card">
        <div class="flex items-center justify-between">
          <span class="stat-label">待发布</span>
          <Clock :size="16" style="color:#fbbf24" />
        </div>
        <div class="stat-value" style="color:#fbbf24">{{ stats.pendingTasks }}</div>
        <span class="text-xs" style="color:var(--text-faint); margin-top:4px">{{ stats.queuedTasks }} 已入队</span>
      </div>

      <div class="stat-card">
        <div class="flex items-center justify-between">
          <span class="stat-label">今日成功</span>
          <CheckCircle :size="16" style="color:#4ade80" />
        </div>
        <div class="stat-value" style="color:#4ade80">{{ stats.todaySuccess }}</div>
        <span class="text-xs" style="color:#ef4444; margin-top:4px" v-if="stats.todayFailed > 0">{{ stats.todayFailed }} 失败</span>
        <span class="text-xs" style="color:var(--text-faint); margin-top:4px" v-else>无失败</span>
      </div>
    </div>

    <!-- 中间区域：任务 + 日志 -->
    <div class="grid grid-cols-2 gap-4">
      <!-- 待发布任务 -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold" style="color:var(--text-primary)">近期待发布任务</h3>
          <router-link to="/schedule" class="text-xs" style="color:#0ea5e9">查看全部 →</router-link>
        </div>

        <div v-if="loading" class="empty-state">
          <div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
        </div>
        <div v-else-if="upcomingTasks.length === 0" class="empty-state">
          <CalendarDays :size="32" />
          <p class="text-sm">暂无待发布任务</p>
        </div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="task in upcomingTasks"
            :key="task.id"
            class="flex items-center justify-between p-3 rounded-lg"
            style="background:var(--bg-base); border:1px solid var(--border-light)"
          >
            <div class="flex flex-col gap-1">
              <div class="flex items-center gap-2">
                <span class="badge" :class="getPlatformBadge(task.account_id)">
                  {{ getPlatformLabel(task.account_id) }}
                </span>
                <span class="text-sm" style="color:var(--text-muted)">账号 #{{ task.account_id }}</span>
              </div>
              <span class="text-xs" style="color:var(--text-faint)">{{ formatDate(task.scheduled_at) }}</span>
            </div>
            <span class="badge" :class="getStatusBadge(task.status)">{{ getStatusLabel(task.status) }}</span>
          </div>
        </div>
      </div>

      <!-- 最新日志 -->
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold" style="color:var(--text-primary)">最新发布日志</h3>
          <router-link to="/logs" class="text-xs" style="color:#0ea5e9">查看全部 →</router-link>
        </div>

        <div v-if="loading" class="empty-state">
          <div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
        </div>
        <div v-else-if="recentLogs.length === 0" class="empty-state">
          <ScrollText :size="32" />
          <p class="text-sm">暂无日志</p>
        </div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="log in recentLogs"
            :key="log.id"
            class="flex items-start gap-3 p-3 rounded-lg"
            style="background:var(--bg-base); border:1px solid var(--border-light)"
          >
            <span class="badge flex-shrink-0 mt-0.5" :class="getLevelBadge(log.level)">{{ log.level.toUpperCase() }}</span>
            <div class="flex flex-col gap-0.5 min-w-0">
              <p class="text-sm truncate" style="color:var(--text-muted)">{{ log.message }}</p>
              <span class="text-xs" style="color:var(--text-faint)">{{ formatDate(log.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 账号健康状态 -->
    <div class="card">
      <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">账号健康状态</h3>
      <div class="grid grid-cols-6 gap-3">
        <div
          v-for="account in accounts.slice(0, 12)"
          :key="account.id"
          class="flex flex-col items-center gap-2 p-3 rounded-lg"
          style="background:var(--bg-base); border:1px solid var(--border-light)"
        >
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
            :style="getAccountCircleStyle(account.status)">
            {{ account.username.slice(0, 1).toUpperCase() }}
          </div>
          <span class="text-xs text-center truncate w-full" style="color:var(--text-muted)">{{ account.username }}</span>
          <div class="w-2 h-2 rounded-full" :class="getStatusDot(account.status)"></div>
        </div>
        <div v-if="accounts.length === 0" class="col-span-6 empty-state">
          <Users :size="24" />
          <p class="text-sm">尚未添加账号</p>
        </div>
      </div>
    </div>

    <!-- 简易矩阵视图（按分组） -->
    <div class="card">
      <h3 class="text-sm font-semibold mb-3" style="color:var(--text-primary)">矩阵视图（按分组快速总览）</h3>
      <div v-if="groupRows.length === 0" class="empty-state">
        <Users :size="24" />
        <p class="text-sm">尚未为账号设置分组，可在「账号管理」中给账号添加分组名（如：财经矩阵 / 生活矩阵）。</p>
      </div>
      <div v-else class="flex flex-col gap-2">
        <div
          v-for="row in groupRows"
          :key="row.name"
          class="flex items-center justify-between px-3 py-2 rounded-lg"
          style="background:var(--bg-base); border:1px solid var(--border-light)"
        >
          <div class="flex items-center gap-2">
            <span class="badge badge-gray">{{ row.name || '未分组' }}</span>
            <span class="text-xs" style="color:var(--text-faint)">{{ row.total }} 个账号</span>
          </div>
          <div class="flex items-center gap-2 text-xs">
            <span class="badge badge-pink">INS {{ row.ins }}</span>
            <span class="badge badge-red">YT {{ row.yt }}</span>
            <span class="badge badge-green">正常 {{ row.active }}</span>
            <span class="badge badge-yellow">限流 {{ row.limited }}</span>
            <span class="badge badge-red">封禁 {{ row.suspended }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Users, Image, Clock, CheckCircle, CalendarDays, ScrollText } from 'lucide-vue-next'
import { accountsApi, materialsApi, tasksApi, logsApi } from '@/api'
import dayjs from 'dayjs'
import isToday from 'dayjs/plugin/isToday'
dayjs.extend(isToday)

const loading = ref(true)
const accounts = ref<any[]>([])
const materials = ref<any[]>([])
const tasks = ref<any[]>([])
const recentLogs = ref<any[]>([])

// 账号 ID → 平台映射
const accountMap = computed(() => {
  const m: Record<number, any> = {}
  accounts.value.forEach(a => { m[a.id] = a })
  return m
})

const stats = computed(() => ({
  totalAccounts: accounts.value.length,
  insAccounts: accounts.value.filter(a => a.platform === 'instagram').length,
  ytAccounts: accounts.value.filter(a => a.platform === 'youtube').length,
  totalMaterials: materials.value.length,
  readyMaterials: materials.value.filter(m => m.status === 'ready').length,
  pendingTasks: tasks.value.filter(t => t.status === 'pending').length,
  queuedTasks: tasks.value.filter(t => t.status === 'queued').length,
  todaySuccess: tasks.value.filter(t => t.status === 'success' && dayjs(t.actual_executed_at).isToday()).length,
  todayFailed: tasks.value.filter(t => t.status === 'failed' && dayjs(t.updated_at).isToday()).length,
}))

const groupRows = computed(() => {
  const map: Record<string, { name: string; total: number; ins: number; yt: number; active: number; suspended: number; limited: number }> = {}
  accounts.value.forEach(a => {
    const key = a.group_name || '未分组'
    if (!map[key]) {
      map[key] = { name: key, total: 0, ins: 0, yt: 0, active: 0, suspended: 0, limited: 0 }
    }
    const row = map[key]
    row.total += 1
    if (a.platform === 'instagram') row.ins += 1
    if (a.platform === 'youtube') row.yt += 1
    if (a.status === 'active') row.active += 1
    if (a.status === 'suspended') row.suspended += 1
    if (a.status === 'limited') row.limited += 1
  })
  return Object.values(map)
})

const upcomingTasks = computed(() =>
  tasks.value
    .filter(t => ['pending', 'queued', 'running'].includes(t.status))
    .slice(0, 6)
)

function formatDate(d: string) { return dayjs(d).format('MM-DD HH:mm') }

function getPlatformLabel(accountId: number) {
  const a = accountMap.value[accountId]
  return a?.platform === 'instagram' ? '📸 INS' : '▶ YT'
}
function getPlatformBadge(accountId: number) {
  const a = accountMap.value[accountId]
  return a?.platform === 'instagram' ? 'badge-pink' : 'badge-red'
}
function getStatusLabel(s: string) {
  return { pending: '等待', queued: '排队', running: '执行中', success: '成功', failed: '失败', cancelled: '已取消' }[s] || s
}
function getStatusBadge(s: string) {
  return { success: 'badge-green', failed: 'badge-red', running: 'badge-blue', queued: 'badge-blue', pending: 'badge-gray', cancelled: 'badge-gray' }[s] || 'badge-gray'
}
function getLevelBadge(l: string) {
  return { success: 'badge-green', error: 'badge-red', warning: 'badge-yellow', info: 'badge-blue' }[l] || 'badge-gray'
}
function getStatusDot(s: string) {
  return { active: 'bg-green-500', suspended: 'bg-red-500', limited: 'bg-yellow-500', unknown: 'bg-gray-500' }[s] || 'bg-gray-500'
}
function getAccountCircleStyle(s: string) {
  const styles: Record<string, string> = {
    active: 'background:#052e16; color:#4ade80; border:1px solid #166534',
    suspended: 'background:#450a0a; color:#f87171; border:1px solid #991b1b',
    limited: 'background:#422006; color:#fbbf24; border:1px solid #92400e',
    unknown: 'background:var(--bg-surface); color:var(--text-muted); border:1px solid var(--border)',
  }
  return styles[s] || styles.unknown
}

onMounted(async () => {
  loading.value = true
  try {
    ;[accounts.value, materials.value, tasks.value, recentLogs.value] = await Promise.all([
      accountsApi.list({ limit: 200 }) as Promise<any[]>,
      materialsApi.list({ limit: 200 }) as Promise<any[]>,
      tasksApi.list({ limit: 200 }) as Promise<any[]>,
      logsApi.list({ limit: 8 }) as Promise<any[]>,
    ])
  } finally {
    loading.value = false
  }
})
</script>
