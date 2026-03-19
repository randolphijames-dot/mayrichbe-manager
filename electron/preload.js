/**
 * Electron preload 脚本（安全桥接）
 * 只暴露必要的 API 给前端，不暴露完整 Node.js 能力
 */
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getVersion: () => ipcRenderer.invoke('get-app-version'),
  getUserDataPath: () => ipcRenderer.invoke('get-user-data-path'),
  openFileDialog: (options) => ipcRenderer.invoke('open-file-dialog', options),
  showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),
  isElectron: true,
})
