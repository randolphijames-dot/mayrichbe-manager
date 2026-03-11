<template>
  <div class="flex flex-col gap-4">

    <!-- 顶部说明 -->
    <div class="p-3 rounded-lg flex items-start gap-2 text-xs" style="background:var(--bg-surface);border:1px solid #92400e">
      <span style="color:#fbbf24;font-size:16px;flex-shrink:0">⚠️</span>
      <div style="color:var(--text-muted)">
        <strong style="color:#fbbf24">截流功能风险提示：</strong>
        自动点赞/评论是 Instagram 官方不鼓励的行为，<strong style="color:var(--text-primary)">每账号每次限制最多 10 个互动</strong>，每次互动间隔随机 30–90 秒，每天执行次数建议 ≤ 2 次。
        新账号（<30天）请勿使用此功能。如出现频繁失败，请暂停 24 小时。
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">

      <!-- 左：任务配置 -->
      <div class="card flex flex-col gap-4">
        <h3 class="text-sm font-semibold" style="color:var(--text-primary)">新建截流任务</h3>

        <!-- 截流方式 -->
        <div>
          <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">截流方式</label>
          <div class="grid grid-cols-2 gap-2">
            <button class="p-3 rounded-lg text-left transition-all" @click="form.mode = 'hashtag'"
              :style="form.mode === 'hashtag' ? 'background:var(--brand);color:white;border:1px solid transparent' : 'background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border)'">
              <div class="text-base mb-1">🏷</div>
              <div class="text-xs font-semibold">话题标签截流</div>
              <div class="text-xs opacity-70 mt-0.5">在某个 # 标签下找帖子互动</div>
            </button>
            <button class="p-3 rounded-lg text-left transition-all" @click="form.mode = 'competitor'"
              :style="form.mode === 'competitor' ? 'background:var(--brand);color:white;border:1px solid transparent' : 'background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border)'">
              <div class="text-base mb-1">🎯</div>
              <div class="text-xs font-semibold">对标账号截流</div>
              <div class="text-xs opacity-70 mt-0.5">找某个大号的粉丝互动</div>
            </button>
          </div>
        </div>

        <!-- 目标 -->
        <div>
          <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">
            {{ form.mode === 'hashtag' ? '话题标签（不含 #）' : '对标账号用户名（不含 @）' }}
          </label>
          <input v-model="form.target" class="input text-sm"
            :placeholder="form.mode === 'hashtag' ? '例：日本財経 / 投資 / 株式市場' : '例：nikkei225_official'" />
        </div>

        <!-- 互动动作 -->
        <div>
          <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">互动动作</label>
          <div class="grid grid-cols-2 gap-2">
            <button class="p-2 rounded-lg text-center transition-all text-xs font-medium" @click="form.action = 'like'"
              :style="form.action === 'like' ? 'background:var(--brand);color:white;border:1px solid transparent' : 'background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border)'">
              ❤️ 点赞（安全）
            </button>
            <button class="p-2 rounded-lg text-center transition-all text-xs font-medium" @click="form.action = 'comment'"
              :style="form.action === 'comment' ? 'background:var(--brand);color:white;border:1px solid transparent' : 'background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border)'">
              💬 评论（引流）
            </button>
          </div>
          <p class="text-xs mt-1" style="color:var(--text-faint)">点赞风险低但引流弱；评论引流效果强但风险略高，建议和话术库搭配使用。</p>
        </div>

        <!-- 评论话术（仅评论模式显示） -->
        <div v-if="form.action === 'comment'">
          <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">评论话术（用 | 分隔多条，每次随机选一条）</label>
          <textarea v-model="form.comment_text" class="input text-sm" rows="3"
            placeholder="プロフィールにもっと情報があります！ | フォローよろしくお願いします✨ | とても参考になりました！" />
          <div class="flex flex-wrap gap-1 mt-2">
            <span class="text-xs" style="color:var(--text-faint)">模板：</span>
            <button v-for="t in commentTemplates" :key="t"
              class="badge badge-gray cursor-pointer text-xs hover:badge-blue"
              @click="addTemplate(t)">{{ t }}</button>
          </div>
        </div>

        <!-- 每账号上限 -->
        <div>
          <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">
            每账号互动上限：<span style="color:var(--brand)">{{ form.limit_per_account }}</span> 个
          </label>
          <input v-model.number="form.limit_per_account" type="range" min="1" max="10" class="w-full" style="accent-color:var(--brand)" />
          <div class="flex justify-between text-xs mt-1" style="color:var(--text-faint)">
            <span>1（最安全）</span><span>10（最多）</span>
          </div>
        </div>

        <!-- 账号选择 -->
        <div>
          <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">使用哪些账号执行截流</label>
          <div class="flex flex-wrap gap-1.5 p-3 rounded-lg" style="background:var(--bg-base);border:1px solid var(--border);min-height:44px">
            <button v-for="a in insAccounts" :key="a.id"
              class="badge cursor-pointer transition-all"
              :class="form.account_ids.includes(a.id) ? 'badge-pink' : 'badge-gray'"
              @click="toggleAccount(a.id)">
              📸 {{ a.username }}
              <span v-if="!a.ins_password_encrypted" style="color:#f87171"> ⚠️</span>
            </button>
            <span v-if="insAccounts.length === 0" class="text-xs" style="color:var(--text-faint)">暂无 Instagram 账号</span>
          </div>
          <p class="text-xs mt-1" style="color:var(--text-faint)">⚠️ 标记的账号缺少密码，无法执行。请在「账号管理」中补充密码。</p>
        </div>

        <!-- 提交 -->
        <button class="btn btn-primary" @click="startTask" :disabled="running || !canSubmit">
          <span v-if="running" class="w-4 h-4 border-2 rounded-full animate-spin" style="border-color:rgba(255,255,255,0.3);border-top-color:white"></span>
          <Zap v-else :size="14" />
          {{ running ? '执行中...' : '启动截流任务' }}
        </button>
      </div>

      <!-- 右：任务进度 + 历史 -->
      <div class="flex flex-col gap-4">

        <!-- 当前任务进度 -->
        <div v-if="currentTask" class="card">
          <h3 class="text-xs font-semibold mb-3" style="color:var(--text-primary)">当前任务进度</h3>

          <!-- 进度条 -->
          <div class="flex items-center gap-3 mb-3">
            <div class="flex-1 h-2 rounded-full overflow-hidden" style="background:var(--bg-base)">
              <div class="h-full rounded-full transition-all" style="background:var(--brand)"
                :style="`width:${currentTask.total ? Math.round(currentTask.done / currentTask.total * 100) : 0}%`"></div>
            </div>
            <span class="text-xs font-medium" style="color:var(--brand)">
              {{ currentTask.done }}/{{ currentTask.total }}
            </span>
            <span class="badge" :class="currentTask.status === 'done' ? 'badge-green' : 'badge-blue'">
              {{ currentTask.status === 'done' ? '完成' : '执行中' }}
            </span>
          </div>

          <!-- 结果列表 -->
          <div class="flex flex-col gap-1 max-h-60 overflow-y-auto">
            <div v-for="(r, i) in currentTask.results" :key="i"
              class="text-xs px-2 py-1.5 rounded flex items-center justify-between"
              :style="r.error ? 'background:var(--bg-base);color:#f87171' : 'background:var(--bg-base);color:#4ade80'">
              <span>{{ r.error ? '❌' : '✅' }} @{{ r.account }}</span>
              <span style="color:var(--text-faint)">
                {{ r.error || `互动 ${r.done} 个` }}
              </span>
            </div>
          </div>
        </div>

        <!-- 使用建议 -->
        <div class="card">
          <h3 class="text-xs font-semibold mb-3" style="color:var(--text-primary)">📖 使用建议</h3>
          <ul class="text-xs space-y-2" style="color:var(--text-muted)">
            <li>✅ <strong style="color:var(--text-primary)">话题截流适合</strong>：主动找感兴趣的用户，适合财经/投资类关键词</li>
            <li>✅ <strong style="color:var(--text-primary)">对标账号截流适合</strong>：精准抢同行的粉丝，效果最好但风险最高</li>
            <li>⚠️ <strong style="color:var(--text-primary)">点赞比评论安全</strong>：新账号建议先用「点赞」暖身 1-2 周再开评论</li>
            <li>⚠️ <strong style="color:var(--text-primary)">每天最多跑 2 次</strong>，每次间隔超过 6 小时</li>
            <li>❌ <strong style="color:var(--text-primary)">不要连续 3 天都跑</strong>，要模拟人工的不规律行为</li>
            <li>💡 <strong style="color:var(--text-primary)">话术要轮换</strong>：用 | 分隔多条评论话术，每次随机选，避免「机器人重复」被识别</li>
          </ul>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { Zap } from 'lucide-vue-next'
