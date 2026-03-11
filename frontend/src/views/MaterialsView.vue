<template>
  <div class="flex gap-4 h-full" style="min-height:0">

    <!-- ─── 左栏：账号 & 文件夹筛选 ─── -->
    <div class="flex-shrink-0 flex flex-col gap-3" style="width:200px">

      <!-- 全部按钮 -->
      <button
        class="nav-item"
        :class="{ active: !filterAccount && !filterFolder }"
        @click="filterAccount = null; filterFolder = ''"
      >
        <Layers :size="14" /> 全部素材
        <span class="ml-auto badge badge-gray text-xs">{{ materials.length }}</span>
      </button>

      <!-- 按账号 -->
      <div>
        <p class="nav-section-label">按账号筛选</p>
        <button
          v-for="a in accounts"
          :key="a.id"
          class="nav-item w-full"
          :class="{ active: filterAccount === a.id }"
          @click="filterAccount = a.id; filterFolder = ''"
          style="font-size:12px; padding:6px 10px"
        >
          <span>{{ a.platform === 'instagram' ? '📸' : '▶' }}</span>
          <span class="truncate flex-1 text-left">{{ a.username }}</span>
          <span class="badge badge-gray" style="font-size:10px">{{ countByAccount(a.id) }}</span>
        </button>
      </div>

      <!-- 按时间文件夹 -->
      <div v-if="folders.length > 0">
        <p class="nav-section-label">按日期文件夹</p>
        <button
          v-for="f in folders"
          :key="f"
          class="nav-item w-full"
          :class="{ active: filterFolder === f }"
          @click="filterFolder = f; filterAccount = null"
          style="font-size:12px; padding:6px 10px"
        >
          <FolderOpen :size="13" />
          <span class="truncate flex-1 text-left">{{ f }}</span>
        </button>
      </div>
    </div>

    <!-- ─── 主区域 ─── -->
    <div class="flex-1 flex flex-col gap-3 overflow-y-auto" style="min-width:0">

      <!-- 工具栏 -->
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <div class="flex items-center gap-2">
          <!-- 视图切换 -->
          <div class="flex rounded-lg overflow-hidden" style="border:1px solid var(--border)">
            <button
              v-for="v in views"
              :key="v.id"
              class="px-3 py-1.5 text-xs flex items-center gap-1.5 transition-colors"
              :style="currentView === v.id
                ? 'background:var(--brand); color:white'
                : 'background:var(--bg-surface); color:var(--text-muted)'"
              @click="currentView = v.id"
            >
              <component :is="v.icon" :size="12" />{{ v.label }}
            </button>
          </div>
          <select v-model="filterType" class="input text-sm" style="width:120px">
            <option value="">全部类型</option>
            <option value="video">🎬 视频</option>
            <option value="image">🖼 图片</option>
          </select>
          <span class="text-xs" style="color:var(--text-faint)">{{ filteredMaterials.length }} 个素材</span>
        </div>
        <div class="flex gap-2">
          <button v-if="currentView === 'board' && selectedInBoard.length > 0" class="btn btn-primary btn-sm" @click="openBoardPublish">
            <Zap :size="13" /> 一键发布 {{ selectedInBoard.length }} 个
          </button>
          <button class="btn btn-secondary btn-sm" @click="loadAll"><RefreshCw :size="13" /></button>
          <button class="btn btn-primary btn-sm" @click="openUpload">
            <Upload :size="13" /> 上传素材
          </button>
        </div>
      </div>

      <!-- ── 网格视图 ── -->
      <div v-if="currentView === 'grid'">
        <div v-if="loading" class="empty-state"><div class="w-6 h-6 border-2 rounded-full animate-spin" style="border-color:var(--border); border-top-color:var(--brand)"></div></div>
        <div v-else-if="filteredMaterials.length === 0" class="empty-state card" style="padding:80px">
          <ImageIcon :size="36" /><p class="text-sm">暂无素材</p>
        </div>
        <div v-else class="grid gap-3" style="grid-template-columns: repeat(auto-fill, minmax(240px, 1fr))">
          <div v-for="m in filteredMaterials" :key="m.id" class="card flex flex-col gap-2" style="padding:14px">
            <!-- 预览 -->
            <div class="rounded-lg flex items-center justify-center relative" style="background:var(--bg-base); height:90px; border:1px solid var(--border-light)">
              <span class="text-2xl">{{ m.material_type === 'video' ? '🎬' : '🖼' }}</span>
              <span class="absolute top-1.5 left-1.5 badge badge-gray" style="font-size:10px">{{ m.material_type }}</span>
              <span v-if="m.folder_tag" class="absolute top-1.5 right-1.5 badge badge-blue" style="font-size:10px">📁{{ m.folder_tag }}</span>
            </div>
            <!-- 标题 -->
            <p class="text-sm font-medium truncate" style="color:var(--text-primary)">{{ m.title || '素材 #' + m.id }}</p>
            <!-- 已分配账号 -->
            <div v-if="m.target_account_ids?.length" class="flex flex-wrap gap-1">
              <span v-for="aid in m.target_account_ids.slice(0,3)" :key="aid" class="badge badge-gray" style="font-size:10px">
                {{ accountName(aid) }}
              </span>
              <span v-if="m.target_account_ids.length > 3" class="badge badge-gray" style="font-size:10px">+{{ m.target_account_ids.length - 3 }}</span>
            </div>
            <p v-else class="text-xs" style="color:var(--text-faint)">未分配账号</p>
            <!-- 操作 -->
            <div class="flex gap-1.5 mt-auto pt-1">
              <button class="btn btn-primary btn-sm flex-1" @click="openTaskModal(m)"><Zap :size="11" /> 发布</button>
              <button class="btn btn-ghost btn-sm" @click="openAssign(m)"><Users :size="11" /></button>
              <button class="btn btn-ghost btn-sm" style="color:#ef4444" @click="handleDelete(m)"><Trash2 :size="11" /></button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 看板视图：素材×账号一键选择发布 ── -->
      <div v-if="currentView === 'board'" class="card" style="padding:0; overflow:auto">
        <div v-if="filteredMaterials.length === 0" class="empty-state" style="padding:60px">
          <Layers :size="28" /><p class="text-sm">暂无素材</p>
        </div>
        <table v-else class="table text-sm" style="min-width:600px">
          <thead>
            <tr>
              <th style="width:200px; position:sticky; left:0; background:var(--bg-surface); z-index:2">素材</th>
              <th v-for="a in accounts" :key="a.id" style="min-width:100px; text-align:center">
                <div class="flex flex-col items-center gap-0.5">
                  <span>{{ a.platform === 'instagram' ? '📸' : '▶' }}</span>
                  <span style="font-size:10px; color:var(--text-faint)" class="truncate max-w-20">{{ a.username }}</span>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in filteredMaterials" :key="m.id">
              <td style="position:sticky; left:0; background:var(--bg-surface); z-index:1">
                <div class="flex items-center gap-2">
                  <input type="checkbox" :value="m.id" v-model="selectedInBoard"
                    class="w-4 h-4 rounded" style="accent-color:var(--brand)" />
                  <div class="flex flex-col min-w-0">
                    <span class="text-xs font-medium truncate" style="color:var(--text-primary); max-width:140px">{{ m.title || '素材 #' + m.id }}</span>
                    <span class="text-xs" style="color:var(--text-faint)">{{ m.material_type }} {{ m.folder_tag ? '· 📁'+m.folder_tag : '' }}</span>
                  </div>
                </div>
              </td>
              <td v-for="a in accounts" :key="a.id" style="text-align:center; vertical-align:middle">
                <button
                  class="w-8 h-8 rounded-lg flex items-center justify-center mx-auto transition-all"
                  :style="isBoardSelected(m.id, a.id)
                    ? 'background:var(--brand); color:white'
                    : 'background:var(--bg-base); color:var(--text-faint); border:1px solid var(--border-light)'"
                  @click="toggleBoard(m.id, a.id)"
                >
                  <CheckSquare v-if="isBoardSelected(m.id, a.id)" :size="14" />
                  <span v-else style="font-size:10px">+</span>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <!-- 看板底部操作栏 -->
        <div v-if="boardSelections.size > 0" class="flex items-center justify-between p-4" style="border-top:1px solid var(--border); background:var(--bg-surface)">
          <span class="text-sm" style="color:var(--text-muted)">已选 {{ boardSelections.size }} 组「素材→账号」</span>
          <button class="btn btn-primary btn-sm" @click="openBoardPublish"><Zap :size="13" /> 设定时间并发布</button>
        </div>
      </div>
    </div>

    <!-- ─── 上传 Modal ─── -->
    <Teleport to="body">
      <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
        <div class="card" style="max-width:500px; width:100%; max-height:92vh; overflow-y:auto">
          <div class="flex items-center justify-between mb-4">
            <h3 class="font-semibold" style="color:var(--text-primary)">上传素材</h3>
            <button @click="showUploadModal = false" style="color:var(--text-faint)"><X :size="18" /></button>
          </div>

          <div class="flex flex-col gap-4">
            <!-- 文件选择 -->
            <div>
              <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">文件 *</label>
              <div
                class="rounded-lg flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors"
                style="background:var(--bg-base); border:2px dashed var(--border); padding:24px"
                :style="uploadFile ? 'border-color:var(--brand)' : ''"
                @click="$refs.fileInput.click()"
              >
                <Upload :size="20" style="color:var(--text-faint)" />
                <span class="text-sm" style="color:var(--text-faint)">{{ uploadFile ? uploadFile.name : '点击选择文件（视频/图片）' }}</span>
                <span v-if="uploadFile" class="badge badge-green">{{ (uploadFile.size/1024/1024).toFixed(1) }}MB</span>
              </div>
              <input ref="fileInput" type="file" accept="video/*,image/*" class="hidden" @change="e => uploadFile = e.target.files[0]" />
            </div>

            <!-- 素材类型 + 日期文件夹 -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">素材类型 *</label>
                <select v-model="uploadForm.material_type" class="input text-sm">
                  <option value="video">🎬 视频</option>
                  <option value="image">🖼 图片</option>
                  <option value="carousel">📸 轮播图</option>
                </select>
              </div>
              <div>
                <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">日期文件夹（可选）</label>
                <input v-model="uploadForm.folder_tag" class="input text-sm" :placeholder="todayStr" />
              </div>
            </div>

            <!-- 内部标题 -->
            <div>
              <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">内部标题</label>
              <input v-model="uploadForm.title" class="input text-sm" placeholder="不填则使用文件名" />
            </div>

            <!-- 发布文案 -->
            <div>
              <label class="text-xs font-medium mb-1 block" style="color:var(--text-muted)">发布文案（Caption）</label>
              <textarea v-model="uploadForm.caption" class="input text-sm" rows="3" placeholder="Instagram 发布时的文案..." />
            </div>

            <!-- 分配账号 -->
            <div>
              <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">分配给哪些账号（可选）</label>
              <div class="flex flex-wrap gap-2 p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border); min-height:44px">
                <button
                  v-for="a in accounts"
                  :key="a.id"
                  class="badge cursor-pointer transition-all"
                  :class="uploadForm.target_account_ids.includes(a.id)
                    ? (a.platform === 'instagram' ? 'badge-pink' : 'badge-red')
                    : 'badge-gray'"
                  @click="toggleUploadAccount(a.id)"
                >
                  {{ a.platform === 'instagram' ? '📸' : '▶' }} {{ a.username }}
                </button>
                <span v-if="accounts.length === 0" class="text-xs" style="color:var(--text-faint)">先在账号管理页添加账号</span>
              </div>
            </div>
          </div>

          <div class="flex justify-end gap-2 mt-5">
            <button class="btn btn-ghost" @click="showUploadModal = false">取消</button>
            <button class="btn btn-primary" @click="handleUpload" :disabled="uploading || !uploadFile">
              <span v-if="uploading" class="w-4 h-4 border-2 rounded-full animate-spin" style="border-color:rgba(255,255,255,0.3); border-top-color:white"></span>
              上传
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ─── 发布任务 Modal（单素材） ─── -->
    <Teleport to="body">
      <div v-if="showTaskModal" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
        <div class="card" style="max-width:460px; width:100%">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h3 class="font-semibold" style="color:var(--text-primary)">安排发布</h3>
              <p class="text-xs mt-0.5" style="color:var(--text-faint)">{{ selectedMaterial?.title || '素材 #' + selectedMaterial?.id }}</p>
            </div>
            <button @click="showTaskModal = false" style="color:var(--text-faint)"><X :size="18" /></button>
          </div>
          <!-- 模式切换 -->
          <div class="flex items-center gap-2 mb-3">
            <span class="text-xs" style="color:var(--text-faint)">模式：</span>
            <div class="flex rounded-lg overflow-hidden" style="border:1px solid var(--border-light)">
              <button
                class="px-3 py-1 text-xs"
                :style="taskAdvanced ? 'background:var(--bg-surface); color:var(--text-muted)' : 'background:var(--brand); color:white'"
                @click="taskAdvanced = false"
              >
                简单
              </button>
              <button
                class="px-3 py-1 text-xs"
                :style="taskAdvanced ? 'background:var(--brand); color:white' : 'background:var(--bg-surface); color:var(--text-muted)'"
                @click="taskAdvanced = true"
              >
                高级
              </button>
            </div>
          </div>
          <div class="flex flex-col gap-4">
            <!-- 账号选择 -->
            <div>
              <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">目标账号 *</label>
              <div class="flex flex-wrap gap-1.5 p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border); min-height:44px">
                <button v-for="a in accounts" :key="a.id"
                  class="badge cursor-pointer"
                  :class="taskForm.account_ids.includes(a.id) ? (a.platform==='instagram' ? 'badge-pink':'badge-red') : 'badge-gray'"
                  @click="toggleTaskAccount(a.id)">
                  {{ a.platform==='instagram'?'📸':'▶' }} {{ a.username }}
                </button>
              </div>
            </div>
            <!-- 时间选择 -->
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-xs font-medium" style="color:var(--text-muted)">发布时间 *</label>
                <span class="text-xs px-2 py-0.5 rounded" style="background:var(--bg-base); color:var(--brand); border:1px solid var(--border)">{{ localTzLabel }}</span>
              </div>
              <div class="flex flex-wrap gap-1.5 mb-2">
                <button v-for="p in timePresets" :key="p.label" class="btn btn-ghost btn-sm" style="font-size:11px; padding:3px 8px" @click="taskForm.scheduled_at = p.value()">{{ p.label }}</button>
              </div>
              <input v-model="taskForm.scheduled_at" type="datetime-local" class="input text-sm" />
              <p v-if="taskForm.scheduled_at" class="text-xs mt-1" style="color:var(--brand)">⏱ {{ timeFromNow }} 后发布</p>
            </div>
            <!-- 随机偏移（高级模式） -->
            <div v-if="taskAdvanced">
              <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">随机偏移 0 ~ <span style="color:var(--brand)">{{ taskForm.random_offset }}</span> 分钟</label>
              <input v-model.number="taskForm.random_offset" type="range" min="0" max="120" class="w-full" style="accent-color:var(--brand)" />
              <p class="text-xs mt-1" style="color:var(--text-faint)">建议 15~60 分钟，用于让多个账号在时间段内自然错开。</p>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button class="btn btn-ghost" @click="showTaskModal = false">取消</button>
            <button class="btn btn-primary" @click="submitTask" :disabled="creatingTask">
              创建 {{ taskForm.account_ids.length }} 个任务
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ─── 看板批量发布 Modal ─── -->
    <Teleport to="body">
      <div v-if="showBoardModal" class="fixed inset-0 z-50 flex items-center justify-center" style="background:var(--modal-overlay)">
        <div class="card" style="max-width:480px; width:100%">
          <div class="flex items-center justify-between mb-3">
            <div>
              <h3 class="font-semibold" style="color:var(--text-primary)">批量发布</h3>
              <p class="text-xs mt-0.5" style="color:var(--text-faint)">{{ boardSelections.size }} 组「素材→账号」将创建任务</p>
            </div>
            <button @click="showBoardModal = false" style="color:var(--text-faint)"><X :size="18" /></button>
          </div>
          <!-- 模式切换 -->
          <div class="flex items-center gap-2 mb-3">
            <span class="text-xs" style="color:var(--text-faint)">模式：</span>
            <div class="flex rounded-lg overflow-hidden" style="border:1px solid var(--border-light)">
              <button
                class="px-3 py-1 text-xs"
                :style="boardAdvanced ? 'background:var(--bg-surface); color:var(--text-muted)' : 'background:var(--brand); color:white'"
                @click="boardAdvanced = false"
              >
                简单
              </button>
              <button
                class="px-3 py-1 text-xs"
                :style="boardAdvanced ? 'background:var(--brand); color:white' : 'background:var(--bg-surface); color:var(--text-muted)'"
                @click="boardAdvanced = true"
              >
                高级
              </button>
            </div>
          </div>
          <!-- 预览列表 -->
          <div class="flex flex-col gap-1 mb-4 max-h-40 overflow-y-auto">
            <div v-for="[key] in boardSelections" :key="key"
              class="flex items-center gap-2 text-xs px-3 py-1.5 rounded" style="background:var(--bg-base)">
              <span style="color:var(--text-primary)">{{ boardMaterialName(key.split('_')[0]) }}</span>
              <span style="color:var(--text-faint)">→</span>
              <span style="color:var(--brand)">{{ boardAccountName(key.split('_')[1]) }}</span>
            </div>
          </div>
          <!-- 时间设置 -->
          <div class="flex flex-col gap-3">
            <div>
              <div class="flex items-center justify-between mb-2">
                <label class="text-xs font-medium" style="color:var(--text-muted)">发布时间（第一个任务）</label>
                <span class="text-xs px-2 py-0.5 rounded" style="background:var(--bg-base); color:var(--brand); border:1px solid var(--border)">{{ localTzLabel }}</span>
              </div>
              <div class="flex flex-wrap gap-1.5 mb-2">
                <button v-for="p in timePresets" :key="p.label" class="btn btn-ghost btn-sm" style="font-size:11px; padding:3px 8px" @click="boardForm.scheduled_at = p.value()">{{ p.label }}</button>
              </div>
              <input v-model="boardForm.scheduled_at" type="datetime-local" class="input text-sm" />
            </div>
            <div v-if="boardAdvanced">
              <label class="text-xs font-medium mb-2 block" style="color:var(--text-muted)">各任务间随机偏移 0 ~ <span style="color:var(--brand)">{{ boardForm.random_offset }}</span> 分钟</label>
              <input v-model.number="boardForm.random_offset" type="range" min="0" max="120" class="w-full" style="accent-color:var(--brand)" />
              <p class="text-xs mt-1" style="color:var(--text-faint)">适合一次性创建大量任务时使用，减少同一时间点的集中动作。</p>
            </div>
          </div>
          <div class="flex justify-end gap-2 mt-5">
            <button class="btn btn-ghost" @click="showBoardModal = false">取消</button>
            <button class="btn btn-primary" @click="submitBoardPublish" :disabled="creatingTask">
              <Zap :size="13" /> 创建全部任务
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { Upload, RefreshCw, X, Users, Zap, Trash2, Layers, FolderOpen, CheckSquare, ImageIcon } from 'lucide-vue-next'
import { materialsApi, accountsApi, tasksApi } from '@/api'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

