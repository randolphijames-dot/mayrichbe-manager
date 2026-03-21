<template>
  <div class="publish-status">
    <!-- 失败提醒条 -->
    <div v-if="newFailedTasks.length > 0" class="alert-bar" @click="newFailedTasks = []">
      <span>{{ newFailedTasks.length }} 个新的发布失败任务！点击关闭提醒</span>
    </div>

    <!-- 总览卡片 -->
    <div class="overview-card">
      <h2>📊 发布状态总览</h2>
      <div class="stats">
        <div class="stat-item success">
          <div class="stat-number">{{ successCount }}</div>
          <div class="stat-label">✅ 成功</div>
        </div>
        <div class="stat-item pending">
          <div class="stat-number">{{ pendingCount }}</div>
          <div class="stat-label">⏳ 进行中</div>
        </div>
        <div class="stat-item failed">
          <div class="stat-number">{{ failedCount }}</div>
          <div class="stat-label">❌ 失败</div>
        </div>
      </div>
      <div class="actions">
        <button @click="refreshAll" class="btn btn-primary">🔄 刷新全部</button>
        <span class="auto-refresh-label">{{ autoRefreshCountdown > 0 ? autoRefreshCountdown + 's 后自动刷新' : '刷新中...' }}</span>
      </div>
    </div>

    <!-- 账号发布列表 -->
    <div class="accounts-list">
      <div v-for="item in accountTasks" :key="item.account.id" class="account-card" :class="getStatusClass(item.task)">
        <!-- 账号头部 -->
        <div class="account-header">
          <div class="account-info">
            <div class="account-avatar">{{ item.account.username.charAt(0).toUpperCase() }}</div>
            <div>
              <div class="account-name">@{{ item.account.username }}</div>
              <div class="account-platform">{{ item.account.platform }}</div>
            </div>
          </div>
          <div class="status-badge" :class="getStatusClass(item.task)">
            {{ getStatusText(item.task) }}
          </div>
        </div>

        <!-- 发布成功的内容 -->
        <div v-if="item.task && item.task.status === 'success'" class="post-content">
          <!-- 帖子信息 -->
          <div class="post-info-box">
            <div class="post-title">📸 {{ displayName(item.material) }}</div>
            <div class="post-meta">
              <span>🔗 {{ getShortcode(item.task.result_url) }}</span>
              <span>📅 {{ formatTime(item.task.actual_executed_at) }}</span>
            </div>
          </div>

          <!-- 实时数据 -->
          <div v-if="item.metrics" class="metrics-box">
            <div class="metrics-header">
              <span>📊 实时数据</span>
              <span class="metrics-time">{{ formatTime(item.metrics.snapshot_at) }} 更新</span>
            </div>
            <div class="metrics-grid">
              <div class="metric-item">
                <div class="metric-icon">👁</div>
                <div class="metric-value">{{ item.metrics.views }}</div>
                <div class="metric-label">浏览</div>
              </div>
              <div class="metric-item">
                <div class="metric-icon">❤️</div>
                <div class="metric-value">{{ item.metrics.likes }}</div>
                <div class="metric-label">点赞</div>
              </div>
              <div class="metric-item">
                <div class="metric-icon">💬</div>
                <div class="metric-value">{{ item.metrics.comments }}</div>
                <div class="metric-label">评论</div>
              </div>
            </div>
            <button @click="refreshMetrics(item.task.id)" class="btn btn-small">🔄 立即更新数据</button>
          </div>

          <!-- 无数据提示 -->
          <div v-else class="no-metrics">
            <p>📊 数据采集中...</p>
            <p style="font-size: 12px; color: #999; margin-top: 4px;">系统每 6 小时自动采集数据</p>
            <button @click="refreshMetrics(item.task.id)" class="btn btn-small">🔄 立即采集</button>
          </div>

          <!-- 操作按钮 -->
          <div class="post-actions">
            <a :href="item.task.result_url" target="_blank" class="btn btn-secondary">
              📱 在 Instagram 打开
            </a>
          </div>
        </div>

        <!-- 进行中 -->
        <div v-else-if="item.task && (item.task.status === 'running' || item.task.status === 'queued')" class="pending-content">
          <div class="spinner"></div>
          <p>⏳ 正在发布...</p>
          <p style="font-size: 12px; color: #999;">预计 {{ formatTime(item.task.scheduled_at) }} 完成</p>
        </div>

        <!-- 失败 -->
        <div v-else-if="item.task && item.task.status === 'failed'" class="failed-content">
          <p>❌ 发布失败</p>
          <p class="error-message">{{ item.task.error_message }}</p>
          <button @click="retryTask(item.task.id)" class="btn btn-small btn-primary">🔄 重试</button>
        </div>

        <!-- 无任务 -->
        <div v-else class="no-task-content">
          <p>📝 暂无发布任务</p>
          <button @click="createTask(item.account)" class="btn btn-small btn-primary">➕ 创建任务</button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner-large"></div>
      <p>加载中...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const loading = ref(false)
