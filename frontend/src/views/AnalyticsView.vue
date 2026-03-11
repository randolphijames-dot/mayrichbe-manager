<template>
  <div class="flex flex-col gap-4">
    <!-- 总体成功率 -->
    <div class="grid grid-cols-4 gap-4">
      <div class="stat-card" v-for="s in overallStats" :key="s.label">
        <div class="flex items-center justify-between">
          <span class="stat-label">{{ s.label }}</span>
          <component :is="s.icon" :size="16" :style="`color:${s.color}`" />
        </div>
        <div class="stat-value" :style="`color:${s.color}`">{{ s.value }}</div>
        <span class="text-xs" style="color:var(--text-faint)">{{ s.sub }}</span>
      </div>
    </div>

    <!-- 平台分布 + 账号分组 -->
    <div class="grid grid-cols-2 gap-4">
      <div class="card">
        <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">平台发布分布</h3>
        <div class="flex flex-col gap-3">
          <div v-for="p in platformStats" :key="p.name">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm" style="color:var(--text-muted)">{{ p.name }}</span>
              <span class="text-sm font-medium" style="color:var(--text-primary)">{{ p.count }} 次 ({{ p.rate }}%)</span>
            </div>
            <div class="h-2 rounded-full overflow-hidden" style="background:var(--bg-base)">
              <div class="h-full rounded-full transition-all duration-500" :style="`width:${p.rate}%; background:${p.color}`"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">账号状态分布</h3>
        <div class="flex flex-col gap-2">
          <div v-for="s in accountStatusDist" :key="s.status" class="flex items-center justify-between p-2 rounded-lg" style="background:var(--bg-base)">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full" :class="s.dot"></div>
              <span class="text-sm" style="color:var(--text-muted)">{{ s.label }}</span>
            </div>
            <span class="badge" :class="s.badge">{{ s.count }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近 7 天每日发布量 -->
    <div class="card">
      <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">最近 7 天发布趋势</h3>
      <div v-if="loading" class="empty-state" style="padding:40px">
        <div class="w-5 h-5 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
      </div>
      <div v-else class="flex items-end gap-2" style="height:120px">
        <div
          v-for="day in dailyData"
          :key="day.date"
          class="flex-1 flex flex-col items-center justify-end gap-1"
        >
          <span class="text-xs" style="color:var(--text-faint)">{{ day.total }}</span>
          <div class="w-full rounded-t-md transition-all duration-500 flex flex-col" :style="`height:${day.barH}px`">
            <div class="rounded-t-md flex-1" style="background:#0ea5e9; opacity:0.8"></div>
            <div v-if="day.failed > 0" :style="`height:${Math.round(day.barH * day.failed / Math.max(day.total,1))}px; background:#ef4444`"></div>
          </div>
          <span class="text-xs" style="color:var(--text-faint)">{{ day.label }}</span>
        </div>
      </div>
      <div class="flex items-center gap-4 mt-2">
        <div class="flex items-center gap-1"><div class="w-3 h-3 rounded" style="background:#0ea5e9"></div><span class="text-xs" style="color:var(--text-faint)">成功</span></div>
        <div class="flex items-center gap-1"><div class="w-3 h-3 rounded" style="background:#ef4444"></div><span class="text-xs" style="color:var(--text-faint)">失败</span></div>
      </div>
    </div>

    <!-- 账号发布排行 -->
    <div class="card">
      <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">账号发布排行（按成功次数）</h3>
      <div v-if="topAccounts.length === 0" class="empty-state" style="padding:40px">
        <BarChart2 :size="28" />
        <p class="text-sm">暂无发布数据</p>
      </div>
      <div v-else class="flex flex-col gap-2">
        <div v-for="(a, i) in topAccounts" :key="a.id" class="flex items-center gap-3 p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border-light)">
          <span class="text-lg font-bold w-6" :style="i < 3 ? 'color:#fbbf24' : 'color:var(--text-faint)'">{{ i+1 }}</span>
          <div class="flex-1">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm font-medium" style="color:var(--text-primary)">{{ a.username }}</span>
              <span class="text-sm" style="color:var(--text-faint)">{{ a.success }} / {{ a.total }}</span>
            </div>
            <div class="h-1.5 rounded-full overflow-hidden" style="background:var(--bg-surface)">
              <div class="h-full rounded-full" :style="`width:${a.rate}%; background:${a.rate > 80 ? '#4ade80' : a.rate > 50 ? '#fbbf24' : '#f87171'}`"></div>
            </div>
          </div>
          <span class="text-sm font-bold" :style="`color:${a.rate > 80 ? '#4ade80' : a.rate > 50 ? '#fbbf24' : '#f87171'}`">{{ a.rate }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { BarChart2, CheckCircle, XCircle, TrendingUp, Users } from 'lucide-vue-next'
import { accountsApi, tasksApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(true)
const tasks = ref<any[]>([])
const accounts = ref<any[]>([])

const successTasks = computed(() => tasks.value.filter(t => t.status === 'success'))
const failedTasks = computed(() => tasks.value.filter(t => t.status === 'failed'))
const successRate = computed(() => {
  const total = successTasks.value.length + failedTasks.value.length
  return total > 0 ? Math.round(successTasks.value.length / total * 100) : 0
})

const overallStats = computed(() => [
  { label: '总发布成功', value: successTasks.value.length, sub: '累计', icon: CheckCircle, color: '#4ade80' },
  { label: '总发布失败', value: failedTasks.value.length, sub: '累计', icon: XCircle, color: '#f87171' },
  { label: '整体成功率', value: successRate.value + '%', sub: '越高越好', icon: TrendingUp, color: '#0ea5e9' },
  { label: '活跃账号', value: accounts.value.filter(a => a.status === 'active').length, sub: `/ ${accounts.value.length} 总账号`, icon: Users, color: '#a78bfa' },
])

const platformStats = computed(() => {
  const insDone = tasks.value.filter(t => t.status === 'success' && t.platform === 'instagram').length
  const ytDone = tasks.value.filter(t => t.status === 'success' && t.platform === 'youtube').length
  const total = insDone + ytDone || 1
  return [
    { name: '📸 Instagram', count: insDone, rate: Math.round(insDone/total*100), color: '#f472b6' },
    { name: '▶ YouTube', count: ytDone, rate: Math.round(ytDone/total*100), color: '#ef4444' },
  ]
})

const accountStatusDist = computed(() => {
  const statusMap: Record<string, { label: string; dot: string; badge: string; count: number }> = {
    active: { label: '正常', dot: 'bg-green-500', badge: 'badge-green', count: 0 },
    suspended: { label: '封禁', dot: 'bg-red-500', badge: 'badge-red', count: 0 },
    limited: { label: '限流', dot: 'bg-yellow-500', badge: 'badge-yellow', count: 0 },
    unknown: { label: '未检测', dot: 'bg-gray-500', badge: 'badge-gray', count: 0 },
  }
  accounts.value.forEach(a => { if (statusMap[a.status]) statusMap[a.status].count++ })
  return Object.values(statusMap)
})

const dailyData = computed(() => {
  const days = []
  const maxVal = 10
  for (let i = 6; i >= 0; i--) {
    const date = dayjs().subtract(i, 'day').format('YYYY-MM-DD')
    const dayTasks = tasks.value.filter(t => t.actual_executed_at && dayjs(t.actual_executed_at).format('YYYY-MM-DD') === date)
    const success = dayTasks.filter(t => t.status === 'success').length
    const failed = dayTasks.filter(t => t.status === 'failed').length
    const total = success + failed
    days.push({ date, label: dayjs(date).format('M/D'), total, success, failed, barH: Math.max(4, Math.round(total / maxVal * 100)) })
  }
  return days
})

const topAccounts = computed(() => {
  const map: Record<number, { id: number; username: string; success: number; total: number; rate: number }> = {}
  tasks.value.forEach(t => {
    if (!map[t.account_id]) {
      const a = accounts.value.find(a => a.id === t.account_id)
      map[t.account_id] = { id: t.account_id, username: a?.username || `#${t.account_id}`, success: 0, total: 0, rate: 0 }
    }
    map[t.account_id].total++
    if (t.status === 'success') map[t.account_id].success++
  })
  return Object.values(map)
    .map(a => ({ ...a, rate: a.total > 0 ? Math.round(a.success / a.total * 100) : 0 }))
    .sort((a, b) => b.success - a.success)
    .slice(0, 10)
})

onMounted(async () => {
  loading.value = true
  try {
    ;[tasks.value, accounts.value] = await Promise.all([
      tasksApi.list({ limit: 1000 }) as Promise<any[]>,
      accountsApi.list({ limit: 500 }) as Promise<any[]>,
    ])
  } finally { loading.value = false }
})
</script>