// ─── 视图切换 ───
const views = [
  { id: 'grid',  label: '网格',  icon: Layers },
  { id: 'board', label: '发布看板', icon: CheckSquare },
]
const currentView = ref<'grid'|'board'>('grid')

// ─── 数据 ───
const loading = ref(false)
const uploading = ref(false)
const creatingTask = ref(false)
const materials = ref<any[]>([])
const accounts = ref<any[]>([])

// ─── 筛选 ───
const filterType = ref('')
const filterAccount = ref<number|null>(null)
const filterFolder = ref('')

const folders = computed(() => {
  const tags = new Set(materials.value.map(m => m.folder_tag).filter(Boolean))
  return [...tags].sort().reverse()
})

const filteredMaterials = computed(() => {
  return materials.value.filter(m => {
    if (filterType.value && m.material_type !== filterType.value) return false
    if (filterAccount.value !== null && !m.target_account_ids?.includes(filterAccount.value)) return false
    if (filterFolder.value && m.folder_tag !== filterFolder.value) return false
    return true
  })
})

function countByAccount(aid: number) {
  return materials.value.filter(m => m.target_account_ids?.includes(aid)).length
}
function accountName(id: number) {
  return accounts.value.find(a => a.id === id)?.username || `#${id}`
}

// ─── 上传 ───
const showUploadModal = ref(false)
const uploadFile = ref<File|null>(null)
const fileInput = ref<HTMLInputElement>()
const todayStr = dayjs().format('YYYY-MM-DD')
const uploadForm = reactive({
  material_type: 'video',
  folder_tag: '',
  title: '',
  caption: '',
  target_account_ids: [] as number[],
  yt_privacy: 'public',
})

