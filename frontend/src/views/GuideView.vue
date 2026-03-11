<template>
  <div class="max-w-3xl mx-auto flex flex-col gap-6">
    <!-- 标题 -->
    <div class="card" style="background: linear-gradient(135deg, #0c1a2e 0%, #1e293b 100%); border-color:#1d4ed8">
      <div class="flex items-center gap-3 mb-2">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center" style="background:#0ea5e9">
          <BookOpen :size="20" color="white" />
        </div>
        <div>
          <h1 class="text-lg font-bold" style="color:var(--text-primary)">Mayrichbe Manager 使用说明</h1>
          <p class="text-xs" style="color:var(--text-faint)">INS & YouTube 矩阵管理系统 · 完整操作手册</p>
        </div>
      </div>
    </div>

    <!-- Q&A 快速解答 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <HelpCircle :size="16" style="color:#0ea5e9" /> 常见问题快速解答
      </h2>
      <div class="flex flex-col gap-3">
        <div v-for="qa in faqs" :key="qa.q" class="rounded-lg p-3" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-1" style="color:var(--text-primary)">❓ {{ qa.q }}</p>
          <p class="text-xs leading-relaxed" style="color:var(--text-muted)" v-html="qa.a"></p>
        </div>
      </div>
    </div>

    <!-- 第一步：环境准备 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#0ea5e9; color:white">1</span>
        环境准备（首次使用必须完成）
      </h2>
      <div class="flex flex-col gap-3">
        <div v-for="step in setupSteps" :key="step.title" class="flex gap-3 p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <span class="text-xl flex-shrink-0">{{ step.emoji }}</span>
          <div>
            <p class="text-sm font-medium" style="color:var(--text-primary)">{{ step.title }}</p>
            <p class="text-xs mt-0.5 leading-relaxed" style="color:var(--text-muted)" v-html="step.desc"></p>
            <code v-if="step.cmd" class="text-xs mt-1 block px-2 py-1 rounded" style="background:var(--bg-base); color:#4ade80; border:1px solid var(--border-light)">{{ step.cmd }}</code>
          </div>
        </div>
      </div>
    </div>

    <!-- 第二步：添加账号 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#a78bfa; color:white">2</span>
        添加账号详细说明
      </h2>

      <div class="mb-4 p-3 rounded-lg" style="background:#0c1a2e; border:1px solid #1d4ed8">
        <p class="text-xs font-semibold mb-1" style="color:#60a5fa">📌 核心原则</p>
        <p class="text-xs leading-relaxed" style="color:var(--text-muted)">
          每个 Instagram 账号必须对应一个独立的指纹浏览器 Profile + 独立代理 IP。
          这是防封号的基础，平台通过「设备指纹」识别多账号关联。
        </p>
      </div>

      <div class="grid grid-cols-2 gap-3 mb-4">
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-2" style="color:var(--text-primary)">📱 方式 A：AdsPower</p>
          <ol class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>1. 下载安装 AdsPower（官网：adspower.net）</li>
            <li>2. 为每个 INS 账号新建一个 Profile</li>
            <li>3. 在 Profile 里配置代理 IP</li>
            <li>4. 手动登录 Instagram（只需一次）</li>
            <li>5. 复制 Profile ID（数字+字母串）</li>
            <li>6. 在本系统填入 browser_profile_id</li>
          </ol>
        </div>
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-2" style="color:var(--text-primary)">🌐 方式 B：比特浏览器</p>
          <ol class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>1. 下载比特浏览器（bitbrowser.cn）</li>
            <li>2. 同样为每账号创建独立窗口</li>
            <li>3. 配置代理 IP + 登录账号</li>
            <li>4. 查看「窗口 ID」（在列表里）</li>
            <li>5. 选择 browser_type = bitbrowser</li>
            <li>6. 填入对应 Profile ID</li>
          </ol>
        </div>
      </div>

      <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
        <p class="text-sm font-medium mb-2" style="color:var(--text-primary)">📊 CSV 批量导入格式</p>
        <div class="overflow-x-auto">
          <table class="table text-xs">
            <thead><tr>
              <th>字段</th><th>说明</th><th>示例</th><th>必填</th>
            </tr></thead>
            <tbody>
              <tr v-for="col in csvCols" :key="col.f">
                <td class="font-mono" style="color:#60a5fa">{{ col.f }}</td>
                <td>{{ col.desc }}</td>
                <td class="font-mono" style="color:var(--text-muted)">{{ col.eg }}</td>
                <td><span :class="col.req ? 'badge-red badge' : 'badge-gray badge'">{{ col.req ? '必填' : '可选' }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
        <a href="/账号导入模版.csv" download class="btn btn-primary btn-sm mt-3">
          <Download :size="12" /> 下载 CSV 模版
        </a>
      </div>
    </div>

    <!-- 第三步：上传素材 + 分配账号 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#4ade80; color:#052e16">3</span>
        上传素材 & 分配账号
      </h2>
      <div class="flex flex-col gap-2">
        <div v-for="(s, i) in materialSteps" :key="i" class="flex gap-3 items-start p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <span class="badge badge-blue flex-shrink-0">Step {{ i+1 }}</span>
          <p class="text-xs leading-relaxed" style="color:var(--text-muted)" v-html="s"></p>
        </div>
      </div>
    </div>

    <!-- 第四步：系统整体逻辑（从素材到发布） -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#fbbf24; color:#1c1917">4</span>
        系统整体逻辑（从素材到发布）
      </h2>
      <div class="p-3 rounded-lg mb-2" style="background:var(--bg-base); border:1px solid var(--border)">
        <p class="text-xs leading-relaxed" style="color:var(--text-muted)">
          这套系统可以简单理解为：<strong style="color:var(--text-primary)">素材仓库 + 账号列表 + 定时闹钟</strong> 三个东西组合在一起。
        </p>
      </div>
      <ol class="list-decimal list-inside text-xs space-y-1.5" style="color:var(--text-muted)">
        <li><strong style="color:var(--text-primary)">先建账号</strong>：在「账号管理」里录入所有 INS / YT 账号，可选填密码、分组、浏览器 Profile。</li>
        <li><strong style="color:var(--text-primary)">再传素材</strong>：把视频 / 图片传到「素材库」，按日期 / 话题打标签。</li>
        <li><strong style="color:var(--text-primary)">把素材分配给账号</strong>：在「一键发布」里选中素材 → 选择要发的账号（一个素材可以对应很多账号）。</li>
        <li><strong style="color:var(--text-primary)">设定发布时间</strong>：选择一个本地时间 + 可选的随机偏移（比如 30 分钟内随机），系统会自动错峰排队。</li>
        <li><strong style="color:var(--text-primary)">内置定时器负责记住所有闹钟</strong>：即使你中间关掉软件，只要电脑在，到点就会自动执行。</li>
        <li><strong style="color:var(--text-primary)">执行时分两条路</strong>：\n          <ul class="list-disc list-inside mt-1 space-y-0.5">\n            <li>INS：优先走「模拟手机」的 instagrapi（更轻、更省资源），失败时可以用指纹浏览器补救。</li>\n            <li>YT：用官方 API 发视频，走你在 Google Cloud 配置的 OAuth 授权。</li>\n          </ul>\n        </li>
      </ol>
      <p class="text-xs mt-3" style="color:var(--text-faint)">你可以把它当作：平时只在「账号管理 / 素材库 / 发布任务」三个页面来回切换，其它高级配置一旦弄好后基本不用再管。</p>
    </div>

    <!-- 第五步：YouTube API 配置 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#ef4444; color:white">5</span>
        YouTube API 配置（仅 YT 账号需要）
      </h2>
      <div class="flex flex-col gap-2">
        <div v-for="(s, i) in ytSteps" :key="i" class="flex gap-3 p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <span class="badge badge-red flex-shrink-0">{{ i+1 }}</span>
          <p class="text-xs leading-relaxed" style="color:var(--text-muted)" v-html="s"></p>
        </div>
      </div>
    </div>

    <!-- 给同事/外包安装使用的小白说明 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#22c55e; color:white">6</span>
        给团队/外包安装使用（桌面应用）
      </h2>
      <div class="grid grid-cols-2 gap-3">
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-1" style="color:var(--text-primary)">🍎 Mac 用户怎么装</p>
          <ol class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>1. 你在开发机上运行：<code style="color:#4ade80">bash electron/scripts/build-app.sh</code></li>
            <li>2. 在 <code style="color:#60a5fa">dist-electron/</code> 目录里找到生成的 <code>.dmg</code> 文件。</li>
            <li>3. 发给同事，他们只需要：双击 .dmg → 把图标拖到「应用程序」。</li>
            <li>4. 第一次打开如被 macOS 拦截，点「仍要打开」即可。</li>
          </ol>
        </div>
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-1" style="color:var(--text-primary)">🪟 Windows 用户怎么装</p>
          <ol class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>1. 把代码拉到一台 Windows 电脑。</li>
            <li>2. 运行 <code style="color:#4ade80">electron\\scripts\\build-backend.bat</code> 打包后端。</li>
            <li>3. 再运行：<code style="color:#4ade80">cd electron && npm install && npm run build:win</code></li>
            <li>4. 在 <code style="color:#60a5fa">dist-electron/</code> 里会生成安装包（.exe），发给同事双击安装即可。</li>
          </ol>
        </div>
      </div>
      <p class="text-xs mt-3" style="color:var(--text-faint)">安装好的桌面版，会自动内置 Python 和定时引擎，<strong style="color:var(--text-primary)">使用者无需安装 Python / Redis / Celery</strong>，只需要正常登录 Instagram / YouTube 即可。</p>
    </div>

    <!-- 新增功能：高级运营工具 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-4 flex items-center gap-2" style="color:var(--text-primary)">
        <span class="w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0" style="background:#a855f7; color:white">7</span>
        高级运营工具（矩阵增长必备）
      </h2>
      <div class="flex flex-col gap-3">

        <!-- 批量改资料 -->
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-base">🪪</span>
            <p class="text-sm font-semibold" style="color:var(--text-primary)">批量改资料（简介 + 头像）</p>
          </div>
          <ul class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>• 在「批量改资料」页面，选择账号分组，一次性为多个账号设置不同简介和头像</li>
            <li>• 简介支持「<strong style="color:var(--text-primary)">模板 + 序号</strong>」功能：输入 <code style="color:#60a5fa">財経情報発信中🔥 #{{序号}}</code>，系统会自动替换成 <code style="color:#4ade80">#01 #02...</code></li>
            <li>• 头像可以每个账号单独上传不同图片</li>
            <li>• 所有修改通过模拟 Android 手机的方式执行，不触发「批量操作」风控</li>
          </ul>
        </div>

        <!-- 智能养号 -->
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-base">🌱</span>
            <p class="text-sm font-semibold" style="color:var(--text-primary)">智能养号（新账号必做！）</p>
          </div>
          <ul class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>• 在「工具箱」里触发「批量养号」，系统会模拟正常用户行为：刷 Feed → 随机点赞 1-2 条 → 浏览发现页 → 查看故事</li>
            <li>• <strong style="color:#fbbf24">新账号 (≤30天) 至少先养 1 周再发内容</strong>，有历史活跃记录的账号风险大幅降低</li>
            <li>• 支持两种模式：无需浏览器的「模拟手机模式」，以及打开指纹浏览器的「浏览器模式」</li>
            <li>• 建议每天执行一次，时间不规律（早 9 点 / 晚 7 点轮换），模拟真人使用节奏</li>
          </ul>
        </div>

        <!-- 消息中心 -->
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-base">📬</span>
            <p class="text-sm font-semibold" style="color:var(--text-primary)">消息中心（统一回复评论 + 私信）</p>
          </div>
          <ul class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>• 在「消息中心」页面，所有账号的评论和私信汇聚到一个界面，无需逐个登录 Instagram App</li>
            <li>• 点击任意消息 → 右侧弹出回复框，可直接发送回复</li>
            <li>• 内置 5 条日文快捷话术，点击即填入，节省时间</li>
            <li>• <strong style="color:var(--text-primary)">数据有 60 秒缓存</strong>，手动点「刷新消息」会立即重新从 Instagram 拉取最新数据</li>
            <li>• 注意：拉取消息需要账号已保存密码，且每次请求会产生 API 调用（建议按需手动刷新，不要频繁自动刷新）</li>
          </ul>
        </div>

        <!-- 自动截流 -->
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:2px solid #92400e">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-base">⚡</span>
            <p class="text-sm font-semibold" style="color:var(--text-primary)">自动截流（引流工具）</p>
            <span class="badge" style="background:#92400e;color:#fbbf24;font-size:10px">风险较高 谨慎使用</span>
          </div>
          <ul class="text-xs space-y-1" style="color:var(--text-muted)">
            <li>• 在「自动截流」页面，选择模式：<strong style="color:var(--text-primary)">话题标签截流</strong>（在 #财经 等话题下互动）或 <strong style="color:var(--text-primary)">对标账号截流</strong>（找竞品的粉丝互动）</li>
            <li>• 互动动作：<strong style="color:#4ade80">点赞</strong>（安全，适合新账号）或 <strong style="color:#60a5fa">评论</strong>（引流效果更强，适合成熟账号）</li>
            <li>• 评论话术支持「<code style="color:#60a5fa">|</code>分隔多条轮换」，例如：<code style="color:var(--text-faint)">フォローよろしく！ | 参考になりました！ | プロフ見てね✨</code></li>
            <li>• <strong style="color:#fbbf24">硬性限制：每账号每次最多 10 个互动，动作间隔 30–90 秒随机</strong></li>
            <li>• 最佳实践：每天最多执行 2 次，每次间隔 6 小时以上；新账号（≤30天）禁止使用</li>
          </ul>
        </div>

      </div>
    </div>

    <!-- 通知配置 -->
    <div class="card">
      <h2 class="text-sm font-bold mb-3 flex items-center gap-2" style="color:var(--text-primary)">
        <Bell :size="16" style="color:#0ea5e9" /> 发布通知配置（可选）
      </h2>
      <div class="grid grid-cols-2 gap-3">
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-1" style="color:var(--text-primary)">Line Notify</p>
          <p class="text-xs mb-2" style="color:var(--text-muted)">访问 notify.line.me 申请 Token，填入 .env</p>
          <code class="text-xs px-2 py-1 rounded block" style="background:var(--bg-base); color:#4ade80; border:1px solid var(--border-light)">LINE_NOTIFY_TOKEN=your_token</code>
        </div>
        <div class="p-3 rounded-lg" style="background:var(--bg-base); border:1px solid var(--border)">
          <p class="text-sm font-medium mb-1" style="color:var(--text-primary)">Telegram</p>
          <p class="text-xs mb-2" style="color:var(--text-muted)">用 @BotFather 创建 Bot，获取 Token 和 Chat ID</p>
          <code class="text-xs px-2 py-1 rounded block" style="background:var(--bg-base); color:#4ade80; border:1px solid var(--border-light)">TELEGRAM_BOT_TOKEN=xxx<br>TELEGRAM_CHAT_ID=yyy</code>
        </div>
      </div>
    </div>

    <!-- 完整启动命令 -->
    <div class="card" style="border-color:#166534">
      <h2 class="text-sm font-bold mb-3 flex items-center gap-2" style="color:#4ade80">
        <Terminal :size="16" /> 完整启动流程
      </h2>
      <div class="flex flex-col gap-2">
        <div v-for="cmd in startCmds" :key="cmd.label" class="flex items-center gap-3 p-2 rounded-lg" style="background:#052e16">
          <span class="text-xs font-medium w-28 flex-shrink-0" style="color:#86efac">{{ cmd.label }}</span>
          <code class="text-xs" style="color:#4ade80">{{ cmd.cmd }}</code>
        </div>
      </div>
      <p class="text-xs mt-3" style="color:var(--text-faint)">✨ 或者直接运行：<code style="color:#4ade80">./start.sh</code>（一键启动所有服务）</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BookOpen, HelpCircle, Download, Bell, Terminal } from 'lucide-vue-next'

