<template>
  <div class="login-page" :class="{ 'theme-light': isLight }">
    <div class="login-card">
      <!-- Logo + 标题 -->
      <div class="text-center mb-6">
        <div class="logo-icon">M</div>
        <h1 class="login-title">Mayrichbe Manager</h1>
        <p class="login-subtitle">Social Media Management</p>
      </div>

      <!-- 登录表单 -->
      <form @submit.prevent="handleLogin">
        <!-- 用户名（仅在后端配置了 ACCESS_USERNAME 时显示） -->
        <div v-if="hasUsername" class="mb-3">
          <input
            v-model="username"
            type="text"
            placeholder="用户名"
            class="input text-sm"
            autocomplete="username"
          />
        </div>

        <!-- 密码 -->
        <div class="mb-3">
          <input
            ref="passwordRef"
            v-model="password"
            type="password"
            placeholder="访问密码"
            class="input text-sm"
            autocomplete="current-password"
            autofocus
          />
        </div>

        <!-- 错误提示 -->
        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <!-- 登录按钮 -->
        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          {{ loading ? '验证中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { setAccessToken } from '@/api'

const router = useRouter()
const username = ref('')
const password = ref('')
const errorMsg = ref('')
const loading = ref(false)
const hasUsername = ref(false)
const isLight = ref(localStorage.getItem('theme') === 'light')
const passwordRef = ref<HTMLInputElement | null>(null)

// 页面加载时检查后端是否需要用户名
onMounted(async () => {
  try {
    const resp = await axios.get('/api/v1/auth/check')
    const data = resp.data
    hasUsername.value = data.has_username
    if (!data.auth_required) {
      // 不需要登录，直接跳转
      router.replace('/')
    }
  } catch {
    // 后端不可达时仍显示登录页
  }
})

async function handleLogin() {
  errorMsg.value = ''
  loading.value = true
  try {
    const resp = await axios.post('/api/v1/auth/login', {
      username: username.value,
      password: password.value,
    })
    const data = resp.data
    // 存储 token、用户名、admin 状态
    setAccessToken(data.token)
    if (data.username) {
      localStorage.setItem('sm_username', data.username)
    }
    localStorage.setItem('sm_is_admin', data.is_admin ? '1' : '0')
    // 跳转到首页（或来源页）
    const redirect = (router.currentRoute.value.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    if (detail) {
      errorMsg.value = detail
    } else {
      errorMsg.value = '无法连接服务器'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
  padding: 16px;
}

.login-card {
  width: 360px;
  max-width: 90vw;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 32px;
}

.logo-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  font-size: 20px;
  font-weight: 700;
  background: var(--brand);
  color: white;
}

.login-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

.login-subtitle {
  font-size: 12px;
  margin-top: 4px;
  color: var(--text-faint);
}

.error-msg {
  font-size: 12px;
  color: #f87171;
  margin-bottom: 12px;
}

.mb-3 { margin-bottom: 12px; }
.mb-6 { margin-bottom: 24px; }
.text-center { text-align: center; }
.w-full { width: 100%; }
</style>