const accountTasks = ref<any[]>([])
const newFailedTasks = ref<any[]>([])
const knownFailedIds = ref(new Set<number>())
const autoRefreshCountdown = ref(30)
let pollTimer: ReturnType<typeof setInterval> | null = null
let countdownTimer: ReturnType<typeof setInterval> | null = null

// 统计数据
const successCount = computed(() =>
  accountTasks.value.filter(item => item.task?.status === 'success').length
)
const pendingCount = computed(() =>
  accountTasks.value.filter(item =>
    item.task?.status === 'running' || item.task?.status === 'queued'
  ).length
)
const failedCount = computed(() =>
  accountTasks.value.filter(item => item.task?.status === 'failed').length
)

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    // 获取所有账号
    const accountsRes = await axios.get('/api/v1/accounts/?limit=500')
    const accounts = accountsRes.data

    // 获取所有任务
    const tasksRes = await axios.get('/api/v1/tasks/?limit=1000')
    const allTasks = tasksRes.data

    // 获取所有素材
    const materialsRes = await axios.get('/api/v1/materials/?limit=500')
    const materials = materialsRes.data

    // 获取所有数据快照
    const metricsRes = await axios.get('/api/v1/analytics/metrics-latest')
    const metricsMap = new Map()
    metricsRes.data.forEach((m: any) => {
      metricsMap.set(m.task_id, m)
    })

    // 组合数据
    accountTasks.value = accounts.map((account: any) => {
      // 获取该账号最新的任务
      const task = allTasks
        .filter((t: any) => t.account_id === account.id)
        .sort((a: any, b: any) => new Date(b.scheduled_at).getTime() - new Date(a.scheduled_at).getTime())[0]

      // 获取素材信息
      const material = task ? materials.find((m: any) => m.id === task.material_id) : null

      // 获取数据快照
      const metrics = task ? metricsMap.get(task.id) : null

      return { account, task, material, metrics }
    })

    // 检测新的失败任务
    const currentFailedIds = new Set<number>()
    const freshFailed: any[] = []
    accountTasks.value.forEach(item => {
      if (item.task?.status === 'failed') {
        currentFailedIds.add(item.task.id)
        if (!knownFailedIds.value.has(item.task.id)) {
          freshFailed.push(item)
        }
      }
    })

    if (freshFailed.length > 0) {
      newFailedTasks.value = freshFailed
      // 浏览器桌面通知
      if (Notification.permission === 'granted') {
        new Notification('发布失败提醒', {
          body: `${freshFailed.length} 个任务发布失败`,
          icon: '/favicon.ico',
        })
      }
    }
    knownFailedIds.value = currentFailedIds
  } catch (error) {
    console.error('获取数据失败', error)
  } finally {
    loading.value = false
  }
}

const refreshAll = () => {
  fetchData()
}

const refreshMetrics = async (taskId: number) => {
  try {
    await axios.post(`/api/v1/analytics/metrics/${taskId}/refresh`)
    await fetchData()
  } catch (error: any) {
    alert(error.response?.data?.detail || '刷新失败')
  }
}

const retryTask = async (taskId: number) => {
  // TODO: 实现重试逻辑
  alert('重试功能开发中')
}

const createTask = (account: any) => {
  router.push('/schedule')
}

const getStatusClass = (task: any) => {
  if (!task) return 'no-task'
  const status = task.status?.toLowerCase()
  if (status === 'success') return 'success'
  if (status === 'running' || status === 'queued') return 'pending'
  if (status === 'failed') return 'failed'
  return ''
}