import { accountsApi } from '@/api'
import axios from 'axios'

const accounts = ref<any[]>([])
const insAccounts = computed(() => accounts.value.filter(a => a.platform === 'instagram'))

const form = reactive({
  mode: 'hashtag' as 'hashtag' | 'competitor',
  target: '',
  action: 'like' as 'like' | 'comment',
  comment_text: '',
  limit_per_account: 5,
  account_ids: [] as number[],
})

const running = ref(false)
const currentTask = ref<any>(null)
let pollInterval: ReturnType<typeof setInterval> | null = null

const commentTemplates = [
  'プロフィールにもっと情報があります！',
  'フォローよろしくお願いします✨',
  'とても参考になりました！',
  'DMでご質問どうぞ😊',
]

const canSubmit = computed(() =>
  form.target.trim() &&
  form.account_ids.length > 0 &&
  (form.action === 'like' || form.comment_text.trim())
)

function toggleAccount(id: number) {
  const idx = form.account_ids.indexOf(id)
  if (idx >= 0) form.account_ids.splice(idx, 1)
  else form.account_ids.push(id)
}

function addTemplate(t: string) {
  if (form.comment_text) form.comment_text += ' | ' + t
  else form.comment_text = t
}

async function startTask() {
  if (!canSubmit.value) return
  running.value = true
  currentTask.value = null

  try {
    const res = await axios.post('/api/v1/traffic/run', {
      account_ids: form.account_ids,
      mode: form.mode,
      target: form.target.trim(),
      action: form.action,
      comment_text: form.comment_text || undefined,
      limit_per_account: form.limit_per_account,
    })

    const taskKey = res.data.task_key
    currentTask.value = { status: 'running', done: 0, total: res.data.total_accounts, results: [] }

    // 轮询进度
    if (pollInterval) clearInterval(pollInterval)
    pollInterval = setInterval(async () => {
      try {
        const status = await axios.get(`/api/v1/traffic/status/${taskKey}`)
        currentTask.value = status.data
        if (status.data.status === 'done') {
          clearInterval(pollInterval!)
          running.value = false
        }
      } catch { clearInterval(pollInterval!) }
    }, 5000)

  } catch (e: any) {
    alert(e?.response?.data?.detail || '启动失败')
    running.value = false
  }
}

onMounted(async () => {
  const res = await accountsApi.list({ limit: 500 }) as any
  accounts.value = Array.isArray(res) ? res : (res?.items || res?.accounts || [])
})
</script>
