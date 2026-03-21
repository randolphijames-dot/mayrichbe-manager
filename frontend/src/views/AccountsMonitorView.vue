<template>
  <div class="accounts-monitor">
    <!-- 顶部控制栏 -->
    <div class="control-bar">
      <h1>📱 多账号监控台</h1>
      <div class="controls">
        <button class="btn-primary" @click="refreshAll">🔄 刷新全部</button>
        <button class="btn-secondary" @click="toggleLayout">
          {{ layoutMode === 'grid' ? '📋 列表模式' : '🎯 网格模式' }}
        </button>
        <select v-model="filterPlatform" class="filter-select">
          <option value="">全部平台</option>
          <option value="INSTAGRAM">Instagram</option>
          <option value="YOUTUBE">YouTube</option>
        </select>
      </div>
    </div>

    <!-- 账号统计 -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-label">总账号</span>
        <span class="stat-value">{{ filteredAccounts.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">在线</span>
        <span class="stat-value online">{{ onlineCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">发布中</span>
        <span class="stat-value publishing">{{ publishingCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">离线</span>
        <span class="stat-value offline">{{ offlineCount }}</span>
      </div>
    </div>

    <!-- 多账号网格视图 -->
    <div :class="['accounts-grid', layoutMode]">
      <div
        v-for="account in filteredAccounts"
        :key="account.id"
        class="account-phone"
        :class="{ active: selectedAccount === account.id }"
        @click="selectAccount(account.id)"
      >
        <!-- 手机边框 -->
        <div class="phone-frame">
          <!-- 顶部状态栏 -->
          <div class="phone-header">
            <div class="account-badge">
              <div class="avatar-placeholder">
                {{ account.username.charAt(0).toUpperCase() }}
              </div>
              <div class="account-info">
                <div class="account-name">{{ account.username }}</div>
                <div class="account-platform">{{ account.platform }}</div>
              </div>
            </div>
            <div class="status-indicator" :class="getAccountStatus(account)">
              {{ getStatusText(account) }}
            </div>
          </div>

          <!-- 手机屏幕 -->
          <div class="phone-screen">
            <!-- 加载中 -->
            <div v-if="loading[account.id]" class="loading-state">
              <div class="spinner"></div>
              <p>加载中...</p>
            </div>

            <!-- Instagram预览 -->
            <div v-else-if="account.platform === 'INSTAGRAM'" class="instagram-preview">
              <!-- 最新帖子预览 -->
              <div v-if="latestPosts[account.id]" class="latest-post">
                <!-- 方式1: Instagram Embed iframe -->
                <div class="embed-container">
                  <iframe
                    :src="`${latestPosts[account.id].url}embed/captioned/`"
                    frameborder="0"
                    scrolling="no"
                    allowtransparency="true"
                    allow="encrypted-media"
                    style="width: 100%; min-height: 500px; border: none; background: white;"
                  ></iframe>
                </div>

                <!-- 帖子信息 -->
                <div class="post-info">
                  <a :href="latestPosts[account.id].url" target="_blank" class="post-url">
                    🔗 {{ latestPosts[account.id].url.split('/p/')[1]?.replace('/', '') }}
                  </a>
                  <button class="btn-refresh" @click.stop="refreshAccount(account.id)">🔄</button>
                </div>
              </div>

              <!-- 无帖子状态 -->
              <div v-else class="empty-state">
                <div class="instagram-icon">📸</div>
                <p>暂无发布记录</p>
                <p style="font-size: 11px; color: #999; margin-top: 8px;">
                  账号: @{{ account.username }}
                </p>
                <p style="font-size: 10px; color: #666; margin-top: 4px;">
                  💡 发布成功后会自动显示最新帖子
                </p>
              </div>
            </div>

            <!-- YouTube预览 -->
            <div v-else-if="account.platform === 'YOUTUBE'" class="youtube-preview">
              <div class="empty-state">
                <div class="youtube-icon">📹</div>
                <p>YouTube账号</p>
              </div>
            </div>
          </div>

          <!-- 底部操作栏 -->
          <div class="phone-footer">
            <button class="btn-small" @click.stop="viewAccountDetail(account)">详情</button>
            <button class="btn-small" @click.stop="refreshAccount(account.id)">刷新</button>
            <button class="btn-small btn-primary" @click.stop="createTask(account)">发布</button>
          </div>

          <!-- 最新任务状态 -->
          <div v-if="latestTasks[account.id]" class="task-status">
            <div class="task-info">
              <span class="task-label">最新任务:</span>
              <span class="task-tag" :class="latestTasks[account.id].status.toLowerCase()">
                {{ latestTasks[account.id].status }}
              </span>
              <span class="task-time">
                {{ formatTime(latestTasks[account.id].scheduled_at) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 添加账号卡片 -->
      <div class="account-phone add-account" @click="$router.push('/accounts')">
        <div class="phone-frame">
          <div class="add-content">
            <div class="add-icon">➕</div>
            <p>添加账号</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

// 数据
const accounts = ref<any[]>([])
const latestPosts = ref<Record<number, any>>({})
const latestTasks = ref<Record<number, any>>({})
const loading = ref<Record<number, boolean>>({})
const selectedAccount = ref<number | null>(null)
const layoutMode = ref('grid') // grid 或 list
const filterPlatform = ref('')
let refreshTimer: any = null

// 统计数据
const filteredAccounts = computed(() => {
  if (!filterPlatform.value) return accounts.value
  return accounts.value.filter(acc => acc.platform === filterPlatform.value)
})

const onlineCount = computed(() => {
  return filteredAccounts.value.filter(acc => getAccountStatus(acc) === 'online').length
})

const publishingCount = computed(() => {
  return filteredAccounts.value.filter(acc => {
    const task = latestTasks.value[acc.id]
    return task && (task.status === 'QUEUED' || task.status === 'RUNNING')
  }).length
})

const offlineCount = computed(() => {
  return filteredAccounts.value.filter(acc => getAccountStatus(acc) === 'offline').length
})

// 方法
const fetchAccounts = async () => {
  try {
    const res = await axios.get('/api/v1/accounts/?limit=500')
    accounts.value = res.data
    // 为每个账号获取最新帖子和任务
    accounts.value.forEach(acc => {
      fetchLatestPost(acc.id)
      fetchLatestTask(acc.id)
    })
  } catch (error) {
    console.error('获取账号列表失败', error)
  }
}

const fetchLatestPost = async (accountId: number) => {
  try {
    // 暂时从任务中获取最新发布的帖子URL
    const res = await axios.get('/api/v1/tasks/', {
      params: {
        account_id: accountId,
        status: 'success',  // 小写，匹配后端枚举值
        limit: 1
      }
    })
    if (res.data && res.data.length > 0 && res.data[0].result_url) {
      latestPosts.value[accountId] = { url: res.data[0].result_url }
    }
  } catch (error) {
    // 静默失败
    console.error(`获取账号 ${accountId} 最新帖子失败:`, error)
  }
}

const fetchLatestTask = async (accountId: number) => {
  try {
    const res = await axios.get('/api/v1/tasks/', {
      params: { limit: 1000 }
    })
    const tasks = res.data.filter((t: any) => t.account_id === accountId)
    if (tasks.length > 0) {
      latestTasks.value[accountId] = tasks[0]
    }
  } catch (error) {
    // 静默失败
  }
}

const refreshAccount = async (accountId: number) => {
  loading.value[accountId] = true
  await fetchLatestPost(accountId)
  await fetchLatestTask(accountId)
  loading.value[accountId] = false
}

const refreshAll = () => {
  fetchAccounts()
}

const selectAccount = (accountId: number) => {
  selectedAccount.value = accountId
}

const toggleLayout = () => {
  layoutMode.value = layoutMode.value === 'grid' ? 'list' : 'grid'
}

const getAccountStatus = (account: any) => {
  const task = latestTasks.value[account.id]
  if (task) {
    const status = task.status.toLowerCase()
    if (status === 'running' || status === 'queued') return 'publishing'
    if (status === 'success') return 'online'
  }
  return 'offline'
}

const getStatusText = (account: any) => {
  const status = getAccountStatus(account)
  const map: Record<string, string> = {
    online: '在线',
    publishing: '发布中',
    offline: '离线'
  }
  return map[status] || '未知'
}

const viewAccountDetail = (account: any) => {
  router.push(`/accounts`)
}

const createTask = (account: any) => {
  router.push(`/calendar`)
}

const formatTime = (dateString: string) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${Math.floor(diff / 86400000)}天前`
}

// 生命周期
onMounted(() => {
  fetchAccounts()
  // 每30秒自动刷新任务和帖子
  refreshTimer = setInterval(() => {
    accounts.value.forEach(acc => {
      fetchLatestTask(acc.id)
      fetchLatestPost(acc.id)  // 同时刷新帖子
    })
  }, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.accounts-monitor {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

/* 按钮样式 */
.btn-primary {
  padding: 10px 20px;
  background: #0095f6;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.3s;
}

.btn-primary:hover {
  background: #0077cc;
}

.btn-secondary {
  padding: 10px 20px;
  background: white;
  color: #262626;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #f7f7f7;
}

.btn-small {
  padding: 6px 12px;
  background: white;
  color: #262626;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s;
}

.btn-small.btn-primary {
  background: #0095f6;
  color: white;
  border: none;
}

.filter-select {
  padding: 10px 16px;
  background: white;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.control-bar h1 {
  margin: 0;
  font-size: 24px;
}

.controls {
  display: flex;
  gap: 12px;
}

.stats-bar {
  display: flex;
  gap: 20px;
  background: white;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 0 20px;
  border-right: 1px solid #e5e5e5;
}

.stat-item:last-child {
  border-right: none;
}

.stat-label {
  font-size: 14px;
  color: #8e8e8e;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #262626;
}

.stat-value.online {
  color: #10B981;
}

.stat-value.publishing {
  color: #F59E0B;
}

.stat-value.offline {
  color: #8e8e8e;
}

/* 网格布局 */
.accounts-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
}

.accounts-grid.list {
  grid-template-columns: 1fr;
}

.account-phone {
  cursor: pointer;
  transition: all 0.3s;
}

.account-phone:hover {
  transform: translateY(-4px);
}

.account-phone.active .phone-frame {
  border-color: #0095f6;
  box-shadow: 0 0 0 3px rgba(0, 149, 246, 0.2);
}

.phone-frame {
  background: white;
  border-radius: 24px;
  border: 3px solid #e5e5e5;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transition: all 0.3s;
}

.phone-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.account-badge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-placeholder {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  border: 2px solid white;
}

.account-info {
  display: flex;
  flex-direction: column;
}

.account-name {
  font-weight: 600;
  font-size: 14px;
}

.account-platform {
  font-size: 12px;
  opacity: 0.8;
}

.status-indicator {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.status-indicator.online {
  background: #10B981;
}

.status-indicator.publishing {
  background: #F59E0B;
  animation: pulse 2s infinite;
}

.status-indicator.offline {
  background: rgba(255,255,255,0.3);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.phone-screen {
  height: 480px;
  background: white;
  position: relative;
  overflow: hidden;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #8e8e8e;
}

.spinner {
  border: 3px solid #f3f3f3;
  border-top: 3px solid #0095f6;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.instagram-preview,
.youtube-preview {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.latest-post {
  height: 100%;
  overflow: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #8e8e8e;
  gap: 12px;
}

.instagram-icon,
.youtube-icon {
  font-size: 64px;
}

.phone-footer {
  padding: 12px 16px;
  background: #f7f7f7;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.task-status {
  padding: 12px 16px;
  background: #f0f0f0;
  border-top: 1px solid #e5e5e5;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.task-label {
  color: #8e8e8e;
}

.task-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.task-tag.success {
  background: #D1FAE5;
  color: #059669;
}

.task-tag.failed {
  background: #FEE2E2;
  color: #DC2626;
}

.task-tag.running,
.task-tag.queued {
  background: #FEF3C7;
  color: #D97706;
}

.task-time {
  color: #8e8e8e;
  margin-left: auto;
  font-size: 12px;
}

/* 添加账号卡片 */
.add-account .phone-frame {
  border: 3px dashed #d0d0d0;
  background: #fafafa;
  cursor: pointer;
  min-height: 580px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-account:hover .phone-frame {
  border-color: #0095f6;
  background: #f0f9ff;
}

.add-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #8e8e8e;
  gap: 12px;
}

.add-icon {
  font-size: 48px;
}

.add-content:hover {
  color: #0095f6;
}

/* 帖子链接 */
.post-link {
  margin-top: 8px;
  text-align: center;
}

.view-post-link {
  display: inline-block;
  padding: 8px 16px;
  background: #0095f6;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  transition: all 0.3s;
}

.view-post-link:hover {
  background: #0077cc;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 149, 246, 0.3);
}

/* Embed 容器 */
.embed-container {
  width: 100%;
  overflow: hidden;
  border-radius: 8px;
  background: white;
}

/* 帖子信息 */
.post-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.post-url {
  font-size: 11px;
  color: #0095f6;
  text-decoration: none;
  font-family: monospace;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.post-url:hover {
  text-decoration: underline;
}

.btn-refresh {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
  transition: transform 0.3s;
}

.btn-refresh:hover {
  transform: rotate(180deg);
}
</style>