const getStatusText = (task: any) => {
  if (!task) return '无任务'
  const status = task.status?.toLowerCase()
  const map: Record<string, string> = {
    success: '发布成功',
    running: '发布中',
    queued: '队列中',
    failed: '发布失败',
    pending: '等待中',
  }
  return map[status] || status
}

const getShortcode = (url: string) => {
  if (!url) return ''
  const match = url.match(/\/p\/([^/?]+)/)
  return match ? match[1] : url
}

const displayName = (material: any) => {
  if (!material) return '未命名'
  if (material.caption) return material.caption.length > 30 ? material.caption.slice(0, 30) + '...' : material.caption
  if (material.title) return material.title
  return '素材 #' + material.id
}

const formatTime = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

function startAutoRefresh() {
  autoRefreshCountdown.value = 30

  countdownTimer = setInterval(() => {
    autoRefreshCountdown.value--
    if (autoRefreshCountdown.value <= 0) {
      autoRefreshCountdown.value = 30
    }
  }, 1000)

  pollTimer = setInterval(() => {
    fetchData()
  }, 30000)
}

onMounted(() => {
  fetchData()
  startAutoRefresh()
  // 请求浏览器通知权限
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission()
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.publish-status {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.overview-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.overview-card h2 {
  margin: 0 0 20px 0;
  font-size: 20px;
  color: #333;
}

.stats {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
}

.stat-item {
  flex: 1;
  text-align: center;
  padding: 16px;
  border-radius: 8px;
  background: #f5f5f5;
}

.stat-item.success { background: #e6f7e6; }
.stat-item.pending { background: #fff8e6; }
.stat-item.failed { background: #ffe6e6; }

.stat-number {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stat-item.success .stat-number { color: #22c55e; }
.stat-item.pending .stat-number { color: #f59e0b; }
.stat-item.failed .stat-number { color: #ef4444; }

.stat-label {
  font-size: 14px;
  color: #666;
}

.actions {
  text-align: center;
}

.accounts-list {
  display: grid;
  gap: 20px;
}

.account-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  border-left: 4px solid #ddd;
}

.account-card.success { border-left-color: #22c55e; }
.account-card.pending { border-left-color: #f59e0b; }
.account-card.failed { border-left-color: #ef4444; }

.account-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #0095f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
}

.account-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.account-platform {
  font-size: 12px;
  color: #999;
}

.status-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 600;
}

.status-badge.success { background: #e6f7e6; color: #22c55e; }
.status-badge.pending { background: #fff8e6; color: #f59e0b; }
.status-badge.failed { background: #ffe6e6; color: #ef4444; }

.post-info-box {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.post-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.post-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #666;
}

.metrics-box {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.metrics-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 12px;
}

.metrics-time {
  color: #999;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}

.metric-item {
  text-align: center;
  padding: 12px;
  background: white;
  border-radius: 6px;
}

.metric-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 11px;
  color: #999;
}

.no-metrics {
  text-align: center;
  padding: 20px;
  color: #999;
}

.post-actions {
  display: flex;
  gap: 8px;
}

.pending-content, .failed-content, .no-task-content {
  text-align: center;
  padding: 20px;
  color: #666;
}

.error-message {
  font-size: 12px;
  color: #ef4444;
  margin: 8px 0;
  padding: 8px;
  background: #ffe6e6;
  border-radius: 4px;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #0095f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-primary {
  background: #0095f6;
  color: white;
}

.btn-primary:hover {
  background: #0077cc;
}

.btn-secondary {
  background: white;
  color: #333;
  border: 1px solid #ddd;
  text-decoration: none;
  display: inline-block;
}

.btn-secondary:hover {
  background: #f5f5f5;
}

.btn-small {
  padding: 6px 12px;
  font-size: 12px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  color: white;
}

.spinner-large {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(255,255,255,0.3);
  border-top: 4px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

.alert-bar {
  background: #450a0a;
  color: #f87171;
  border: 1px solid #991b1b;
  border-radius: 8px;
  padding: 12px 20px;
  margin-bottom: 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-align: center;
  animation: pulse-alert 2s infinite;
}

@keyframes pulse-alert {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.auto-refresh-label {
  display: inline-block;
  margin-left: 12px;
  font-size: 12px;
  color: #999;
}
</style>