function openUpload() {
  uploadFile.value = null
  Object.assign(uploadForm, { material_type: 'video', folder_tag: todayStr, title: '', caption: '', target_account_ids: [], yt_privacy: 'public' })
  showUploadModal.value = true
}
function toggleUploadAccount(id: number) {
  const idx = uploadForm.target_account_ids.indexOf(id)
  if (idx >= 0) uploadForm.target_account_ids.splice(idx, 1)
  else uploadForm.target_account_ids.push(id)
}

async function handleUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', uploadFile.value)
    fd.append('material_type', uploadForm.material_type)
    if (uploadForm.title) fd.append('title', uploadForm.title)
    if (uploadForm.caption) fd.append('caption', uploadForm.caption)
    if (uploadForm.folder_tag) fd.append('folder_tag', uploadForm.folder_tag)
    fd.append('yt_privacy', uploadForm.yt_privacy)
    if (uploadForm.target_account_ids.length) fd.append('target_account_ids', uploadForm.target_account_ids.join(','))
    await materialsApi.upload(fd)
    showUploadModal.value = false
    uploadFile.value = null
    await loadAll()
  } finally { uploading.value = false }
}

// ─── 分配账号 ───
function openAssign(m: any) {
  selectedMaterial.value = m
  taskForm.account_ids = [...(m.target_account_ids || [])]
  showTaskModal.value = true
}