const faqs = [
  {
    q: '现在是完整版吗？还需要配置什么 API？',
    a: '核心功能已经齐全。使用前只需要：① 正常运行 backend + frontend（或安装桌面版应用）② 如用 YouTube：在 Google Cloud 申请 OAuth2 密钥 ③ 如想用指纹浏览器方式：安装 AdsPower 或比特浏览器。Instagram 本身不需要官方 API，也不再需要安装 Redis/Celery。',
  },
  {
    q: '上传素材后怎么分配到对应账号发布？',
    a: '两种方式：① 上传时直接选择目标账号（在素材库上传弹窗里，底部有账号多选）② 上传后在素材卡片点「安排发布」，可重新选择账号和发布时间。一个素材可分配给多个账号，系统会分别创建独立发布任务。',
  },
  {
    q: 'Redis 和 Celery 是什么？不用它们可以吗？',
    a: '以前的版本依赖 Redis + Celery 来做「定时发布」，现在已经改成内置的轻量定时器，所有任务直接保存在同一份数据库里。结论：<strong style="color:var(--text-primary)">你完全不用再安装或启动 Redis/Celery</strong>，只要后端程序在运行，定时发布就会自动执行。',
  },
  {
    q: '比特浏览器和 AdsPower 怎么选？',
    a: '两者功能类似，都是指纹浏览器。整体推荐优先用「模拟手机（instagrapi）」方式做矩阵发帖；当某个账号风控更严/经常异常时，再为这个账号单独切换到 AdsPower 或比特浏览器方案。',
  },
  {
    q: '不想存密码，手动登录可以吗？',
    a: '完全可以。在 AdsPower/比特浏览器里手动登录一次后，Cookie 会存在 Profile 里。系统每次发布前会先检查是否已登录，已登录就直接用，不需要密码。密码存储是可选的自动登录功能。',
  },
]

