#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# 完整打包流程（Mac 机上执行）：
#   1. 构建前端 Vue 产物 → backend/static
#   2. PyInstaller 打包 Python → electron/backend-dist/
#   3. electron-builder 打包 Electron → dist-electron/
# ─────────────────────────────────────────────────────────────────
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  矩阵管理系统 - 桌面应用打包脚本"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ① 前端构建
echo "📦 Step 1/3: 构建前端..."
cd "$ROOT/frontend"
npm run build
# 将 dist 复制到 backend/static 供 FastAPI 静态托管
rm -rf "$ROOT/backend/static"
cp -r "$ROOT/frontend/dist" "$ROOT/backend/static"
echo "✅ 前端构建完成"

# ② Python 后端打包
echo "🐍 Step 2/3: 打包 Python 后端..."
bash "$ROOT/electron/scripts/build-backend.sh"

# ③ Electron 打包（Mac DMG）
echo "⚡ Step 3/3: 打包 Electron 应用..."
cd "$ROOT/electron"

# 安装 Electron 依赖（如果尚未安装）
if [ ! -d "node_modules" ]; then
  npm install
fi

# 将 PyInstaller 产物拷贝到 electron 目录供 electron-builder 打包进去
BACKEND_DIST="$ROOT/electron/backend-dist"
if [ -f "$BACKEND_DIST/backend_mac" ]; then
  mkdir -p "$ROOT/electron/assets"
  # electron-builder extraResources 会负责复制 backend 目录
  cp "$BACKEND_DIST/backend_mac" "$ROOT/backend/"
fi

# 打包 Mac（同时支持 Intel 和 M1/M2）
npm run build:mac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 打包完成！"
echo "   Mac DMG: $ROOT/dist-electron/"
echo ""
echo "💡 Windows 打包需要在 Windows 机器上运行："
echo "   1. 先运行 electron/scripts/build-backend.bat"
echo "   2. 再运行 cd electron && npm run build:win"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
