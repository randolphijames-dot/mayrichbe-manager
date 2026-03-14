<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div class="flex items-center gap-2">
        <h2 class="text-sm font-semibold" style="color:var(--text-primary)">发布后数据统计</h2>
        <span class="text-xs" style="color:var(--text-faint)">按播放量/点赞/评论采集并排名</span>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn btn-secondary btn-sm" @click="loadAll" :disabled="loading">
          <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" /> 刷新视图
        </button>
        <button class="btn btn-primary btn-sm" @click="refreshMetrics" :disabled="refreshing">
          <RefreshCw :size="13" :class="refreshing ? 'animate-spin' : ''" />
          {{ refreshing ? '采集中...' : '立即采集' }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-4 gap-4">
      <div class="stat-card" v-for="s in statCards" :key="s.label">
        <div class="flex items-center justify-between">
          <span class="stat-label">{{ s.label }}</span>
          <component :is="s.icon" :size="16" :style="`color:${s.color}`" />
        </div>
        <div class="stat-value" :style="`color:${s.color}`">{{ s.value }}</div>
        <span class="text-xs" style="color:var(--text-faint)">{{ s.sub }}</span>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div class="card">
        <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">平台作品分布</h3>
        <div class="flex flex-col gap-3">
          <div v-for="p in platformStats" :key="p.platform">
            <div class="flex items-center justify-between mb-1">
              <span class="text-sm" style="color:var(--text-muted)">{{ p.label }}</span>
              <span class="text-sm font-medium" style="color:var(--text-primary)">{{ p.count }} 个 ({{ p.rate }}%)</span>
            </div>
            <div class="h-2 rounded-full overflow-hidden" style="background:var(--bg-base)">
              <div class="h-full rounded-full transition-all duration-500" :style="`width:${p.rate}%; background:${p.color}`"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">今日 Top 5（增量）</h3>
        <div v-if="todayTop5.length === 0" class="empty-state" style="padding:36px">
          <Trophy :size="24" />
          <p class="text-sm">暂无今日排名数据</p>
        </div>
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="(item, idx) in todayTop5"
            :key="item.task_id"
            class="flex items-center justify-between p-2 rounded-lg"
            style="background:var(--bg-base); border:1px solid var(--border-light)"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-sm font-bold w-5" :style="idx < 3 ? 'color:#fbbf24' : 'color:var(--text-faint)'">{{ idx + 1 }}</span>
              <div class="min-w-0">
                <p class="text-xs font-medium truncate" style="color:var(--text-primary)">{{ item.account_username }}</p>
                <p class="text-xs truncate" style="color:var(--text-faint)">{{ item.material_title }}</p>
              </div>
            </div>
            <span class="badge badge-blue">+{{ item.views_delta }} 播放</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">最近 7 天增量趋势</h3>
      <div v-if="trendBars.length === 0" class="empty-state" style="padding:36px">
        <BarChart2 :size="24" />
        <p class="text-sm">暂无趋势数据</p>
      </div>
      <div v-else class="flex items-end gap-2" style="height:140px">
        <div
          v-for="day in trendBars"
          :key="day.date"
          class="flex-1 flex flex-col items-center justify-end gap-1"
        >
          <span class="text-xs" style="color:var(--text-faint)">{{ day.views_delta }}</span>
          <div class="w-full rounded-t-md transition-all duration-500" :style="`height:${day.barH}px; background:#0ea5e9`"></div>
          <span class="text-xs" style="color:var(--text-faint)">{{ day.label }}</span>
        </div>
      </div>
      <div class="flex items-center justify-between mt-3 text-xs" style="color:var(--text-faint)">
        <span>柱状图展示每日播放增量</span>
        <span>点赞/评论增量用于排名评分</span>
      </div>
    </div>

    <div class="card" style="padding:0; overflow:hidden">
      <div class="flex items-center justify-between p-3" style="border-bottom:1px solid var(--border)">
        <h3 class="text-sm font-semibold" style="color:var(--text-primary)">每日作品排名</h3>
        <div class="flex items-center gap-2">
          <input v-model="rankingDate" type="date" class="input text-sm" style="width:150px" />
          <button class="btn btn-secondary btn-sm" @click="loadRanking" :disabled="rankingLoading">
            <RefreshCw :size="13" :class="rankingLoading ? 'animate-spin' : ''" /> 查询
          </button>
        </div>
      </div>

      <div v-if="rankingLoading" class="empty-state" style="padding:48px">
        <div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
      </div>
      <div v-else-if="rankingItems.length === 0" class="empty-state" style="padding:48px">
        <Trophy :size="24" />
        <p class="text-sm">该日期暂无排名数据</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th style="width:60px">排名</th>
            <th style="width:160px">账号</th>
            <th style="width:90px">平台</th>
            <th>作品</th>
            <th style="width:120px">播放增量</th>
            <th style="width:120px">点赞增量</th>
            <th style="width:120px">评论增量</th>
            <th style="width:100px">评分</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in rankingItems" :key="item.task_id">
            <td>
              <span class="text-sm font-bold" :style="idx < 3 ? 'color:#fbbf24' : 'color:var(--text-faint)'">#{{ idx + 1 }}</span>
            </td>
            <td>
              <div class="flex flex-col gap-0.5">
                <span class="text-xs" style="color:var(--text-primary)">{{ item.account_username }}</span>
                <span class="text-xs" style="color:var(--text-faint)">任务 #{{ item.task_id }}</span>
              </div>
            </td>
            <td>
              <span class="badge" :class="item.platform === 'instagram' ? 'badge-pink' : 'badge-red'">
                {{ item.platform === 'instagram' ? 'Instagram' : 'YouTube' }}
              </span>
            </td>
            <td>
              <div class="flex flex-col gap-0.5 min-w-0">
                <span class="text-xs truncate" style="color:var(--text-muted)">{{ item.material_title }}</span>
                <a v-if="item.post_url" :href="item.post_url" target="_blank" class="text-xs" style="color:#0ea5e9">查看作品 →</a>
              </div>
            </td>
            <td><span class="badge badge-blue">+{{ item.views_delta }}</span></td>
            <td><span class="badge badge-green">+{{ item.likes_delta }}</span></td>
            <td><span class="badge badge-yellow">+{{ item.comments_delta }}</span></td>
            <td><span class="text-xs font-semibold" style="color:#a78bfa">{{ item.score }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { BarChart2, Eye, Heart, MessageCircle, RefreshCw, Trophy } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { analyticsApi } from '@/api'

const loading = ref(false)
const refreshing = ref(false)
const rankingLoading = ref(false)
const rankingDate = ref(dayjs().format('YYYY-MM-DD'))

const summary = ref<any>({
  overview: { tracked_posts: 0, total_views: 0, total_likes: 0, total_comments: 0, last_snapshot_at: null },
  platform_distribution: [],
  trend: [],
  today_top5: [],
})

const rankingItems = ref<any[]>([])

const statCards = computed(() => [
  {
    label: '已追踪作品',
    value: summary.value.overview?.tracked_posts || 0,
    sub: '近一次快照覆盖',
    icon: Trophy,
    color: '#fbbf24',
  },
  {
    label: '总播放量',
    value: summary.value.overview?.total_views || 0,
    sub: '所有作品累计',
    icon: Eye,
    color: '#0ea5e9',
  },
  {
    label: '总点赞数',
    value: summary.value.overview?.total_likes || 0,
    sub: '所有作品累计',
    icon: Heart,
    color: '#ef4444',
  },
  {
    label: '总评论数',
    value: summary.value.overview?.total_comments || 0,
    sub: '所有作品累计',
    icon: MessageCircle,
    color: '#22c55e',
  },
])

const platformStats = computed(() => {
  const items = summary.value.platform_distribution || []
  const total = items.reduce((acc: number, cur: any) => acc + (cur.count || 0), 0) || 1
  return items.map((item: any) => ({
    ...item,
    label: item.platform === 'instagram' ? '📸 Instagram' : '▶ YouTube',
    color: item.platform === 'instagram' ? '#f472b6' : '#ef4444',
    rate: Math.round(((item.count || 0) / total) * 100),
  }))
})

const todayTop5 = computed(() => summary.value.today_top5 || [])

const trendBars = computed(() => {
  const trend = summary.value.trend || []
  if (!trend.length) return []
  const maxViews = Math.max(...trend.map((d: any) => d.views_delta || 0), 1)
  return trend.map((d: any) => ({
    ...d,
    label: dayjs(d.date).format('M/D'),
    barH: Math.max(6, Math.round(((d.views_delta || 0) / maxViews) * 110)),
  }))
})

async function loadSummary() {
  const data = await analyticsApi.summary({ days: 7 }) as any
  summary.value = data || summary.value
}

async function loadRanking() {
  rankingLoading.value = true
  try {
    const data = await analyticsApi.dailyRanking({ target_date: rankingDate.value, limit: 50 }) as any
    rankingItems.value = data?.items || []
  } finally {
    rankingLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadSummary(), loadRanking()])
  } finally {
    loading.value = false
  }
}

async function refreshMetrics() {
  refreshing.value = true
  try {
    await analyticsApi.refresh({ days: 30, limit: 300 })
    await loadAll()
  } finally {
    refreshing.value = false
  }
}

onMounted(loadAll)
</script>
