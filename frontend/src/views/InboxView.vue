<template>
  <div class="flex flex-col gap-4">

    <!-- 顶部工具栏 -->
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div class="flex items-center gap-2">
        <!-- tab 切换 -->
        <div class="flex rounded-lg overflow-hidden" style="border:1px solid var(--border)">
          <button v-for="t in tabs" :key="t.id" class="px-3 py-1.5 text-xs flex items-center gap-1.5"
            :style="currentTab === t.id ? 'background:var(--brand);color:white' : 'background:var(--bg-surface);color:var(--text-muted)'"
            @click="currentTab = t.id">
            <component :is="t.icon" :size="12" />{{ t.label }}
            <span v-if="t.id === 'comments'" class="badge badge-gray" style="font-size:10px">{{ comments.length }}</span>
            <span v-if="t.id === 'dm'" class="badge badge-gray" style="font-size:10px">{{ dms.length }}</span>
          </button>
        </div>
        <!-- 账号筛选 -->
        <select v-model="filterAccountId" class="input text-sm" style="width:160px">
          <option value="">全部账号</option>
          <option v-for="a in accounts" :key="a.id" :value="a.id">@{{ a.username }}</option>
        </select>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-secondary btn-sm" @click="refreshAll" :disabled="loading">
          <RefreshCw :size="13" :class="loading ? 'animate-spin' : ''" /> 刷新消息
        </button>
      </div>
    </div>

    <!-- 提示横幅 -->
    <div class="p-3 rounded-lg text-xs flex items-center gap-2" style="background:var(--bg-surface);border:1px solid var(--border)">
      <Info :size="13" style="color:#0ea5e9;flex-shrink:0" />
      <span style="color:var(--text-muted)">
        消息中心需要账号在「账号管理」中已保存密码。每次拉取会消耗一定时间，数据有 1 分钟缓存。
        <strong style="color:var(--text-primary)">点赞/评论/私信均会实际发送到 Instagram</strong>，请谨慎操作。
      </span>
    </div>

    <!-- 内容区：左侧消息列表 + 右侧回复框 -->
    <div class="flex gap-3" style="min-height:500px">

      <!-- 消息列表 -->
      <div class="flex-1 flex flex-col gap-2 overflow-y-auto" style="max-height:calc(100vh - 260px)">
        <div v-if="loading" class="empty-state"><div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border);border-top-color:var(--brand)"></div></div>
        <div v-else-if="currentList.length === 0" class="empty-state card" style="padding:60px">
          <MessageSquare :size="28" /><p class="text-sm">暂无消息</p>
          <p class="text-xs mt-1" style="color:var(--text-faint)">点「刷新消息」从 Instagram 拉取最新数据</p>
        </div>

        <div v-for="item in currentList" :key="item.comment_id || item.thread_id"
          class="card cursor-pointer transition-shadow hover:shadow-lg"
          :style="selected === item ? 'border-color:var(--brand)' : ''"
          style="padding:12px"
          @click="selected = item">

          <div class="flex items-start justify-between gap-2">
            <!-- 左：头像 + 内容 -->
            <div class="flex items-start gap-2 min-w-0">
              <!-- 头像占位 -->
              <div class="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold"
                style="background:var(--bg-base);border:1px solid var(--border-light);color:var(--text-muted)">
                {{ item.from_username?.[0]?.toUpperCase() || '?' }}
              </div>
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-xs font-semibold" style="color:var(--text-primary)">@{{ item.from_username }}</span>
                  <span class="badge badge-gray text-xs">@{{ item.account_username }}</span>
                  <span v-if="currentTab === 'comments'" class="badge badge-blue" style="font-size:9px">评论</span>
                  <span v-if="currentTab === 'dm'" class="badge badge-purple" style="font-size:9px">私信</span>
                </div>
                <p class="text-xs mt-1 leading-relaxed" style="color:var(--text-muted)">{{ item.text }}</p>
                <div class="flex items-center gap-3 mt-1">
                  <span class="text-xs" style="color:var(--text-faint)">{{ formatTime(item.created_at) }}</span>
                  <a v-if="item.post_url" :href="item.post_url" target="_blank"
                    class="text-xs" style="color:var(--brand)" @click.stop>查看帖子 →</a>
                </div>
              </div>
            </div>

            <!-- 右：快速回复按钮 -->
            <button class="btn btn-primary btn-sm flex-shrink-0" style="font-size:11px"
              @click.stop="selected = item; replyText = ''">回复</button>
          </div>
        </div>
      </div>

      <!-- 右侧：选中消息 + 回复框 -->
      <div v-if="selected" class="card flex flex-col gap-3" style="width:300px;flex-shrink:0;padding:14px;align-self:flex-start;position:sticky;top:0">
        <h3 class="text-xs font-semibold" style="color:var(--text-primary)">回复 @{{ selected.from_username }}</h3>

        <!-- 原消息 -->
        <div class="p-2 rounded text-xs leading-relaxed" style="background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border-light)">
          "{{ selected.text }}"
        </div>

        <!-- 快捷话术 -->
        <div>
          <p class="text-xs mb-1.5" style="color:var(--text-faint)">快捷话术：</p>
          <div class="flex flex-wrap gap-1">
            <button v-for="t in quickReplies" :key="t" class="badge badge-gray cursor-pointer hover:badge-blue"
              style="font-size:10px" @click="replyText = t">{{ t }}</button>
          </div>
        </div>

        <!-- 回复输入 -->
        <textarea v-model="replyText" class="input text-sm" rows="3"
          :placeholder="currentTab === 'dm' ? '输入私信内容...' : '输入评论内容...'" />

        <button class="btn btn-primary w-full" @click="sendReply" :disabled="!replyText.trim() || sending">
          <span v-if="sending" class="w-4 h-4 border-2 rounded-full animate-spin" style="border-color:rgba(255,255,255,0.3);border-top-color:white"></span>
          <Send v-else :size="13" />
          {{ currentTab === 'dm' ? '发送私信' : '发送评论' }}
        </button>

        <p v-if="replyResult" class="text-xs text-center" :style="replyResult.ok ? 'color:#4ade80' : 'color:#f87171'">
          {{ replyResult.msg }}
        </p>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { MessageSquare, RefreshCw, Send, Info } from 'lucide-vue-next'
