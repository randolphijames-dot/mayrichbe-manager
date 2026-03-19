<template>
  <div class="flex flex-col gap-4">
    <!-- 筛选栏 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <select v-model="filterStatus" class="input text-sm" style="width:130px">
          <option value="">全部状态</option>
          <option value="pending">等待</option>
          <option value="queued">排队中</option>
          <option value="running">执行中</option>
          <option value="success">成功</option>
          <option value="failed">失败</option>
          <option value="cancelled">已取消</option>
        </select>
        <input v-model="filterAccountId" type="number" class="input text-sm" style="width:120px" placeholder="账号 ID" />
        <button class="btn btn-secondary btn-sm" @click="loadTasks"><RefreshCw :size="13" />刷新</button>
      </div>
      <div class="flex items-center gap-2 text-sm" style="color:var(--text-faint)">
        <span class="badge badge-gray">总计 {{ filteredTasks.length }}</span>
        <span class="badge badge-yellow">待发 {{ pendingCount }}</span>
        <span class="badge badge-green">成功 {{ successCount }}</span>
        <span class="badge badge-red">失败 {{ failCount }}</span>
      </div>
    </div>

    <!-- 表格 -->
    <div class="card" style="padding:0; overflow:hidden">
      <div v-if="loading" class="empty-state" style="padding:60px">
        <div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
      </div>
      <div v-else-if="filteredTasks.length === 0" class="empty-state" style="padding:60px">
        <CalendarDays :size="32" />
        <p class="text-sm">暂无发布任务</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th style="width:50px">ID</th>
            <th style="width:80px">账号</th>
            <th style="width:80px">素材</th>
            <th>计划时间</th>
            <th style="width:110px">状态</th>
            <th style="width:60px">重试</th>
            <th>结果</th>
            <th style="width:150px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in filteredTasks" :key="task.id">
            <td class="text-xs" style="color:var(--text-faint)">{{ task.id }}</td>
            <td>
              <span class="badge" :class="getPlatformBadge(task.account_id)">
                #{{ task.account_id }}
              </span>
            </td>
            <td class="text-xs" style="color:var(--text-muted)">#{{ task.material_id }}</td>
            <td>
              <div class="flex flex-col gap-0.5">
                <span class="text-sm" :style="isOverdue(task) ? 'color:#f87171' : 'color:var(--text-muted)'">
                  {{ formatDate(task.scheduled_at) }}
                </span>
                <span v-if="task.random_offset_minutes > 0" class="text-xs" style="color:var(--text-faint)">
                  +{{ task.random_offset_minutes }}m 偏移
                </span>
              </div>
            </td>
            <td>
              <div class="flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="statusDot(task.status)"></div>
                <span class="text-xs" :class="statusTextClass(task.status)">{{ statusLabel(task.status) }}</span>
                <span v-if="task.status === 'running'" class="w-3 h-3 border rounded-full animate-spin flex-shrink-0" style="border-color:#1e40af; border-top-color:#60a5fa"></span>
              </div>
            </td>
            <td class="text-xs text-center" style="color:var(--text-faint)">{{ task.retry_count }}/{{ task.max_retries || 3 }}</td>
            <td>
              <a v-if="task.result_url" :href="task.result_url" target="_blank" class="text-xs" style="color:#0ea5e9">查看帖子 →</a>
              <span v-else-if="task.error_message" class="text-xs" style="color:#f87171" :title="task.error_message">
                {{ task.error_message.slice(0, 30) }}...
              </span>
              <span v-else class="text-xs" style="color:var(--text-muted)">—</span>
            </td>
            <td>
              <div class="flex gap-1">
                <button
                  v-if="['pending','queued','running'].includes(task.status)"
                  class="btn btn-ghost btn-sm"
                  @click="handleCancel(task.id)"
                >取消</button>
                <button
                  v-if="task.status === 'failed'"
                  class="btn btn-primary btn-sm"
                  @click="handleRetry(task.id)"
                >重试</button>
                <span v-if="task.status === 'success'" class="text-xs" style="color:#4ade80">✓ 完成</span>
                <span v-if="task.status === 'cancelled'" class="text-xs" style="color:var(--text-faint)">已取消</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RefreshCw, CalendarDays } from 'lucide-vue-next'
import { tasksApi, accountsApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const tasks = ref<any[]>([])
const accounts = ref<any[]>([])
const filterStatus = ref('')
const filterAccountId = ref('')

const accountMap = computed(() => {
  const m: Record<number, any> = {}
  accounts.value.forEach(a => { m[a.id] = a })
  return m
})

const filteredTasks = computed(() =>
  tasks.value.filter(t => {
    if (filterStatus.value && t.status !== filterStatus.value) return false
    if (filterAccountId.value && t.account_id !== parseInt(filterAccountId.value)) return false
    return true
  })
)

const pendingCount = computed(() => filteredTasks.value.filter(t => ['pending','queued'].includes(t.status)).length)
const successCount = computed(() => filteredTasks.value.filter(t => t.status === 'success').length)
const failCount = computed(() => filteredTasks.value.filter(t => t.status === 'failed').length)

function getPlatformBadge(accountId: number) {
  return accountMap.value[accountId]?.platform === 'instagram' ? 'badge-pink' : 'badge-red'
}
function formatDate(d: string) { return dayjs(d).format('MM-DD HH:mm') }
function isOverdue(task: any) { return task.status === 'pending' && dayjs(task.scheduled_at).isBefore(dayjs()) }
function statusLabel(s: string) {
  return { pending: '等待', queued: '排队', running: '执行中', success: '成功', failed: '失败', retrying: '重试中', cancelled: '已取消' }[s] || s
}
function statusDot(s: string) {
  return { success: 'bg-green-500', failed: 'bg-red-500', running: 'bg-blue-400', queued: 'bg-blue-400', pending: 'bg-yellow-500', cancelled: 'bg-gray-600', retrying: 'bg-yellow-500' }[s] || 'bg-gray-600'
}
function statusTextClass(s: string) {
  return { success: 'text-green-400', failed: 'text-red-400', running: 'text-blue-400', queued: 'text-blue-400', pending: 'text-yellow-400', cancelled: 'text-gray-500' }[s] || 'text-gray-400'
}

async function loadTasks() {
  loading.value = true
  try { tasks.value = await tasksApi.list({ limit: 500 }) as any[] }
  finally { loading.value = false }
}

async function handleCancel(id: number) {
  await tasksApi.cancel(id)
  await loadTasks()
}
async function handleRetry(id: number) {
  await tasksApi.retry(id)
  await loadTasks()
}

onMounted(async () => {
  await Promise.all([loadTasks(), accountsApi.list({ limit: 500 }).then(r => { accounts.value = r as any[] })])
})
</script>