const setupSteps = [
  { emoji: '🌐', title: '（可选）安装指纹浏览器', desc: '如果你希望用「开浏览器」的方式发 INS：下载 AdsPower（adspower.net）或比特浏览器（bitbrowser.cn），为每个账号创建独立 Profile 并配好代理 IP。手动登录一次 Instagram 即可，Cookie 会自动保存。' },
  { emoji: '📦', title: '配置环境变量', desc: '复制 backend/.env.example 为 .env，填写 YouTube OAuth 密钥（如有）和通知 Token（可选）。', cmd: 'cp backend/.env.example backend/.env' },
  { emoji: '🚀', title: '启动系统（开发模式）', desc: '运行 start.sh 一键启动后端 + 前端 + 内置定时器，无需 Redis/Celery。', cmd: './start.sh' },
  { emoji: '💻', title: '打包成桌面应用（可选）', desc: '在 Mac 上运行 electron/scripts/build-app.sh，会生成 .dmg 安装包；在 Windows 上运行 build-backend.bat + npm run build:win，会生成 .exe 安装包，方便发给团队使用。', cmd: 'bash electron/scripts/build-app.sh' },
]

const materialSteps = [
  '点击左侧「素材库」→「上传素材」，选择视频或图片文件（支持 mp4/mov/jpg/png）。',
  '填写发布文案（INS Caption）或 YouTube 标题/描述。',
  '<strong style="color:var(--text-primary)">关键步骤</strong>：在「目标账号」区域点击要发布的账号（可多选，已选的高亮显示），相同素材可同时分配给多个账号。',
  '上传完成后，在素材卡片点「安排发布」，选择发布时间和随机偏移范围（建议设 30 分钟，各账号在此范围内错峰发布）。',
  '在「发布任务」页查看任务状态。系统内置定时器会自动到点执行，无需 Redis/Celery。',
]