import { accountsApi } from '@/api'
import axios from 'axios'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const tabs = [
  { id: 'comments', label: '评论', icon: MessageSquare },
  { id: 'dm', label: '私信 DM', icon: Send },
]
const currentTab = ref<'comments'|'dm'>('comments')
const filterAccountId = ref<number|''>('')
const accounts = ref<any[]>([])
const comments = ref<any[]>([])
const dms = ref<any[]>([])
const loading = ref(false)
const selected = ref<any>(null)
const replyText = ref('')
const sending = ref(false)
const replyResult = ref<{ ok: boolean; msg: string } | null>(null)

const quickReplies = [
  'ありがとうございます！',
  'フォローいただきありがとうございます😊',
  '詳しくはプロフィールのリンクからどうぞ！',
  'ご質問ありがとうございます、DMでお答えします！',
  'こちらもフォローよろしくお願いします✨',
]

const currentList = computed(() =>
  currentTab.value === 'comments' ? comments.value : dms.value
)

function formatTime(t: string) {
  if (!t) return '—'
  return dayjs(t).fromNow()
}

async function refreshAll() {
  loading.value = true
  selected.value = null
  try {
    // 先清除缓存
    await axios.post('/api/v1/inbox/refresh',
      filterAccountId.value ? { account_id: filterAccountId.value } : {}
    )
    // 再拉取
    const [cmts, dm] = await Promise.all([
      axios.get('/api/v1/inbox/comments', { params: filterAccountId.value ? { account_id: filterAccountId.value, limit: 50 } : { limit: 50 } }),
      axios.get('/api/v1/inbox/dm', { params: filterAccountId.value ? { account_id: filterAccountId.value, limit: 30 } : { limit: 30 } }),
    ])
    comments.value = cmts.data || []
    dms.value = dm.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function sendReply() {
  if (!selected.value || !replyText.value.trim()) return
  sending.value = true
  replyResult.value = null
  try {
    const payload: any = {
      account_id: selected.value.account_id,
      text: replyText.value,
    }
    if (currentTab.value === 'comments') {
      payload.comment_id = selected.value.comment_id
    } else {
      payload.thread_id = selected.value.thread_id
    }
    await axios.post('/api/v1/inbox/reply', payload)
    replyResult.value = { ok: true, msg: '已发送到队列，稍后执行' }
    replyText.value = ''
  } catch (e: any) {
    replyResult.value = { ok: false, msg: e?.response?.data?.detail || '发送失败' }
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  const res = await accountsApi.list({ limit: 500, platform: 'instagram' }) as any
  accounts.value = Array.isArray(res) ? res : (res?.items || res?.accounts || [])
})
</script>
