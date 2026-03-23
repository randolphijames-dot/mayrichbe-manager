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
                {{ accountMap[task.account_id]?.name || '#' + task.account_id }}
              </span>
            </td>
            <td class="text-xs" style="color:var(--text-muted); max-width:200px" :title="materialDisplayName(task.material_id)">
              <span class="truncate block">{{ materialDisplayName(task.material_id) }}</span>
            </td>
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
                  v-if="['pending','queued'].includes(task.status)"
                  class="btn btn-secondary btn-sm"
                  @click="openEditTask(task)"
                >编辑</button>
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
  <!-- 编辑任务 Modal -->
  <Teleport to="body">
    <div v-if="editingTask" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
      <div class="card" style="max-width:480px; width:100%">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold" style="color:var(--text-primary)">编辑任务 #{{ editingTask.id }}</h3>
          <button @click="editingTask = null" style="color:var(--text-faint)"><X :size="18" /></button>
        </div>
        <div class="flex flex-col gap-3">
          <div>
            <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">发布时间</label>
            <input v-model="editForm.scheduled_at" type="datetime-local" class="input text-sm" />
          </div>
          <div>
            <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">素材</label>
            <select v-model="editForm.material_id" class="input text-sm">
              <option v-for="m in materials" :key="m.id" :value="m.id">
                #{{ m.id }} {{ m.title || '素材' }}
              </option>
            </select>
          </div>
          <div>
            <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">备注</label>
            <input v-model="editForm.notes" class="input text-sm" placeholder="可选备注" />
          </div>
        </div>
        <div class="flex justify-end gap-2 mt-4">
          <button class="btn btn-ghost" @click="editingTask = null">取消</button>
          <button class="btn btn-primary" @click="handleEditSave" :disabled="editSaving">
            <span v-if="editSaving" class="w-4 h-4 border-2 rounded-full animate-spin" style="border-color:rgba(255,255,255,0.3); border-top-color:white"></span>
            保存
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive } from 'vue'
import { RefreshCw, CalendarDays, X } from 'lucide-vue-next'
import { tasksApi, accountsApi, materialsApi } from '@/api'
import { toBackendScheduled, fmtScheduled } from '@/composables/timezone'
import dayjs from 'dayjs'

const loading = ref(false)
const tasks = ref<any[]>([])
const accounts = ref<any[]>([])
const materials = ref<any[]>([])
const filterStatus = ref('')
const filterAccountId = ref('')
const editingTask = ref<any>(null)
const editForm = reactive({ scheduled_at: '', notes: '', material_id: 0 })
const editSaving = ref(false)

const accountMap = computed(() => {
  const m: Record<number, any> = {}
  accounts.value.forEach(a => { m[a.id] = a })
  return m
})

const materialMap = computed(() => {
  const m: Record<number, any> = {}
  materials.value.forEach(mat => { m[mat.id] = mat })
  return m
})

function materialDisplayName(materialId: number) {
  const mat = materialMap.value[materialId]
  if (!mat) return '#' + materialId
  if (mat.caption) return mat.caption.length > 30 ? mat.caption.slice(0, 30) + '...' : mat.caption
  if (mat.title) return mat.title
  return '素材 #' + mat.id
}

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
function formatDate(d: string) { return fmtScheduled(d) }
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

function openEditTask(task: any) {
  editingTask.value = task
  // 显示时需要把存储的时间转回用户时区显示
  // scheduled_at 按后端+8时间存储，这里直接用 dayjs 加回去
  const adj = (Number(localStorage.getItem('sm_tz_offset') || 9)) - 8
  const displayTime = dayjs(task.scheduled_at).add(adj, 'hour').format('YYYY-MM-DDTHH:mm')
  editForm.scheduled_at = displayTime
  editForm.notes = task.notes || ''
  editForm.material_id = task.material_id
}

async function handleEditSave() {
  if (!editingTask.value) return
  editSaving.value = true
  try {
    const adj = (Number(localStorage.getItem('sm_tz_offset') || 9)) - 8
    const backendTime = dayjs(editForm.scheduled_at).subtract(adj, 'hour').format('YYYY-MM-DDTHH:mm') + ':00'
    await tasksApi.update(editingTask.value.id, {
      scheduled_at: backendTime,
      notes: editForm.notes || null,
      material_id: editForm.material_id || undefined,
    })
    editingTask.value = null
    await loadTasks()
  } finally {
    editSaving.value = false
  }
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
  await Promise.all([
    loadTasks(),
    accountsApi.list({ limit: 500 }).then(r => { accounts.value = r as any[] }),
    materialsApi.list({ limit: 500 }).then(r => { materials.value = r as any[] }),
  ])
})

let pollTimer: any
onMounted(() => {
  pollTimer = setInterval(() => {
    const hasActive = tasks.value.some(t => ['queued', 'running', 'pending'].includes(t.status))
    if (hasActive) loadTasks()
  }, 5000)
})
onUnmounted(() => { clearInterval(pollTimer) })
</script>
