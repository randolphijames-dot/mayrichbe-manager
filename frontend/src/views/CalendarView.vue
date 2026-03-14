<template>
  <div class="flex flex-col gap-4">
    <!-- 视图切换 + 月份导航 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <!-- 视图模式切换 -->
        <div class="flex gap-1 p-1 rounded-lg" style="background:var(--bg-hover)">
          <button
            class="btn btn-sm"
            :class="viewMode === 'calendar' ? 'btn-primary' : 'btn-ghost'"
            @click="viewMode = 'calendar'"
          >日历视图</button>
          <button
            class="btn btn-sm"
            :class="viewMode === 'account' ? 'btn-primary' : 'btn-ghost'"
            @click="viewMode = 'account'"
          >账号×日期</button>
        </div>

        <div class="w-px h-5" style="background:var(--border)"></div>

        <!-- 日期导航 -->
        <button class="btn btn-ghost btn-sm" @click="prevPeriod"><ChevronLeft :size="14" /></button>
        <h2 class="text-base font-semibold" style="color:var(--text-primary)">{{ currentPeriodLabel }}</h2>
        <button class="btn btn-ghost btn-sm" @click="nextPeriod"><ChevronRight :size="14" /></button>
        <button class="btn btn-secondary btn-sm" @click="goToday">今天</button>

        <!-- 账号视图专用：分组筛选 -->
        <template v-if="viewMode === 'account'">
          <div class="w-px h-5" style="background:var(--border)"></div>
          <select v-model="filterGroup" class="input text-sm" style="width:130px">
            <option value="">全部分组</option>
            <option v-for="g in allGroups" :key="g" :value="g">{{ g }}</option>
          </select>
        </template>
      </div>
      <div class="flex items-center gap-2 text-xs" style="color:var(--text-faint)">
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#0ea5e9"></span>排队/等待</span>
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#4ade80"></span>成功</span>
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#f87171"></span>失败</span>
        <span class="flex items-center gap-1"><span class="w-2 h-2 rounded-full" style="background:#a78bfa"></span>执行中</span>
      </div>
    </div>

    <!-- 日历视图：月度日历网格 -->
    <div v-if="viewMode === 'calendar'" class="card" style="padding:0; overflow:hidden">
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

    <!-- 账号视图：账号×日期二维表格 -->
    <div v-else-if="viewMode === 'account'" class="card" style="padding:0; overflow:auto; max-height:700px">
      <table class="table" style="min-width:100%">
        <thead style="position:sticky; top:0; z-index:10; background:var(--bg-card)">
          <tr>
            <th style="min-width:150px; position:sticky; left:0; background:var(--bg-card); z-index:11">账号</th>
            <th v-for="date in accountViewDates" :key="date" style="min-width:130px; text-align:center">
              <div class="flex flex-col items-center gap-0.5">
                <span class="text-xs" style="color:var(--text-muted)">{{ dayjs(date).format('MM-DD') }}</span>
                <span class="text-xs font-normal" style="color:var(--text-faint)">{{ weekDays[dayjs(date).day()] }}</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="account in displayedAccounts" :key="account.id">
            <td style="position:sticky; left:0; background:var(--bg-card); z-index:9">
              <div class="flex flex-col gap-1">
                <div class="flex items-center gap-2">
                  <span class="badge" :class="account.platform === 'instagram' ? 'badge-pink' : 'badge-red'">
                    {{ account.platform === 'instagram' ? '📸' : '▶' }}
                  </span>
                  <span class="text-sm font-medium" style="color:var(--text-primary)">{{ account.username }}</span>
                </div>
                <span v-if="account.group_name" class="text-xs" style="color:var(--text-faint)">{{ account.group_name }}</span>
              </div>
            </td>
            <td v-for="date in accountViewDates" :key="date" style="vertical-align:top; padding:8px">
              <div class="flex flex-col gap-1">
                <div
                  v-for="task in getTasksForAccountDate(account.id, date)"
                  :key="task.id"
                  class="text-xs px-2 py-1 rounded cursor-pointer transition-all"
                  :style="`background:${taskColor(task.status)}22; color:${taskColor(task.status)}; border:1px solid ${taskColor(task.status)}44`"
                  :title="`素材#${task.material_id} - ${getStatusLabel(task.status)}`"
                  @click="selectTask(task)"
                >
                  <div class="flex items-center justify-between gap-1">
                    <span>{{ dayjs(task.scheduled_at).format('HH:mm') }}</span>
                    <span>{{ getStatusEmoji(task.status) }}</span>
                  </div>
                </div>
                <button
                  v-if="getTasksForAccountDate(account.id, date).length === 0"
                  class="text-xs px-2 py-1 rounded border transition-colors"
                  style="border:1px dashed var(--border); color:var(--text-faint)"
                  @click="createTaskForAccountDate(account.id, date)"
                >+ 新建</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="displayedAccounts.length === 0" class="empty-state" style="padding:60px">
        <CalendarDays :size="32" /><p class="text-sm">没有符合筛选条件的账号</p>
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
const selectedTask = ref<any>(null)
const loading = ref(false)

