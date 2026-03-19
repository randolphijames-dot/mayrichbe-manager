<template>
  <div class="flex flex-col gap-4">

    <!-- 顶部工具栏 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-sm font-bold" style="color:var(--text-primary)">批量编辑账号资料</h2>
        <p class="text-xs mt-0.5" style="color:var(--text-faint)">简介和头像可每个账号独立设置，不填则不修改</p>
      </div>
      <div class="flex gap-2">
        <button class="btn btn-secondary btn-sm" @click="applyTemplate" :disabled="!templateText">
          <Wand2 :size="13" /> 应用模板
        </button>
        <button class="btn btn-primary btn-sm" @click="executeAll" :disabled="executing || !hasAnyChange">
          <span v-if="executing" class="w-3 h-3 border-2 rounded-full animate-spin" style="border-color:rgba(255,255,255,0.3);border-top-color:white"></span>
          <Zap v-else :size="13" /> 批量执行
        </button>
      </div>
    </div>

    <!-- 简介模板工具 -->
    <div class="card" style="padding:14px">
      <div class="flex items-center gap-3">
        <div class="flex-1">
          <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">
            简介模板（快速填充，可用 <code style="color:var(--brand)">{{序号}}</code> 自动填1/2/3...）
          </label>
          <input v-model="templateText" class="input text-sm" placeholder="例：日本の最新財経ニュースを毎日配信 💹 No.{{序号}}" />
        </div>
        <div style="width:130px">
          <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">起始序号</label>
          <input v-model.number="templateStart" type="number" min="1" class="input text-sm" style="width:100%" />
        </div>
        <button class="btn btn-secondary btn-sm mt-5" @click="applyTemplate" :disabled="!templateText">
          填入全部
        </button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="flex items-center gap-2">
      <select v-model="filterGroup" class="input text-sm" style="width:150px">
        <option value="">全部分组</option>
        <option v-for="g in groups" :key="g">{{ g }}</option>
      </select>
      <label class="flex items-center gap-1.5 text-xs cursor-pointer" style="color:var(--text-muted)">
        <input v-model="onlyShowSelected" type="checkbox" style="accent-color:var(--brand)" />
        只显示已选账号
      </label>
      <span class="text-xs" style="color:var(--text-faint)">{{ filteredRows.length }} 个账号</span>
    </div>

    <!-- 主表格 -->
    <div class="card" style="padding:0; overflow-x:auto">
      <table class="table" style="min-width:700px">
        <thead>
          <tr>
            <th style="width:40px">
              <input type="checkbox" :checked="allSelected" @change="toggleAll" style="accent-color:var(--brand)" />
            </th>
            <th style="width:160px">账号</th>
            <th style="width:80px">分组</th>
            <th>新简介（空=不修改）</th>
            <th style="width:120px">新头像（空=不换）</th>
            <th style="width:80px">状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filteredRows" :key="row.account.id">
            <!-- 勾选 -->
            <td>
              <input type="checkbox" v-model="row.selected" style="accent-color:var(--brand)" />
            </td>
            <!-- 账号信息 -->
            <td>
              <div class="flex flex-col gap-0.5">
                <span class="text-xs font-medium" style="color:var(--text-primary)">{{ row.account.username }}</span>
                <span class="text-xs" style="color:var(--text-faint)">{{ row.account.name }}</span>
                <span v-if="!row.account.has_password" class="badge badge-red" style="font-size:9px; width:fit-content">需密码</span>
              </div>
            </td>
            <!-- 分组 -->
            <td>
              <span class="badge badge-gray" style="font-size:10px">{{ row.account.group_name || '—' }}</span>
            </td>
            <!-- 新简介 -->
            <td>
              <textarea
                v-model="row.newBio"
                class="input text-xs"
                rows="2"
                :placeholder="row.currentBio ? ('当前：' + row.currentBio.slice(0, 30) + '...') : '留空则不修改'"
                style="resize:none; font-size:12px"
              />
            </td>
            <!-- 新头像 -->
            <td>
              <div class="flex flex-col items-center gap-1">
                <img v-if="row.avatarPreview" :src="row.avatarPreview" class="w-10 h-10 rounded-full object-cover" style="border:1px solid var(--border)" />
                <div v-else class="w-10 h-10 rounded-full flex items-center justify-center text-lg" style="background:var(--bg-base); border:1px solid var(--border)">
                  {{ row.account.username?.[0]?.toUpperCase() }}
                </div>
                <label class="btn btn-ghost btn-sm cursor-pointer" style="font-size:10px; padding:2px 6px">
                  <Upload :size="10" /> 选图
                  <input type="file" accept="image/*" class="hidden" @change="e => handleAvatarFile(row, e)" />
                </label>
              </div>
            </td>
            <!-- 状态 -->
            <td>
              <span class="badge" :class="statusBadge(row.status)">{{ statusLabel(row.status) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 执行日志 -->
    <div v-if="logs.length > 0" class="card" style="padding:14px">
      <h3 class="text-xs font-semibold mb-2" style="color:var(--text-primary)">执行日志</h3>
      <div class="flex flex-col gap-1 max-h-40 overflow-y-auto">
        <div v-for="(log, i) in logs" :key="i" class="text-xs px-2 py-1 rounded" style="background:var(--bg-base)"
          :style="log.ok ? 'color:#4ade80' : 'color:#f87171'">
          {{ log.ok ? '✅' : '❌' }} {{ log.msg }}
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { Wand2, Zap, Upload } from 'lucide-vue-next'
import { accountsApi, profileApi } from '@/api'

interface Row {
  account: any
  selected: boolean
  newBio: string
  currentBio: string
  avatarFile: File | null
  avatarPreview: string
  status: 'idle' | 'running' | 'success' | 'error' | 'skipped'
  errorMsg: string
}

const accounts = ref<any[]>([])
const rows = ref<Row[]>([])
const templateText = ref('')
const templateStart = ref(1)
const filterGroup = ref('')
const onlyShowSelected = ref(false)
const executing = ref(false)
const logs = ref<{ ok: boolean; msg: string }[]>([])

const groups = computed(() => [...new Set(accounts.value.map(a => a.group_name).filter(Boolean))])

const filteredRows = computed(() => rows.value.filter(r => {
  if (filterGroup.value && r.account.group_name !== filterGroup.value) return false
  if (onlyShowSelected.value && !r.selected) return false
  return r.account.platform === 'instagram'
}))

const allSelected = computed(() => filteredRows.value.every(r => r.selected))
const hasAnyChange = computed(() => rows.value.some(r => r.selected && (r.newBio || r.avatarFile)))

function toggleAll(e: Event) {
  const checked = (e.target as HTMLInputElement).checked
  filteredRows.value.forEach(r => { r.selected = checked })
}

function applyTemplate() {
  if (!templateText.value) return
  let seq = templateStart.value
  filteredRows.value.forEach(r => {
    r.newBio = templateText.value.replace('{{序号}}', String(seq).padStart(2, '0'))
    seq++
  })
}

function handleAvatarFile(row: Row, e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  row.avatarFile = file
  row.avatarPreview = URL.createObjectURL(file)
}

function statusBadge(s: string) {
  return { idle: 'badge-gray', running: 'badge-blue', success: 'badge-green', error: 'badge-red', skipped: 'badge-gray' }[s] || 'badge-gray'
}
function statusLabel(s: string) {
  return { idle: '待执行', running: '执行中', success: '完成', error: '失败', skipped: '跳过' }[s] || s
}

async function executeAll() {
  const toRun = rows.value.filter(r => r.selected && (r.newBio || r.avatarFile) && r.account.has_password)
  if (!toRun.length) { alert('没有可执行的账号（需勾选账号、填写内容、且已存储密码）'); return }
  if (!confirm(`将对 ${toRun.length} 个账号执行操作，继续吗？`)) return

  executing.value = true
  logs.value = []

  for (const row of toRun) {
    row.status = 'running'

    // Step 1：先上传头像文件（如果有）
    if (row.avatarFile) {
      try {
        await profileApi.uploadAvatar(row.account.id, row.avatarFile)
      } catch (e: any) {
        row.status = 'error'
        row.errorMsg = '头像上传失败'
        logs.value.push({ ok: false, msg: `${row.account.username} 头像上传失败: ${e?.message}` })
        continue
      }
    }

    // Step 2：执行修改
    try {
      const ops: Promise<any>[] = []

      if (row.newBio) {
        ops.push(profileApi.batchBio([{ account_id: row.account.id, biography: row.newBio }]))
      }
      if (row.avatarFile) {
        ops.push(profileApi.batchAvatar([row.account.id]))
      }

      await Promise.all(ops)
      row.status = 'success'
      logs.value.push({ ok: true, msg: `${row.account.username} 操作已发送（后台执行中）` })
    } catch (e: any) {
      row.status = 'error'
      row.errorMsg = e?.message || '操作失败'
      logs.value.push({ ok: false, msg: `${row.account.username} 失败: ${row.errorMsg}` })
    }

    // 每个账号间延迟 1 秒（避免并发过高）
    await new Promise(r => setTimeout(r, 1000))
  }

  executing.value = false
}

onMounted(async () => {
  accounts.value = await accountsApi.list({ limit: 500 }) as any[]
  rows.value = accounts.value
    .filter(a => a.platform === 'instagram')
    .map(a => reactive({
      account: a,
      selected: false,
      newBio: '',
      currentBio: '',
      avatarFile: null,
      avatarPreview: '',
      status: 'idle' as const,
      errorMsg: '',
    }))
})
</script>