// ─── 删除 ───
async function handleDelete(m: any) {
  if (!confirm(`确定删除素材 "${m.title || '#' + m.id}"？`)) return
  await materialsApi.delete(m.id)
  await loadAll()
}

// ─── 单素材发布 Modal ───
const showTaskModal = ref(false)
const selectedMaterial = ref<any>(null)
const taskForm = reactive({ account_ids: [] as number[], scheduled_at: '', random_offset: 30 })
const taskAdvanced = ref(false)

// 时区 & 快捷预设
const localTzLabel = computed(() => {
  const offset = -new Date().getTimezoneOffset()
  const h = Math.floor(Math.abs(offset) / 60)
  const sign = offset >= 0 ? '+' : '-'
  const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone
  return `UTC${sign}${h} ${tzName}`
})
const timeFromNow = computed(() => {
  if (!taskForm.scheduled_at) return ''
  const diff = dayjs(taskForm.scheduled_at).diff(dayjs(), 'minute')
  if (diff <= 0) return '⚠️ 已过期'
  const h = Math.floor(diff / 60), m = diff % 60
  return `${h > 0 ? h + '小时' : ''}${m > 0 ? m + '分钟' : ''}`
})
const timePresets = [
  { label: '1小时后',   value: () => dayjs().add(1,'h').format('YYYY-MM-DDTHH:mm') },
  { label: '3小时后',   value: () => dayjs().add(3,'h').format('YYYY-MM-DDTHH:mm') },
  { label: '今日18:00', value: () => dayjs().hour(18).minute(0).format('YYYY-MM-DDTHH:mm') },
  { label: '今日21:00', value: () => dayjs().hour(21).minute(0).format('YYYY-MM-DDTHH:mm') },
  { label: '明日09:00', value: () => dayjs().add(1,'d').hour(9).minute(0).format('YYYY-MM-DDTHH:mm') },
  { label: '明日18:00', value: () => dayjs().add(1,'d').hour(18).minute(0).format('YYYY-MM-DDTHH:mm') },
]

