<template>
  <div class="flex flex-col gap-4">
    <!-- 非 admin 无权限提示 -->
    <div v-if="!isAdmin" class="card p-8 text-center">
      <p class="text-sm" style="color:var(--text-muted)">无权限访问此页面，请联系管理员。</p>
    </div>

    <template v-else>
      <!-- 当前账户卡片 -->
      <div class="card p-4">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs" style="color:var(--text-faint)">当前账户</p>
            <p class="text-sm font-semibold mt-1" style="color:var(--text-primary)">{{ currentUser.username }}</p>
            <p class="text-xs mt-0.5" style="color:var(--text-muted)">{{ currentUser.is_admin ? '管理员' : '普通用户' }}</p>
          </div>
          <button class="btn btn-sm" @click="openChangePassword">修改密码</button>
        </div>
      </div>

      <!-- 用户列表 -->
      <div class="card">
        <div class="flex items-center justify-between p-4 border-b" style="border-color:var(--border)">
          <span class="text-sm font-semibold" style="color:var(--text-primary)">所有用户</span>
          <button class="btn btn-primary btn-sm" @click="openCreateModal">+ 新建用户</button>
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr style="background:var(--bg-base)">
              <th class="th">ID</th>
              <th class="th">用户名</th>
              <th class="th">显示名</th>
              <th class="th">角色</th>
              <th class="th">状态</th>
              <th class="th">创建时间</th>
              <th class="th">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in users" :key="u.id" class="border-b" style="border-color:var(--border)">
              <td class="td" style="color:var(--text-faint)">{{ u.id }}</td>
              <td class="td font-medium" style="color:var(--text-primary)">{{ u.username }}</td>
              <td class="td" style="color:var(--text-muted)">{{ u.display_name }}</td>
              <td class="td">
                <span class="px-2 py-0.5 rounded text-xs" :style="u.is_admin ? 'background:#1e3a5f;color:#60a5fa' : 'background:var(--bg-base);color:var(--text-muted)'">
                  {{ u.is_admin ? '管理员' : '普通' }}
                </span>
              </td>
              <td class="td">
                <span class="px-2 py-0.5 rounded text-xs" :style="u.is_active ? 'background:#052e16;color:#4ade80' : 'background:#450a0a;color:#f87171'">
                  {{ u.is_active ? '正常' : '已禁用' }}
                </span>
              </td>
              <td class="td" style="color:var(--text-faint)">{{ u.created_at }}</td>
              <td class="td">
                <div class="flex gap-2">
                  <button class="text-xs px-2 py-1 rounded" style="background:var(--bg-base);color:var(--text-muted);border:1px solid var(--border)" @click="openEditModal(u)">编辑</button>
                  <button v-if="u.id !== currentUser.id && u.is_active" class="text-xs px-2 py-1 rounded" style="background:#450a0a;color:#f87171;border:1px solid #991b1b" @click="handleDisable(u)">
                    禁用
                  </button>
                  <span v-if="u.id !== currentUser.id && !u.is_active" class="text-xs px-2 py-1 rounded" style="color:var(--text-faint)">已禁用</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="users.length === 0" class="p-8 text-center text-sm" style="color:var(--text-faint)">暂无用户</div>
      </div>
    </template>

    <!-- 创建/编辑弹窗 -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-card">
        <h3 class="text-sm font-semibold mb-4" style="color:var(--text-primary)">{{ modalTitle }}</h3>
        <div class="flex flex-col gap-3">
          <div v-if="modalMode === 'create'">
            <label class="label">用户名</label>
            <input v-model="form.username" type="text" class="input text-sm" placeholder="至少 2 个字符" />
          </div>
          <div v-if="modalMode === 'create' || modalMode === 'password'">
            <label class="label">{{ modalMode === 'password' ? '新密码' : '密码' }}</label>
            <input v-model="form.password" type="password" class="input text-sm" placeholder="至少 4 个字符" />
          </div>
          <div v-if="modalMode === 'create'">
            <label class="label">显示名称（可选）</label>
            <input v-model="form.display_name" type="text" class="input text-sm" placeholder="留空则使用用户名" />
          </div>
          <div v-if="modalMode === 'create'" class="flex items-center gap-2">
            <input v-model="form.is_admin" type="checkbox" id="chk-admin" />
            <label for="chk-admin" class="text-xs" style="color:var(--text-muted)">设为管理员</label>
          </div>
          <div v-if="modalMode === 'edit'" class="flex flex-col gap-3">
            <div>
              <label class="label">新密码（留空不修改）</label>
              <input v-model="form.password" type="password" class="input text-sm" placeholder="留空则不修改密码" />
            </div>
            <div>
              <label class="label">显示名称</label>
              <input v-model="form.display_name" type="text" class="input text-sm" />
            </div>
            <div class="flex items-center gap-2">
              <input v-model="form.is_admin" type="checkbox" id="chk-admin-edit" />
              <label for="chk-admin-edit" class="text-xs" style="color:var(--text-muted)">管理员</label>
            </div>
            <div class="flex items-center gap-2">
              <input v-model="form.is_active" type="checkbox" id="chk-active-edit" />
              <label for="chk-active-edit" class="text-xs" style="color:var(--text-muted)">启用</label>
            </div>
          </div>
          <p v-if="formError" class="text-xs" style="color:#f87171">{{ formError }}</p>
          <div class="flex gap-2 mt-2">
            <button class="btn btn-primary btn-sm flex-1" :disabled="saving" @click="handleSubmit">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="btn btn-sm flex-1" @click="closeModal">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { usersApi, authApi } from '@/api'

