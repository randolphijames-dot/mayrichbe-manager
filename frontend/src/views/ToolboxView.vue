<template>
  <div class="flex flex-col gap-4">

    <!-- 卡片 1：批量养号 -->
    <div class="card" style="padding:16px">
      <h3 class="text-sm font-semibold mb-1" style="color:var(--text-primary)">批量养号</h3>
      <p class="text-xs mb-3" style="color:var(--text-faint)">
        养号会模拟真实用户行为（刷 Feed、点赞、看 Reels），新账号建议每天执行一次
      </p>

      <!-- 账号列表 -->
      <div v-if="igAccounts.length === 0" class="text-xs py-3 text-center" style="color:var(--text-faint)">
        暂无 Instagram 账号
      </div>
      <div v-else class="flex flex-col gap-1 mb-3 max-h-52 overflow-y-auto">
        <label
          v-for="acc in igAccounts"
          :key="acc.id"
          class="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer"
          style="background:var(--bg-base); border:1px solid var(--border)"
        >
          <input
            type="checkbox"
            :value="acc.id"
            v-model="selectedIds"
            style="accent-color:var(--brand)"
          />
          <span class="text-xs flex-1" style="color:var(--text-primary)">{{ acc.username }}</span>
          <span class="badge badge-gray" style="font-size:10px">
            {{ acc.publish_method === 'bitbrowser' ? 'bitbrowser' : 'instagrapi' }}
          </span>
        </label>
      </div>

      <!-- 操作按钮行 -->
      <div class="flex items-center gap-2 mb-3">
        <button
          class="btn btn-secondary btn-sm"
          @click="toggleSelectAll"
          :disabled="igAccounts.length === 0"
        >
          {{ allSelected ? '取消全选' : '全选' }}
        </button>
        <button
          class="btn btn-primary btn-sm flex items-center gap-1.5"
          :disabled="selectedIds.length === 0 || warmupLoading"
          @click="startWarmup"
        >
          <span v-if="warmupLoading" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          开始养号
          <span v-if="!warmupLoading && selectedIds.length > 0" style="opacity:0.75">（{{ selectedIds.length }} 个）</span>
        </button>
      </div>

      <!-- 成功提示 -->
      <div
        v-if="warmupSuccess"
        class="text-xs px-3 py-2 rounded mb-3"
        style="background:#052e16; color:#4ade80; border:1px solid #166534"
      >
        已触发 {{ warmupTriggeredCount }} 个账号的养号任务，正在后台执行，每账号间隔 2-5 分钟
      </div>

      <!-- 上次养号结果 -->
      <div v-if="warmupStatus" class="text-xs px-3 py-2 rounded" style="background:var(--bg-base); border:1px solid var(--border)">
        <span style="color:var(--text-muted)">上次养号：</span>
        <span style="color:var(--text-primary)">{{ warmupStatus.last_run_at || '—' }}</span>
        <span class="ml-3" style="color:#4ade80">成功 {{ warmupStatus.success_count ?? 0 }}</span>
        <span class="ml-2" style="color:#f87171">失败 {{ warmupStatus.fail_count ?? 0 }}</span>
      </div>
    </div>

    <!-- 卡片 2：通知测试 -->
    <div class="card" style="padding:16px">
      <h3 class="text-sm font-semibold mb-1" style="color:var(--text-primary)">通知测试</h3>
      <p class="text-xs mb-3" style="color:var(--text-faint)">发送测试消息到已配置的通知渠道</p>

      <div class="flex items-center gap-2">
        <!-- LINE -->
        <button
          class="btn btn-secondary btn-sm flex items-center gap-1.5"
          :disabled="lineLoading"
          @click="testNotify('line')"
        >
          <span v-if="lineLoading" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          测试 LINE 通知
        </button>
        <!-- Telegram -->
        <button
          class="btn btn-secondary btn-sm flex items-center gap-1.5"
          :disabled="telegramLoading"
          @click="testNotify('telegram')"
        >
          <span v-if="telegramLoading" class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
          测试 Telegram 通知
        </button>
      </div>

      <!-- 通知成功提示 -->
      <div
        v-if="notifySuccess"
        class="text-xs px-3 py-2 rounded mt-3"
        style="background:#052e16; color:#4ade80; border:1px solid #166534"
      >
        发送成功
      </div>
    </div>

    <!-- 卡片 3：系统配置 -->
    <div class="card" style="padding:16px">
      <h3 class="text-sm font-semibold mb-1" style="color:var(--text-primary)">系统配置</h3>
      <p class="text-xs mb-3" style="color:var(--text-faint)">当前系统配置状态（只读）</p>

      <div v-if="settingsLoading" class="flex items-center gap-2 py-2">
        <span class="inline-block w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
        <span class="text-xs" style="color:var(--text-faint)">加载中...</span>
      </div>

      <div v-else-if="settings" class="flex flex-col gap-2">
        <!-- 通知配置 -->
        <div class="flex items-center justify-between py-1.5 border-b" style="border-color:var(--border)">
          <span class="text-xs" style="color:var(--text-muted)">LINE 通知</span>
          <span v-if="settings.line_notify_configured" class="badge badge-green">已配置</span>
          <span v-else class="badge badge-gray">未配置</span>
        </div>
        <div class="flex items-center justify-between py-1.5 border-b" style="border-color:var(--border)">
          <span class="text-xs" style="color:var(--text-muted)">Telegram 通知</span>
          <span v-if="settings.telegram_configured" class="badge badge-green">已配置</span>
          <span v-else class="badge badge-gray">未配置</span>
        </div>
        <div class="flex items-center justify-between py-1.5 border-b" style="border-color:var(--border)">
          <span class="text-xs" style="color:var(--text-muted)">YouTube OAuth</span>
          <span v-if="settings.youtube_oauth_configured" class="badge badge-green">已配置</span>
          <span v-else class="badge badge-gray">未配置</span>
        </div>
        <!-- 路径 / 数值配置 -->
        <div class="flex items-center justify-between py-1.5 border-b" style="border-color:var(--border)">
          <span class="text-xs" style="color:var(--text-muted)">BitBrowser 地址</span>
          <span class="text-xs" style="color:var(--text-primary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">
            {{ settings.bitbrowser_url || '—' }}
          </span>
        </div>
        <div class="flex items-center justify-between py-1.5 border-b" style="border-color:var(--border)">
          <span class="text-xs" style="color:var(--text-muted)">上传目录</span>
          <span class="text-xs" style="color:var(--text-primary); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">
            {{ settings.upload_dir || '—' }}
          </span>
        </div>
        <div class="flex items-center justify-between py-1.5 border-b" style="border-color:var(--border)">
          <span class="text-xs" style="color:var(--text-muted)">最大文件大小</span>
          <span class="text-xs" style="color:var(--text-primary)">
            {{ settings.max_file_size_mb != null ? settings.max_file_size_mb + ' MB' : '—' }}
          </span>
        </div>
        <div class="flex items-center justify-between py-1.5">
          <span class="text-xs" style="color:var(--text-muted)">随机发布偏移</span>
          <span class="text-xs" style="color:var(--text-primary)">
            {{ settings.random_offset_minutes != null ? settings.random_offset_minutes + ' 分钟' : '—' }}
          </span>
        </div>
      </div>

      <div v-else class="text-xs py-2" style="color:var(--text-faint)">配置信息不可用</div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { accountsApi, toolsApi } from '@/api'

