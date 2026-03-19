#!/bin/bash
# 一键启动脚本（Mac/Linux，支持局域网模式）

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# 获取本机局域网 IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "========================================"
echo "  Social Manager 启动"
echo "========================================"

# 检查 Redis
if ! redis-cli ping &>/dev/null; then
    echo "⚙️  启动 Redis..."
    brew services start redis 2>/dev/null || (echo "❌ Redis 未安装: brew install redis" && exit 1)
    sleep 1
fi
echo "✅ Redis 运行中"

# 虚拟环境
VENV="$BACKEND_DIR/.venv"
if [ ! -d "$VENV" ]; then
    echo "📦 创建 Python 虚拟环境..."
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

# 安装后端依赖
echo "📦 检查后端依赖..."
pip install -q -r "$BACKEND_DIR/requirements.txt" --disable-pip-version-check

# 创建 .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "⚠️  已创建 .env，请按需修改配置"
fi

# 数据库迁移
cd "$BACKEND_DIR"
python -c "from app.db.init_db import init_db; init_db()" 2>/dev/null

# 启动后端（0.0.0.0 支持局域网访问）
echo "🚀 启动后端 API (端口 8000)..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# 启动 Celery Worker
echo "⚙️  启动 Celery Worker..."
celery -A app.tasks.celery_app worker -Q default,youtube,instagram,health -l warning -c 2 &
CELERY_PID=$!

# 启动 Celery Beat
celery -A app.tasks.celery_app beat -l warning &
BEAT_PID=$!

# 前端
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    echo "📦 安装前端依赖（首次需要几分钟）..."
    npm install --silent
fi

# 前端用 --host 0.0.0.0 支持局域网访问
echo "🌐 启动前端 (端口 5173)..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

sleep 2
echo ""
echo "========================================"
echo "  ✅ 所有服务已启动！"
echo ""
echo "  本机访问：  http://localhost:5173"
echo "  局域网访问：http://$LOCAL_IP:5173"
echo ""
echo "  API 文档：  http://localhost:8000/docs"
echo "========================================"
echo ""
echo "按 Ctrl+C 停止所有服务"

trap "echo '停止服务...'; kill $BACKEND_PID $CELERY_PID $BEAT_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