interface UserItem {
  id: number
  username: string
  display_name: string
  is_admin: boolean
  is_active: boolean
  created_at: string
}

const isAdmin = ref(localStorage.getItem('sm_is_admin') === '1')
const currentUser = reactive({ id: 0, username: '', is_admin: false })
const users = ref<UserItem[]>([])

const showModal = ref(false)
const modalMode = ref<'create' | 'edit' | 'password'>('create')
const modalTitle = ref('')
const editingUserId = ref(0)
const saving = ref(false)
const formError = ref('')
const form = reactive({
  username: '',
  password: '',
  display_name: '',
  is_admin: false,
  is_active: true,
})

function resetForm() {
  form.username = ''
  form.password = ''
  form.display_name = ''
  form.is_admin = false
  form.is_active = true
  formError.value = ''
}

function openCreateModal() {
  resetForm()
  modalMode.value = 'create'
  modalTitle.value = '新建用户'
  showModal.value = true
}

function openEditModal(u: UserItem) {
  resetForm()
  modalMode.value = 'edit'
  modalTitle.value = `编辑用户: ${u.username}`
  editingUserId.value = u.id
  form.display_name = u.display_name
  form.is_admin = u.is_admin
  form.is_active = u.is_active
  showModal.value = true
}

function openChangePassword() {
  resetForm()
  modalMode.value = 'password'
  modalTitle.value = '修改密码'
  editingUserId.value = currentUser.id
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function loadUsers() {
  try {
    const data: any = await usersApi.list()
    users.value = data
  } catch {
    // 权限不足或网络错误
  }
}

async function loadMe() {
  try {
    const me: any = await authApi.me()
    currentUser.id = me.id
    currentUser.username = me.username
    currentUser.is_admin = me.is_admin
    isAdmin.value = me.is_admin
  } catch {
    // token 失效
  }
}

async function handleSubmit() {
  formError.value = ''
  saving.value = true
  try {
    if (modalMode.value === 'create') {
      if (!form.username || form.username.trim().length < 2) {
        formError.value = '用户名至少 2 个字符'
        return
      }
      if (!form.password || form.password.length < 4) {
        formError.value = '密码至少 4 个字符'
        return
      }
      await usersApi.create({
        username: form.username.trim(),
        password: form.password,
        display_name: form.display_name || undefined,
        is_admin: form.is_admin,
      })
    } else if (modalMode.value === 'password') {
      if (!form.password || form.password.length < 4) {
        formError.value = '密码至少 4 个字符'
        return
      }
      await usersApi.update(editingUserId.value, { password: form.password })
    } else if (modalMode.value === 'edit') {
      const payload: any = {
        display_name: form.display_name,
        is_admin: form.is_admin,
        is_active: form.is_active,
      }
      if (form.password && form.password.length > 0) {
        if (form.password.length < 4) {
          formError.value = '密码至少 4 个字符'
          return
        }
        payload.password = form.password
      }
      await usersApi.update(editingUserId.value, payload)
    }
    closeModal()
    await loadUsers()
  } catch (e: any) {
    formError.value = e?.response?.data?.detail || '操作失败'
  } finally {
    saving.value = false
  }
}

async function handleDisable(u: UserItem) {
  if (!confirm(`确定要禁用用户 "${u.username}" 吗？`)) return
  try {
    await usersApi.delete(u.id)
    await loadUsers()
  } catch {
    // error handled by interceptor
  }
}

onMounted(async () => {
  await loadMe()
  if (isAdmin.value) {
    await loadUsers()
  }
})
</script>

<style scoped>
.th {
  text-align: left;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.td {
  padding: 10px 12px;
}
.label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-faint);
  margin-bottom: 4px;
}
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-card {
  width: 400px;
  max-width: 90vw;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
}
</style>
