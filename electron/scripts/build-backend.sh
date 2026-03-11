#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# 用 PyInstaller 将 Python 后端打包成单一可执行文件
# 运行环境：Mac（生成 backend_mac），在 Win 机器上运行生成 backend_win.exe
# 用法：bash electron/scripts/build-backend.sh
# ─────────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/../.."
BACKEND="$ROOT/backend"
DIST_DIR="$ROOT/electron/backend-dist"

echo "🐍 安装 PyInstaller..."
cd "$BACKEND"
pip install pyinstaller --quiet

# 检测平台
if [[ "$OSTYPE" == "darwin"* ]]; then
  EXE_NAME="backend_mac"
else
  EXE_NAME="backend_win"
fi

echo "📦 打包 Python 后端..."
pyinstaller \
  --onefile \
  --name "$EXE_NAME" \
  --hidden-import "app.api.v1.endpoints.accounts" \
  --hidden-import "app.api.v1.endpoints.materials" \
  --hidden-import "app.api.v1.endpoints.tasks" \
  --hidden-import "app.api.v1.endpoints.logs" \
  --hidden-import "app.api.v1.endpoints.youtube" \
  --hidden-import "app.api.v1.endpoints.tools" \
  --hidden-import "app.api.v1.endpoints.profile" \
  --hidden-import "apscheduler.triggers.date" \
  --hidden-import "apscheduler.jobstores.sqlalchemy" \
  --hidden-import "apscheduler.executors.pool" \
  --hidden-import "instagrapi" \
  --hidden-import "playwright" \
  --collect-all "instagrapi" \
  --noconfirm \
  --distpath "$DIST_DIR" \
  run_server.py   # 入口文件

echo "✅ 后端可执行文件已生成: $DIST_DIR/$EXE_NAME"