function toggleTaskAccount(id: number) {
  const idx = taskForm.account_ids.indexOf(id)
  if (idx >= 0) taskForm.account_ids.splice(idx, 1)
  else taskForm.account_ids.push(id)
}
function openTaskModal(m: any) {
  selectedMaterial.value = m
  taskForm.account_ids = [...(m.target_account_ids || [])]
  taskForm.scheduled_at = dayjs().add(1, 'h').format('YYYY-MM-DDTHH:mm')
  showTaskModal.value = true
}
async function submitTask() {
  if (!taskForm.account_ids.length || !taskForm.scheduled_at) return
  if (dayjs(taskForm.scheduled_at).diff(dayjs(), 'minute') <= 0) { alert('时间已过期'); return }
  creatingTask.value = true
  try {
    await tasksApi.createBatch({
      material_id: selectedMaterial.value.id,
      account_ids: taskForm.account_ids,
      scheduled_at: new Date(taskForm.scheduled_at).toISOString(),
      random_offset_minutes: taskForm.random_offset,
    })
    showTaskModal.value = false
  } finally { creatingTask.value = false }
}

// ─── 看板视图 ───
// boardSelections: Map 的 key = "materialId_accountId"
const boardSelections = ref(new Map<string, boolean>())
const selectedInBoard = computed(() => {
  const mids = new Set<number>()
  boardSelections.value.forEach((_, k) => mids.add(Number(k.split('_')[0])))
  return [...mids]
})
const showBoardModal = ref(false)
const boardForm = reactive({ scheduled_at: '', random_offset: 30 })
const boardAdvanced = ref(false)

