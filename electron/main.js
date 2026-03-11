/**
 * Electron 主进程
 * 负责：启动内置 Python 后端、加载前端、处理应用生命周期
 */
const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron')
const path = require('path')
const { spawn, execFile } = require('child_process')
const http = require('http')
const fs = require('fs')

const BACKEND_PORT = 8000
let mainWindow = null
let splashWindow = null
let backendProcess = null

// ─── 启动画面 ─────────────────────────────────────────
function createSplash() {
  splashWindow = new BrowserWindow({
    width: 400, height: 300,
    frame: false, transparent: true, resizable: false,
    webPreferences: { nodeIntegration: false },
  })
  splashWindow.loadFile(path.join(__dirname, 'splash.html'))
  splashWindow.center()
}

// ─── 主窗口 ───────────────────────────────────────────
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400, height: 900,
    minWidth: 1100, minHeight: 700,
    show: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  })

  // 加载后端提供的 index.html（FastAPI 同时服务静态前端）
  mainWindow.loadURL(`http://localhost:${BACKEND_PORT}`)

  mainWindow.once('ready-to-show', () => {
    if (splashWindow) { splashWindow.destroy(); splashWindow = null }
    mainWindow.show()
    mainWindow.maximize()
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // 外部链接在系统浏览器打开
    if (!url.startsWith(`http://localhost`)) {
      shell.openExternal(url)
      return { action: 'deny' }
    }
    return { action: 'allow' }
  })
}

// ─── Python 后端启动 ───────────────────────────────────
function getPythonExecutable() {
  const resourcesPath = process.resourcesPath || __dirname

  // 打包后：使用内置 Python（PyInstaller 生成的可执行文件）
  const bundledNames = {
    darwin: 'backend_mac',
    win32: 'backend_win.exe',
    linux: 'backend_linux',
  }
  const bundledExe = path.join(resourcesPath, 'backend', bundledNames[process.platform] || 'backend')
  if (fs.existsSync(bundledExe)) {
    console.log('[Main] 使用内置 Python 后端:', bundledExe)
    return { exe: bundledExe, args: [], useBundled: true }
  }

  // 开发模式：使用系统 Python + uvicorn
  const venvPython = path.join(__dirname, '..', 'backend', '.venv', 'bin', 'python3')
  const sysPython = process.platform === 'win32' ? 'python' : 'python3'
  const pythonExe = fs.existsSync(venvPython) ? venvPython : sysPython

  console.log('[Main] 开发模式，使用 Python:', pythonExe)
  return {
    exe: pythonExe,
    args: ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
    useBundled: false,
    cwd: path.join(__dirname, '..', 'backend'),
  }
}

function startBackend() {
  const { exe, args, useBundled, cwd } = getPythonExecutable()

  const userData = app.getPath('userData')
  try { fs.mkdirSync(path.join(userData, 'uploads'), { recursive: true }) } catch (_) {}

  const env = {
    ...process.env,
    PORT: String(BACKEND_PORT),
    DATABASE_URL: `sqlite:///${path.join(userData, 'social_manager.db')}`,
    UPLOAD_DIR: path.join(userData, 'uploads'),
  }

  const logPath = path.join(app.getPath('userData'), 'backend.log')
  const opts = {
    env,
    cwd: cwd || (useBundled ? path.dirname(exe) : undefined),
    stdio: ['ignore', 'pipe', 'pipe'],
  }

  // Windows：使用 execFile 防止 cmd 弹窗
  if (process.platform === 'win32' && !useBundled) {
    backendProcess = spawn(exe, args, { ...opts, windowsHide: true })
  } else {
    backendProcess = spawn(exe, args, opts)
  }

  const logStream = fs.createWriteStream(logPath, { flags: 'a' })
  logStream.write(`\n--- ${new Date().toISOString()} 启动 ---\n`)
  backendProcess.stdout?.on('data', d => {
    const msg = d.toString().trim()
    console.log('[Backend]', msg)
    logStream.write(msg + '\n')
  })
  backendProcess.stderr?.on('data', d => {
    const msg = d.toString().trim()
    console.error('[Backend ERR]', msg)
    logStream.write('ERR: ' + msg + '\n')
  })
  backendProcess.on('exit', (code) => {
    console.warn(`[Backend] 进程退出，code=${code}`)
    logStream.write(`退出 code=${code}\n`)
    logStream.end()
  })

  console.log('[Main] Python 后端已启动，PID:', backendProcess.pid)
}

// ─── 等待后端就绪 ─────────────────────────────────────
// 首次启动 PyInstaller 解压约 10-20 秒，超时设为 90 秒
function waitForBackend(attempts = 0, maxAttempts = 180) {
  return new Promise((resolve, reject) => {
    const check = () => {
      http.get(`http://localhost:${BACKEND_PORT}/health`, (res) => {
        if (res.statusCode === 200) { resolve(); return }
        retry()
      }).on('error', retry)
    }
    const retry = () => {
      if (attempts++ >= maxAttempts) { reject(new Error('Backend 启动超时')); return }
      setTimeout(check, 500)
    }
    // 打包版首次启动 PyInstaller 需解压（可能 15-20 秒），先等 12 秒再检测
    const delay = process.defaultApp ? 0 : 12000
    setTimeout(check, delay)
  })
}

// ─── 应用生命周期 ─────────────────────────────────────
app.whenReady().then(async () => {
  createSplash()
  startBackend()

  try {
    await waitForBackend()
    createMainWindow()
  } catch (err) {
    const logPath = path.join(app.getPath('userData'), 'backend.log')
    dialog.showErrorBox('启动失败', `后端服务启动失败：${err.message}\n\n可能原因：1) 端口 8000 被占用  2) 首次启动较慢（请再试一次）\n\n日志：${logPath}`)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow()
})

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    console.log('[Main] 关闭 Python 后端进程')
    backendProcess.kill('SIGTERM')
  }
})

// ─── IPC：前端可调用的 Native 功能 ───────────────────
ipcMain.handle('get-app-version', () => app.getVersion())
ipcMain.handle('get-user-data-path', () => app.getPath('userData'))
ipcMain.handle('open-file-dialog', async (_, options) => {
  const result = await dialog.showOpenDialog(mainWindow, options)
  return result
})
ipcMain.handle('show-save-dialog', async (_, options) => {
  return dialog.showSaveDialog(mainWindow, options)
})