// ---- 卡片 1：批量养号 ----
const igAccounts = ref<any[]>([])
const selectedIds = ref<number[]>([])
const warmupLoading = ref(false)
const warmupSuccess = ref(false)
const warmupTriggeredCount = ref(0)
const warmupStatus = ref<any>(null)

const allSelected = computed(
  () => igAccounts.value.length > 0 && selectedIds.value.length === igAccounts.value.length
)

function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = igAccounts.value.map((a) => a.id)
  }
}

async function startWarmup() {
  if (selectedIds.value.length === 0 || warmupLoading.value) return
  warmupLoading.value = true
  warmupSuccess.value = false
  try {
    await toolsApi.triggerWarmup(selectedIds.value)
    warmupTriggeredCount.value = selectedIds.value.length
    warmupSuccess.value = true
    setTimeout(() => { warmupSuccess.value = false }, 5000)
  } finally {
    warmupLoading.value = false
  }
}

async function fetchWarmupStatus() {
  try {
    const data: any = await toolsApi.getSettings()
    // warmup/status 是独立接口，单独调用
    const resp: any = await fetch('/api/v1/tools/warmup/status').then((r) => {
      if (!r.ok) return null
      return r.json()
    })
    if (resp && (resp.last_run_at !== undefined || resp.success_count !== undefined)) {
      warmupStatus.value = resp
    }
  } catch {
    // 接口不存在或报错时静默忽略
  }
}

// ---- 卡片 2：通知测试 ----
const lineLoading = ref(false)
const telegramLoading = ref(false)
const notifySuccess = ref(false)

async function testNotify(channel: 'line' | 'telegram') {
  if (channel === 'line') {
    if (lineLoading.value) return
    lineLoading.value = true
  } else {
    if (telegramLoading.value) return
    telegramLoading.value = true
  }
  notifySuccess.value = false
  try {
    await toolsApi.testNotify(channel)
    notifySuccess.value = true
    setTimeout(() => { notifySuccess.value = false }, 3000)
  } finally {
    if (channel === 'line') lineLoading.value = false
    else telegramLoading.value = false
  }
}

// ---- 卡片 3：系统配置 ----
const settings = ref<any>(null)
const settingsLoading = ref(false)

async function fetchSettings() {
  settingsLoading.value = true
  try {
    settings.value = await toolsApi.getSettings() as any
  } catch {
    settings.value = null
  } finally {
    settingsLoading.value = false
  }
}

// ---- 初始化 ----
onMounted(async () => {
  const all: any[] = await accountsApi.list({ limit: 500 }) as any[]
  igAccounts.value = all.filter((a) => a.platform === 'instagram')

  // 并行加载配置和养号状态
  await Promise.all([fetchSettings(), fetchWarmupStatus()])
})
</script>