// 视图模式：calendar（月度日历）或 account（账号×日期表格）
const viewMode = ref<'calendar' | 'account'>('calendar')
const filterGroup = ref('')

const weekDays = ['日', '月', '火', '水', '木', '金', '土']

// 根据视图模式动态显示不同的标签
const currentPeriodLabel = computed(() => {
  if (viewMode.value === 'calendar') {
    return currentDate.value.format('YYYY年M月')
  } else {
    // 账号视图显示7天范围
    const start = currentDate.value
    const end = currentDate.value.add(6, 'day')
    if (start.month() === end.month()) {
      return `${start.format('YYYY年M月D日')} - ${end.format('D日')}`
    } else {
      return `${start.format('M月D日')} - ${end.format('M月D日')}`
    }
  }
})

// 账号分组列表
const allGroups = computed(() => {
  const groups = new Set<string>()
  accounts.value.forEach(a => {
    if (a.group_name) groups.add(a.group_name)
  })
  return Array.from(groups).sort()
})

// 账号视图中显示的账号（根据分组筛选）
const displayedAccounts = computed(() => {
  let filtered = accounts.value.filter(a => a.is_active)
  if (filterGroup.value) {
    filtered = filtered.filter(a => a.group_name === filterGroup.value)
  }
  return filtered.sort((a, b) => {
    // 按分组、平台、用户名排序
    if (a.group_name !== b.group_name) return (a.group_name || '').localeCompare(b.group_name || '')
    if (a.platform !== b.platform) return a.platform.localeCompare(b.platform)
    return a.username.localeCompare(b.username)
  })
})

// 账号视图的日期范围（未来7天）
const accountViewDates = computed(() => {
  const dates: string[] = []
  for (let i = 0; i < 7; i++) {
    dates.push(currentDate.value.add(i, 'day').format('YYYY-MM-DD'))
  }
  return dates
})

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

// 导航函数（根据视图模式不同，步进不同）
function prevPeriod() {
  if (viewMode.value === 'calendar') {
    currentDate.value = currentDate.value.subtract(1, 'month')
  } else {
    currentDate.value = currentDate.value.subtract(7, 'day')
  }
}
function nextPeriod() {
  if (viewMode.value === 'calendar') {
    currentDate.value = currentDate.value.add(1, 'month')
  } else {
    currentDate.value = currentDate.value.add(7, 'day')
  }
}
function goToday() { currentDate.value = dayjs() }
function selectDay(cell: any) { selectedDay.value = cell }

// 获取某个账号在某个日期的所有任务
function getTasksForAccountDate(accountId: number, dateStr: string) {
  return tasks.value.filter(t => {
    return t.account_id === accountId && dayjs(t.scheduled_at).format('YYYY-MM-DD') === dateStr
  }).sort((a, b) => dayjs(a.scheduled_at).diff(dayjs(b.scheduled_at)))
}

// 选中任务（可以后续扩展为弹窗编辑）
function selectTask(task: any) {
  selectedTask.value = task
  alert(`任务详情：\n账号ID: ${task.account_id}\n素材ID: ${task.material_id}\n时间: ${dayjs(task.scheduled_at).format('YYYY-MM-DD HH:mm')}\n状态: ${getStatusLabel(task.status)}`)
}

// 为某个账号在某个日期创建新任务（占位功能）
function createTaskForAccountDate(accountId: number, dateStr: string) {
  alert(`功能开发中：\n将为账号 #${accountId} 在 ${dateStr} 创建新任务`)
  // TODO: 实现创建任务弹窗
}

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
function getStatusEmoji(s: string) {
  return { success: '✓', failed: '✗', running: '⋯', queued: '⋯', pending: '◷', cancelled: '◌' }[s] || '○'
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
