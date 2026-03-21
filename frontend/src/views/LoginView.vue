<template>
  <div class="login-page">
    <div class="login-card">
      <!-- Logo -->
      <div class="logo-area">
        <svg width="56" height="52" viewBox="0 0 64 58" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M 7 52 C 5 38, 7 18, 17 10 C 24 5, 31 9, 30 22"
                stroke="#7B4A2F" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M 30 22 C 29 9, 36 5, 43 10 C 53 18, 55 38, 53 52"
                stroke="#7B4A2F" stroke-width="6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M 46 40 L 53 52"
                stroke="#7B4A2F" stroke-width="6" stroke-linecap="round"/>
          <ellipse cx="28" cy="36" rx="9" ry="13" fill="#7B4A2F" transform="rotate(-8 28 36)"/>
          <path d="M 29 23 Q 32 36 29 49"
                stroke="rgba(255,255,255,0.4)" stroke-width="1.8" fill="none" stroke-linecap="round"/>
        </svg>
        <div class="brand-name">MAYRICHBE</div>
        <div class="brand-sub">Manager</div>
      </div>

      <!-- 分割线 -->
      <div class="divider"></div>

      <!-- 表单 -->
      <form @submit.prevent="handleLogin" class="form-area">
        <div v-if="hasUsername" class="field">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            placeholder="请输入用户名"
            autocomplete="username"
          />
        </div>

        <div class="field">
          <label>密码</label>
          <input
            ref="passwordRef"
            v-model="password"
            type="password"
            placeholder="请输入密码"
            autocomplete="current-password"
            autofocus
          />
        </div>

        <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>

        <button type="submit" class="login-btn" :disabled="loading">
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
const passwordRef = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  try {
    const resp = await axios.get('/api/v1/auth/check')
    const data = resp.data
    hasUsername.value = data.has_username
    if (!data.auth_required) {
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
    setAccessToken(data.token)
    if (data.username) localStorage.setItem('sm_username', data.username)
    localStorage.setItem('sm_is_admin', data.is_admin ? '1' : '0')
    const redirect = (router.currentRoute.value.query.redirect as string) || '/'
    router.replace(redirect)
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    errorMsg.value = detail || '无法连接服务器'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── 整体背景：温暖米白，品牌感 ── */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F2EDE8;
  padding: 16px;
}

/* ── 卡片：纯白，大圆角，精致阴影 ── */
.login-card {
  width: 380px;
  max-width: 92vw;
  background: #FFFFFF;
  border-radius: 24px;
  padding: 44px 40px 40px;
  box-shadow: 0 8px 40px rgba(90, 50, 20, 0.12), 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Logo 区域 ── */
.logo-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

.brand-name {
  font-family: 'Cinzel', Georgia, serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: #7B4A2F;
  margin-top: 4px;
}

.brand-sub {
  font-size: 12px;
  letter-spacing: 0.18em;
  color: #B08060;
  text-transform: uppercase;
  margin-top: -4px;
}

/* ── 分割线 ── */
.divider {
  height: 1px;
  background: #EDE8E3;
  margin-bottom: 28px;
}

/* ── 表单 ── */
.form-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 12px;
  font-weight: 500;
  color: #8A6A50;
  letter-spacing: 0.04em;
}

.field input {
  padding: 11px 14px;
  border: 1.5px solid #E8E0D8;
  border-radius: 10px;
  font-size: 14px;
  color: #3A2A1E;
  background: #FAF8F6;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.field input::placeholder {
  color: #C4B4A4;
}

.field input:focus {
  border-color: #7B4A2F;
  box-shadow: 0 0 0 3px rgba(123, 74, 47, 0.10);
  background: #FFFFFF;
}

/* ── 错误提示 ── */
.error-msg {
  font-size: 12px;
  color: #C0392B;
  background: #FDF0EF;
  border: 1px solid #F5C6C2;
  border-radius: 8px;
  padding: 8px 12px;
  margin: -4px 0;
}

/* ── 登录按钮 ── */
.login-btn {
  width: 100%;
  padding: 13px;
  background: #7B4A2F;
  color: white;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.06em;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s, transform 0.1s;
  margin-top: 4px;
}

.login-btn:hover:not(:disabled) {
  background: #6A3D27;
}

.login-btn:active:not(:disabled) {
  transform: scale(0.98);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
