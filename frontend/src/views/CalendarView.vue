<template>
  <div class="flex flex-col gap-4">
    <!-- 月份导航 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <button class="btn btn-ghost btn-sm" @click="prevMonth"><ChevronLeft :size="14" /></button>
        <h2 class="text-base font-semibold" style="color:var(--text-primary)">{{ currentMonthLabel }}</h2>
        <button class="btn btn-ghost btn-sm" @click="nextMonth"><ChevronRight :size="14" /></button>
        <button class="btn btn-secondary btn-sm" @click="goToday">今天</button>
      </div>
      <div class="flex items-center gap-2 text-xs" style="color:var(--text-faint)">
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#0ea5e9"></span>排队/等待</span>
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#4ade80"></span>成功</span>
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#f87171"></span>失败</span>
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#a78bfa"></span>执行中</span>
      </div>
    </div>

    <!-- 日历网格 -->
    <div class="card" style="padding:0; overflow:hidden">
      <!-- 星期标题 -->
      <div class="grid" style="grid-template-columns: repeat(7, 1fr); border-bottom:1px solid var(--border)">
        <div v-for="d in weekDays" :key="d" class="text-center py-2 text-xs font-semibold" style="color:var(--text-faint)">{{ d }}</div>
      </div>

      <!-- 日期格 -->
      <div class="grid" style="grid-template-columns: repeat(7, 1fr)">
        <div
          v-for="cell in calendarCells"
          :key="cell.key"
          class="border-b border-r min-h-24 p-2 cursor-pointer transition-colors"
          style="border-color:var(--border-light)"
          :class="{ 'opacity-40': !cell.inMonth }"
          :style="cell.isToday ? 'background:var(--bg-hover)' : ''"
          @click="selectDay(cell)"
        >
          <div class="flex items-center justify-between mb-1">
            <span
              class="text-sm font-medium w-6 h-6 flex items-center justify-center rounded-full"
              :style="cell.isToday ? 'background:var(--brand); color:white' : 'color:var(--text-primary)'"
            >{{ cell.day }}</span>
            <span v-if="cell.tasks.length > 0" class="text-xs" style="color:var(--text-faint)">{{ cell.tasks.length }}</span>
          </div>
          <div class="flex flex-col gap-0.5">
            <div
              v-for="task in cell.tasks.slice(0, 3)"
              :key="task.id"
              class="text-xs px-1.5 py-0.5 rounded truncate"
              :style="`background:${taskColor(task.status)}22; color:${taskColor(task.status)}; border:1px solid ${taskColor(task.status)}44`"
            >
              {{ formatTaskLabel(task) }}
            </div>
            <span v-if="cell.tasks.length > 3" class="text-xs" style="color:var(--text-faint)">+{{ cell.tasks.length - 3 }} 更多</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 选中日期的任务详情 -->
    <div v-if="selectedDay" class="card">
      <h3 class="text-sm font-semibold mb-3" style="color:var(--text-primary)">
        {{ selectedDay.date }} 发布任务（{{ selectedDay.tasks.length }} 个）
      </h3>
      <div v-if="selectedDay.tasks.length === 0" class="empty-state" style="padding:30px">
        <CalendarDays :size="24" /><p class="text-sm">当天无发布任务</p>
      </div>
      <div v-else class="flex flex-col gap-2">
        <div
          v-for="task in selectedDay.tasks"
          :key="task.id"
          class="flex items-center justify-between p-3 rounded-lg"
          style="background:var(--bg-base); border:1px solid var(--border-light)"
        >
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono" style="color:var(--text-faint)">#{{ task.id }}</span>
              <span class="badge" :class="getPlatformBadge(task.account_id)">账号 #{{ task.account_id }}</span>
              <span class="text-xs" style="color:var(--text-muted)">素材 #{{ task.material_id }}</span>
            </div>
            <span class="text-xs" style="color:var(--text-faint)">{{ dayjs(task.scheduled_at).format('HH:mm') }}</span>
          </div>
          <span class="badge" :class="getStatusBadge(task.status)">{{ getStatusLabel(task.status) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-vue-next'
import { tasksApi, accountsApi } from '@/api'
import dayjs from 'dayjs'

const tasks = ref<any[]>([])
const accounts = ref<any[]>([])
const currentDate = ref(dayjs())
const selectedDay = ref<any>(null)
const loading = ref(false)

const weekDays = ['日', '月', '火', '水', '木', '金', '土']
const currentMonthLabel = computed(() => currentDate.value.format('YYYY年M月'))

const accountMap = computed(() => {
  const m: Record<number, any> = {}
  accounts.value.forEach(a => { m[a.id] = a })
  return m
})

const calendarCells = computed(() => {
  const start = currentDate.value.startOf('month')
  const end = currentDate.value.endOf('month')
  const firstDow = start.day()
  const cells = []

  // 补前面空格
  for (let i = 0; i < firstDow; i++) {
    const d = start.subtract(firstDow - i, 'day')
    cells.push({ key: d.format('YYYY-MM-DD'), day: d.date(), inMonth: false, isToday: false, date: d.format('YYYY-MM-DD'), tasks: [] })
  }

  // 当月天数
  for (let d = start; d.isBefore(end) || d.isSame(end, 'day'); d = d.add(1, 'day')) {
    const dateStr = d.format('YYYY-MM-DD')
    const dayTasks = tasks.value.filter(t => dayjs(t.scheduled_at).format('YYYY-MM-DD') === dateStr)
    cells.push({ key: dateStr, day: d.date(), inMonth: true, isToday: d.isSame(dayjs(), 'day'), date: dateStr, tasks: dayTasks })
  }

  // 补后面空格（凑满 6 行 = 42 格）
  const remaining = 42 - cells.length
  for (let i = 1; i <= remaining; i++) {
    const d = end.add(i, 'day')
    cells.push({ key: d.format('YYYY-MM-DD'), day: d.date(), inMonth: false, isToday: false, date: d.format('YYYY-MM-DD'), tasks: [] })
  }

  return cells
})

function prevMonth() { currentDate.value = currentDate.value.subtract(1, 'month') }
function nextMonth() { currentDate.value = currentDate.value.add(1, 'month') }
function goToday() { currentDate.value = dayjs() }
function selectDay(cell: any) { selectedDay.value = cell }

function taskColor(status: string) {
  return { success: '#4ade80', failed: '#f87171', running: '#a78bfa', queued: '#0ea5e9', pending: '#0ea5e9', cancelled: '#64748b' }[status] || '#64748b'
}
function formatTaskLabel(task: any) {
  const a = accountMap.value[task.account_id]
  return `${a?.platform === 'instagram' ? '📸' : '▶'} ${dayjs(task.scheduled_at).format('HH:mm')}`
}
function getPlatformBadge(id: number) {
  return accountMap.value[id]?.platform === 'instagram' ? 'badge-pink' : 'badge-red'
}
function getStatusBadge(s: string) {
  return { success: 'badge-green', failed: 'badge-red', running: 'badge-purple', queued: 'badge-blue', pending: 'badge-blue', cancelled: 'badge-gray' }[s] || 'badge-gray'
}
function getStatusLabel(s: string) {
  return { success: '成功', failed: '失败', running: '执行中', queued: '排队', pending: '等待', cancelled: '取消' }[s] || s
}

onMounted(async () => {
  loading.value = true
  ;[tasks.value, accounts.value] = await Promise.all([
    tasksApi.list({ limit: 1000 }) as Promise<any[]>,
    accountsApi.list({ limit: 500 }) as Promise<any[]>,
  ])
  loading.value = false
})
</script>
