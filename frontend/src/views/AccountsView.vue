<template>
  <div class="flex flex-col gap-4">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <select v-model="filterPlatform" class="input text-sm" style="width:140px">
          <option value="">全部平台</option>
          <option value="instagram">📸 Instagram</option>
          <option value="youtube">▶ YouTube</option>
        </select>
        <select v-model="filterStatus" class="input text-sm" style="width:120px">
          <option value="">全部状态</option>
          <option value="active">正常</option>
          <option value="suspended">封禁</option>
          <option value="limited">限流</option>
          <option value="unknown">未知</option>
        </select>
        <button class="btn btn-secondary btn-sm" @click="loadAccounts">
          <RefreshCw :size="13" />刷新
        </button>
      </div>
      <div class="flex items-center gap-2">
        <label class="btn btn-secondary btn-sm cursor-pointer">
          <Upload :size="13" />批量导入 CSV
          <input type="file" accept=".csv" class="hidden" @change="handleCsvImport" />
        </label>
        <button class="btn btn-primary btn-sm" @click="openCreate">
          <Plus :size="13" />新增账号
        </button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="card" style="padding:0; overflow:hidden">
      <div v-if="loading" class="empty-state" style="padding:40px">
        <div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:#0ea5e9"></div>
      </div>
      <div v-else-if="filteredAccounts.length === 0" class="empty-state" style="padding:60px">
        <Users :size="32" />
        <p>暂无账号，点击「新增账号」或「批量导入 CSV」开始</p>
        <a href="/账号导入模板.csv" download class="btn btn-ghost btn-sm mt-2">下载 CSV 模板</a>
      </div>
      <table v-else class="table">
        <thead>
          <tr>
            <th style="width:50px">ID</th>
            <th>账号名</th>
            <th>用户名</th>
            <th style="width:120px">平台</th>
            <th style="width:100px">状态</th>
            <th style="width:80px">代理</th>
            <th>AdsPower ID</th>
            <th style="width:200px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="account in filteredAccounts" :key="account.id">
            <td class="text-xs" style="color:var(--text-faint)">{{ account.id }}</td>
            <td class="font-medium" style="color:var(--text-primary)">{{ account.name }}</td>
            <td class="font-mono text-xs">@{{ account.username }}</td>
            <td>
              <span class="badge" :class="account.platform === 'instagram' ? 'badge-pink' : 'badge-red'">
                {{ account.platform === 'instagram' ? '📸 Instagram' : '▶ YouTube' }}
              </span>
            </td>
            <td>
              <div class="flex items-center gap-1.5">
                <div class="w-1.5 h-1.5 rounded-full flex-shrink-0" :class="statusDot(account.status)"></div>
                <span class="text-xs" :style="statusColor(account.status)">{{ statusLabel(account.status) }}</span>
              </div>
            </td>
            <td>
              <span class="text-xs" :style="account.proxy ? 'color:#4ade80' : 'color:var(--text-muted)'">
                {{ account.proxy ? '✓ 配置' : '— 无' }}
              </span>
            </td>
            <td class="font-mono text-xs" style="color:var(--text-faint)">{{ account.adspower_profile_id || '—' }}</td>
            <td>
              <div class="flex items-center gap-1">
                <button class="btn btn-ghost btn-sm" @click="handleEdit(account)">编辑</button>
                <button class="btn btn-ghost btn-sm" @click="handleCheckStatus(account)" :disabled="checkingId === account.id">
                  <span v-if="checkingId === account.id" class="w-3 h-3 border rounded-full animate-spin inline-block" style="border-color:var(--text-muted); border-top-color:#0ea5e9"></span>
                  <span v-else>检测</span>
                </button>
                <button v-if="account.platform === 'youtube'" class="btn btn-ghost btn-sm" style="color:#0ea5e9" @click="handleYtOAuth(account)">授权</button>
                <button class="btn btn-danger btn-sm" @click="handleDelete(account)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 创建/编辑 Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
        <div class="card w-full" style="max-width:520px; max-height:92vh; overflow-y:auto">
          <div class="flex items-center justify-between mb-5">
            <div>
              <h3 class="font-semibold" style="color:var(--text-primary)">{{ editRecord ? '编辑账号' : '新增账号' }}</h3>
              <p class="text-xs mt-0.5" style="color:var(--text-faint)">带 * 为必填项</p>
            </div>
            <button @click="showModal = false" style="color:var(--text-faint)"><X :size="18" /></button>
          </div>

          <div class="flex flex-col gap-4">
            <!-- 基础信息 -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">显示名称 *</label>
                <input v-model="form.name" class="input" placeholder="日本財経_01" />
              </div>
              <div>
                <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">用户名 *</label>
                <input v-model="form.username" class="input" placeholder="不含 @" />
              </div>
            </div>

            <!-- 平台 + 分组 -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">平台 *</label>
                <div class="flex gap-1.5">
                  <button class="btn flex-1 btn-sm" :class="form.platform === 'instagram' ? 'btn-primary' : 'btn-ghost'" @click="form.platform = 'instagram'">📸 INS</button>
                  <button class="btn flex-1 btn-sm" :class="form.platform === 'youtube' ? 'btn-primary' : 'btn-ghost'" @click="form.platform = 'youtube'">▶ YT</button>
                </div>
              </div>
              <div>
                <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">账号分组</label>
                <input v-model="form.group_name" class="input text-sm" placeholder="如：财经类、生活类" />
              </div>
            </div>

            <!-- 发布方式（INS专用） -->
            <div v-if="form.platform === 'instagram'">
              <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">发布方式 *</label>
              <div class="grid grid-cols-3 gap-2">
                <button
                  v-for="m in publishMethods"
                  :key="m.value"
                  class="p-3 rounded-lg text-left transition-all"
                  :style="form.publish_method === m.value
                    ? 'background:var(--brand); color:white; border:1px solid transparent'
                    : 'background:var(--bg-base); color:var(--text-muted); border:1px solid var(--border)'"
                  @click="form.publish_method = m.value"
                >
                  <div class="text-lg mb-1">{{ m.icon }}</div>
                  <div class="text-xs font-semibold leading-tight">{{ m.label }}</div>
                  <div class="text-xs mt-0.5 opacity-70">{{ m.desc }}</div>
                </button>
              </div>
            </div>

            <!-- 指纹浏览器 Profile ID（AdsPower / BitBrowser）-->
            <div v-if="form.platform === 'instagram' && (form.publish_method === 'adspower' || form.publish_method === 'bitbrowser')">
              <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">
                {{ form.publish_method === 'adspower' ? 'AdsPower' : '比特浏览器' }} Profile ID
              </label>
              <div class="flex gap-2">
                <input v-model="form.browser_profile_id" class="input font-mono text-sm flex-1"
                  :placeholder="form.publish_method === 'adspower' ? '在 AdsPower 账号列表查看' : '在比特浏览器窗口列表查看'" />
              </div>
              <p class="text-xs mt-1.5 leading-relaxed" style="color:var(--text-faint)">
                {{ form.publish_method === 'adspower'
                  ? '📍 AdsPower → 打开软件 → 账号列表 → 每行最左侧的字母+数字 ID'
                  : '📍 比特浏览器 → 主界面 → 窗口列表 → 点击窗口名旁边的「ID」复制'
                }}
              </p>
            </div>

            <!-- instagrapi：密码 + TOTP -->
            <div v-if="form.platform === 'instagram' && form.publish_method === 'instagrapi'" class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
              <div class="flex items-center gap-2 mb-3">
                <span class="badge badge-yellow">⚡ 无需浏览器</span>
                <span class="text-xs" style="color:var(--text-faint)">直接用账号密码操作</span>
              </div>
              <div class="flex flex-col gap-3">
                <div>
                  <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">账号密码 *</label>
                  <input v-model="form.ins_password" type="password" class="input text-sm" placeholder="密码（加密存储）" autocomplete="new-password" />
                </div>
                <div>
                  <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">2FA TOTP 密钥（如开启了两步验证）</label>
                  <input v-model="form.ins_totp_secret" class="input font-mono text-sm" placeholder="32位 Base32 密钥（可选）" />
                </div>
                <div class="p-2 rounded" style="background:#422006; border:1px solid #92400e">
                  <p class="text-xs" style="color:#fde68a">⚠️ instagrapi 为非官方方案，风险略高于指纹浏览器。建议配合代理使用，单账号每日发布 ≤ 3 次。</p>
                </div>
              </div>
            </div>

            <!-- 代理 -->
            <div>
              <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">代理 IP（强烈建议填写）</label>
              <input v-model="form.proxy" class="input font-mono text-sm" placeholder="http://user:pass@ip:port 或 socks5://..." />
              <p class="text-xs mt-1" style="color:var(--text-faint)">每个账号应使用独立代理，建议住宅 IP（日本节点）</p>
            </div>

            <!-- 备注 -->
            <div>
              <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">备注</label>
              <textarea v-model="form.notes" class="input text-sm" rows="2" placeholder="可选备注" />
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-5">
            <button class="btn btn-ghost" @click="showModal = false">取消</button>
            <button class="btn btn-primary" @click="handleSubmit" :disabled="submitting">
              <span v-if="submitting" class="w-4 h-4 border-2 rounded-full animate-spin" style="border-color:rgba(255,255,255,0.3); border-top-color:white"></span>
              {{ editRecord ? '保存更改' : '创建账号' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 删除确认 -->
    <Teleport to="body">
      <div v-if="deleteTarget" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
        <div class="card" style="max-width:380px; width:100%">
          <h3 class="font-semibold mb-2" style="color:var(--text-primary)">确认删除</h3>
          <p class="text-sm mb-5" style="color:var(--text-muted)">确定要删除账号 <strong style="color:var(--text-primary)">{{ deleteTarget.username }}</strong>？此操作不可撤销。</p>
          <div class="flex justify-end gap-2">
            <button class="btn btn-ghost" @click="deleteTarget = null">取消</button>
            <button class="btn btn-danger" @click="confirmDelete">确认删除</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 成功 Toast -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="toast" class="fixed bottom-6 right-6 z-50 px-4 py-3 rounded-lg text-sm font-medium"
          :style="toast.type === 'error' ? 'background:#7f1d1d; color:#fca5a5; border:1px solid #991b1b' : 'background:#052e16; color:#86efac; border:1px solid #166534'">
          {{ toast.message }}
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Plus, Upload, RefreshCw, Users, X } from 'lucide-vue-next'
import { accountsApi, youtubeApi } from '@/api'

const loading = ref(false)
const submitting = ref(false)
const accounts = ref<any[]>([])
const filterPlatform = ref('')
const filterStatus = ref('')
const showModal = ref(false)
const editRecord = ref<any>(null)
const checkingId = ref<number | null>(null)
const deleteTarget = ref<any>(null)
const toast = ref<{ message: string; type: string } | null>(null)

const publishMethods = [
  { value: 'adspower',   icon: '🖥', label: 'AdsPower 浏览器',  desc: '通过指纹浏览器自动操作网页，适合少量主号' },
  { value: 'bitbrowser', icon: '🌐', label: '比特浏览器',      desc: '国内指纹浏览器，和 AdsPower 用法类似' },
  { value: 'instagrapi', icon: '⚡', label: '模拟手机（推荐）', desc: '系统伪装成安卓 App，无需打开浏览器，适合矩阵批量' },
]

const formDefault = () => ({
  name: '', username: '', platform: 'instagram', group_name: '',
  publish_method: 'adspower', browser_profile_id: '',
  ins_password: '', ins_totp_secret: '',
  proxy: '', notes: '',
})
const form = reactive(formDefault())

const filteredAccounts = computed(() =>
  accounts.value.filter(a => {
    if (filterPlatform.value && a.platform !== filterPlatform.value) return false
    if (filterStatus.value && a.status !== filterStatus.value) return false
    return true
  })
)

function statusDot(s: string) {
  return { active: 'bg-green-500', suspended: 'bg-red-500', limited: 'bg-yellow-500', unknown: 'bg-gray-600' }[s] || 'bg-gray-600'
}
function statusColor(s: string) {
  return { active: 'color:#4ade80', suspended: 'color:#f87171', limited: 'color:#fbbf24', unknown: 'color:var(--text-faint)' }[s] || 'color:var(--text-faint)'
}
function statusLabel(s: string) {
  return { active: '正常', suspended: '封禁', limited: '限流', unknown: '未检测' }[s] || s
}

function showToast(message: string, type = 'success') {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 3500)
}

