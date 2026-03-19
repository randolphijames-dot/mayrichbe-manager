import axios from 'axios'

// 访问密码（从 localStorage 读取，设置后每次请求自动带上）
const ACCESS_TOKEN_KEY = 'sm_access_token'
export function getAccessToken() { return localStorage.getItem(ACCESS_TOKEN_KEY) || '' }
export function setAccessToken(token: string) { localStorage.setItem(ACCESS_TOKEN_KEY, token) }

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

// 自动在请求头里加访问令牌
api.interceptors.request.use(config => {
  const token = getAccessToken()
  if (token) config.headers['X-Access-Token'] = token
  return config
})

function humanizeError(raw: string): string {
  const msg = raw || ''
  // 冷却 / 频率限制
  if (msg.includes('冷却中')) return '该账号当前处于冷却期，系统稍后会自动重试，请暂时不要人工频繁操作。'
  if (msg.toLowerCase().includes('rate limit') || msg.includes('Too Many Requests')) {
    return '请求过于频繁，疑似触发平台限流，系统会自动放慢节奏，请稍后再试。'
  }
  // 账号/密码类
  if (msg.includes('未存储密码')) return '该账号尚未保存密码，请在「账号管理」中编辑该账号并填写 Instagram 密码。'
  if (msg.toLowerCase().includes('loginrequired') || msg.includes('LoginRequired')) {
    return 'Instagram 要求重新登录，请在指纹浏览器或手机里重新登录一次该账号后再试。'
  }
  if (msg.includes('未授权 YouTube OAuth')) {
    return '该账号尚未完成 YouTube 授权，请在「账号管理」中点击该账号右侧的「授权」按钮并走完流程。'
  }
  // 配置缺失
  if (msg.includes('未配置指纹浏览器 Profile ID')) {
    return '该账号没有配置浏览器窗口 ID，请在「账号管理」中补全 AdsPower/比特浏览器的 Profile ID。'
  }
  // 默认返回原始信息
  return msg
}

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const raw = err.response?.data?.detail || err.message || '请求失败'
    const friendly = humanizeError(raw)
    console.error('[API Error]', raw)
    showToast(friendly, 'error')
    return Promise.reject(err)
  }
)

function showToast(msg: string, type: 'error' | 'success' = 'success') {
  const el = document.createElement('div')
  el.textContent = msg
  Object.assign(el.style, {
    position: 'fixed', top: '20px', right: '20px', zIndex: '9999',
    padding: '10px 16px', borderRadius: '8px', fontSize: '13px', maxWidth: '320px',
    background: type === 'error' ? '#450a0a' : '#052e16',
    color: type === 'error' ? '#f87171' : '#4ade80',
    border: `1px solid ${type === 'error' ? '#991b1b' : '#166534'}`,
    boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
    transition: 'opacity 0.3s',
  })
  document.body.appendChild(el)
  setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300) }, 3000)
}

export { showToast }

// 账号管理
export const accountsApi = {
  list: (params?: object) => api.get('/accounts/', { params }),
  create: (data: object) => api.post('/accounts/', data),
  update: (id: number, data: object) => api.patch(`/accounts/${id}`, data),
  delete: (id: number) => api.delete(`/accounts/${id}`),
  checkStatus: (id: number) => api.post(`/accounts/${id}/check-status`),
  importCsv: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/accounts/import/csv', form)
  },
}

// 素材管理
export const materialsApi = {
  list: (params?: object) => api.get('/materials/', { params }),
  upload: (formData: FormData) => api.post('/materials/upload', formData),
  update: (id: number, data: object) => api.patch(`/materials/${id}`, data),
  delete: (id: number) => api.delete(`/materials/${id}`),
}

// 任务管理
export const tasksApi = {
  list: (params?: object) => api.get('/tasks/', { params }),
  create: (data: object) => api.post('/tasks/', data),
  createBatch: (data: object) => api.post('/tasks/batch', data),
  cancel: (id: number) => api.post(`/tasks/${id}/cancel`),
  retry: (id: number) => api.post(`/tasks/${id}/retry`),
}

// 日志
export const logsApi = {
  list: (params?: object) => api.get('/logs/', { params }),
}

// YouTube OAuth
export const youtubeApi = {
  startOAuth: (accountId: number) => api.get(`/youtube/oauth/start/${accountId}`),
  getChannelInfo: (accountId: number) => api.get(`/youtube/channel-info/${accountId}`),
}

// 账号资料编辑
export const profileApi = {
  batchBio: (updates: { account_id: number; biography: string }[]) =>
    api.post('/profile/batch-bio', { updates }),
  uploadAvatar: (accountId: number, file: File) => {
    const fd = new FormData(); fd.append('file', file)
    return api.post(`/profile/upload-avatar/${accountId}`, fd)
  },
  batchAvatar: (accountIds: number[]) =>
    api.post('/profile/batch-avatar', { account_ids: accountIds }),
  getInfo: (accountId: number) => api.get(`/profile/info/${accountId}`),
}

// 工具类
export const toolsApi = {
  triggerWarmup: (accountIds?: number[]) => api.post('/tools/warmup', { account_ids: accountIds || null }),
  testNotify: (channel: 'line' | 'telegram') => api.post('/tools/notify-test', { channel }),
  getSettings: () => api.get('/tools/settings'),
}

// 发布后统计
export const analyticsApi = {
  refresh: (params?: { days?: number; limit?: number }) => api.post('/analytics/refresh', null, { params }),
  summary: (params?: { days?: number }) => api.get('/analytics/summary', { params }),
  dailyRanking: (params?: { target_date?: string; limit?: number }) => api.get('/analytics/daily-ranking', { params }),
}

export default api