const ytSteps = [
  '访问 <a href="https://console.cloud.google.com" target="_blank" style="color:#60a5fa">Google Cloud Console</a>，新建项目。',
  '进入「API & Services」→「启用 API」，搜索并启用 <strong style="color:var(--text-primary)">YouTube Data API v3</strong>。',
  '进入「凭据」→「创建凭据」→「OAuth 客户端 ID」，应用类型选「Web 应用」。',
  '授权重定向 URI 填：<code style="color:#60a5fa">http://localhost:8000/api/v1/youtube/oauth/callback</code>',
  '复制 Client ID 和 Client Secret，填入 backend/.env 文件。',
  '在账号管理页找到 YouTube 账号，点「授权 YT」按钮，完成 OAuth 绑定。<strong style="color:#fbbf24">30+ 账号建议申请多个 Google Cloud 项目</strong>（每个项目每日 10,000 单位配额）。',
]

const startCmds = [
  { label: '① 一键启动（推荐）', cmd: './start.sh' },
  { label: '② 仅启动后端 API', cmd: 'cd backend && uvicorn app.main:app --reload' },
  { label: '③ 仅启动前端', cmd: 'cd frontend && npm run dev' },
]

const csvCols = [
  { f: 'name', desc: '账号显示名（内部用）', eg: '日本財経_01', req: true },
  { f: 'username', desc: '平台用户名', eg: 'finance_jp_01', req: true },
  { f: 'platform', desc: 'instagram 或 youtube', eg: 'instagram', req: true },
  { f: 'group_name', desc: '分组名', eg: '财经类', req: false },
  { f: 'proxy', desc: '代理地址', eg: 'http://u:p@ip:port', req: false },
  { f: 'browser_type', desc: 'adspower 或 bitbrowser', eg: 'adspower', req: false },
  { f: 'browser_profile_id', desc: '指纹浏览器 Profile ID', eg: 'abc123', req: false },
  { f: 'notes', desc: '备注', eg: '主账号', req: false },
]
</script>