async function loadAccounts() {
  loading.value = true
  try { accounts.value = await accountsApi.list({ limit: 500 }) as any[] }
  finally { loading.value = false }
}

function openCreate() {
  editRecord.value = null
  Object.assign(form, formDefault())
  showModal.value = true
}
function handleEdit(record: any) {
  editRecord.value = record
  Object.assign(form, {
    name: record.name,
    username: record.username,
    platform: record.platform,
    group_name: record.group_name || '',
    publish_method: record.browser_type === 'bitbrowser' ? 'bitbrowser' : record.browser_type === 'none' ? 'instagrapi' : 'adspower',
    browser_profile_id: record.browser_profile_id || '',
    proxy: record.proxy || '',
    notes: record.notes || '',
    ins_password: '',
    ins_totp_secret: '',
  })
  showModal.value = true
}
async function handleSubmit() {
  if (!form.name || !form.username) { showToast('请填写名称和用户名', 'error'); return }
  if (form.platform === 'instagram' && form.publish_method !== 'instagrapi' && !form.browser_profile_id) {
    showToast(`请填写 ${form.publish_method === 'adspower' ? 'AdsPower' : '比特浏览器'} Profile ID`, 'error'); return
  }
  submitting.value = true
  try {
    const payload: any = {
      name: form.name, username: form.username, platform: form.platform,
      group_name: form.group_name || null,
      browser_type: form.publish_method === 'instagrapi' ? 'none' : form.publish_method,
      browser_profile_id: form.browser_profile_id || null,
      proxy: form.proxy || null,
      notes: form.notes || null,
    }
    if (form.ins_password) payload.ins_password = form.ins_password
    if (form.ins_totp_secret) payload.ins_totp_secret = form.ins_totp_secret
    if (editRecord.value) { await accountsApi.update(editRecord.value.id, payload); showToast('更新成功') }
    else { await accountsApi.create(payload); showToast('创建成功') }
    showModal.value = false
    await loadAccounts()
  } catch { showToast('操作失败', 'error') }
  finally { submitting.value = false }
}
function handleDelete(record: any) { deleteTarget.value = record }
async function confirmDelete() {
  if (!deleteTarget.value) return
  await accountsApi.delete(deleteTarget.value.id)
  showToast(`已删除 ${deleteTarget.value.username}`)
  deleteTarget.value = null
  await loadAccounts()
}
async function handleCheckStatus(record: any) {
  checkingId.value = record.id
  try { await accountsApi.checkStatus(record.id); showToast('健康检测已触发，稍后刷新查看') }
  finally { checkingId.value = null }
}
async function handleYtOAuth(record: any) {
  const res = await youtubeApi.startOAuth(record.id) as any
  if (res.auth_url) window.open(res.auth_url, '_blank', 'width=600,height=700')
}
async function handleCsvImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const res = await accountsApi.importCsv(file) as any
  showToast(`导入完成：新增 ${res.created}，跳过 ${res.skipped}`)
  await loadAccounts()
}
onMounted(loadAccounts)
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s, transform 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(8px); }
</style>
