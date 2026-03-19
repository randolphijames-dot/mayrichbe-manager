<template>
  <div class="flex flex-col gap-4">
    <!-- 筛选栏 -->
    <div class="flex items-center gap-2">
      <select v-model="filterLevel" class="input text-sm" style="width:120px">
        <option value="">全部级别</option>
        <option value="success">成功</option>
        <option value="info">信息</option>
        <option value="warning">警告</option>
        <option value="error">错误</option>
      </select>
      <input v-model="filterEvent" class="input text-sm" style="width:220px" placeholder="事件类型（如 publish_success）" />
      <button class="btn btn-secondary btn-sm" @click="loadLogs"><RefreshCw :size="13" />刷新</button>
      <span class="text-xs ml-auto" style="color:var(--text-faint)">共 {{ logs.length }} 条</span>
    </div>

    <!-- 日志列表 -->
    <div class="card" style="padding:0; overflow:hidden">
      <div v-if="loading" class="empty-state" style="padding:60px">
        <div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
      </div>
      <div v-else-if="logs.length === 0" class="empty-state" style="padding:60px">
        <ScrollText :size="32" />
        <p class="text-sm">暂无日志</p>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th style="width:50px">ID</th>
            <th style="width:80px">级别</th>
            <th style="width:160px">事件</th>
            <th>消息</th>
            <th style="width:70px">账号</th>
            <th style="width:70px">任务</th>
            <th style="width:90px">详情</th>
            <th style="width:130px">时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td class="text-xs" style="color:var(--text-faint)">{{ log.id }}</td>
            <td><span class="badge" :class="levelBadge(log.level)">{{ log.level.toUpperCase() }}</span></td>
            <td class="font-mono text-xs" style="color:var(--text-muted)">{{ log.event }}</td>
            <td class="text-sm" style="color:var(--text-muted); max-width:300px">
              <span :title="log.message">{{ log.message.slice(0, 80) }}{{ log.message.length > 80 ? '...' : '' }}</span>
            </td>
            <td class="text-xs text-center" style="color:var(--text-faint)">{{ log.account_id || '—' }}</td>
            <td class="text-xs text-center" style="color:var(--text-faint)">{{ log.task_id || '—' }}</td>
            <td>
              <button v-if="log.detail" class="btn btn-ghost btn-sm" @click="showDetail(log)">查看</button>
              <span v-else class="text-xs" style="color:var(--text-muted)">—</span>
            </td>
            <td class="text-xs" style="color:var(--text-faint)">{{ formatDate(log.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 详情 Modal -->
    <Teleport to="body">
      <div v-if="detailLog" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
        <div class="card" style="max-width:600px; width:100%; max-height:80vh; overflow-y:auto">
          <div class="flex items-center justify-between mb-4">
            <div>
              <span class="badge" :class="levelBadge(detailLog.level)">{{ detailLog.level.toUpperCase() }}</span>
              <span class="text-sm ml-2 font-mono" style="color:var(--text-muted)">{{ detailLog.event }}</span>
            </div>
            <button @click="detailLog = null" style="color:var(--text-faint)"><X :size="18" /></button>
          </div>
          <p class="text-sm mb-3" style="color:var(--text-primary)">{{ detailLog.message }}</p>
          <pre class="text-xs rounded-lg p-4 overflow-x-auto" style="background:var(--bg-base); color:var(--text-muted); border:1px solid var(--border-light)">{{ detailLog.detail }}</pre>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { RefreshCw, ScrollText, X } from 'lucide-vue-next'
import { logsApi } from '@/api'
import dayjs from 'dayjs'

const loading = ref(false)
const logs = ref<any[]>([])
const filterLevel = ref('')
const filterEvent = ref('')
const detailLog = ref<any>(null)

function levelBadge(l: string) {
  return { success: 'badge-green', error: 'badge-red', warning: 'badge-yellow', info: 'badge-blue' }[l] || 'badge-gray'
}
function formatDate(d: string) { return dayjs(d).format('MM-DD HH:mm:ss') }
function showDetail(log: any) { detailLog.value = log }

async function loadLogs() {
  loading.value = true
  try {
    const params: any = { limit: 200 }
    if (filterLevel.value) params.level = filterLevel.value
    if (filterEvent.value) params.event = filterEvent.value
    logs.value = await logsApi.list(params) as any[]
  } finally { loading.value = false }
}

let debounceTimer: any
watch([filterLevel, filterEvent], () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadLogs, 300)
})
onMounted(loadLogs)
</script>