function isBoardSelected(mid: number, aid: number) {
  return boardSelections.value.has(`${mid}_${aid}`)
}
function toggleBoard(mid: number, aid: number) {
  const k = `${mid}_${aid}`
  if (boardSelections.value.has(k)) boardSelections.value.delete(k)
  else boardSelections.value.set(k, true)
  boardSelections.value = new Map(boardSelections.value)
}
function boardMaterialName(id: string) {
  return materials.value.find(m => m.id === Number(id))?.title || '素材 #' + id
}
function boardAccountName(id: string) {
  return accounts.value.find(a => a.id === Number(id))?.username || '#' + id
}
function openBoardPublish() {
  boardForm.scheduled_at = dayjs().add(1, 'h').format('YYYY-MM-DDTHH:mm')
  boardForm.random_offset = 30
  showBoardModal.value = true
}
async function submitBoardPublish() {
  if (!boardForm.scheduled_at) return
  if (dayjs(boardForm.scheduled_at).diff(dayjs(), 'minute') <= 0) { alert('时间已过期'); return }
  creatingTask.value = true
  try {
    // 按素材分组，每个素材的所有账号一次 batch 请求
    const byMaterial = new Map<number, number[]>()
    boardSelections.value.forEach((_, key) => {
      const [mid, aid] = key.split('_').map(Number)
      if (!byMaterial.has(mid)) byMaterial.set(mid, [])
      byMaterial.get(mid)!.push(aid)
    })
    const scheduledUtc = new Date(boardForm.scheduled_at).toISOString()
    for (const [mid, aids] of byMaterial) {
      await tasksApi.createBatch({
        material_id: mid,
        account_ids: aids,
        scheduled_at: scheduledUtc,
        random_offset_minutes: boardForm.random_offset,
      })
    }
    boardSelections.value.clear()
    showBoardModal.value = false
    alert(`已创建 ${boardSelections.value.size || '全部'} 个发布任务！`)
  } finally { creatingTask.value = false }
}

// ─── 加载数据 ───
async function loadAll() {
  loading.value = true
  try {
    ;[materials.value, accounts.value] = await Promise.all([
      materialsApi.list({ limit: 500 }) as Promise<any[]>,
      accountsApi.list({ limit: 500 }) as Promise<any[]>,
    ])
  } finally { loading.value = false }
}

onMounted(loadAll)
</script>
