#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  Mayrichbe Manager - 多账号管理系统"
echo "========================================"
echo ""
echo "正在启动后端服务..."
echo ""

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未检测到 Python 3，请先安装"
    echo "安装命令: brew install python@3.11"
    read -p "按任意键退出..."
    exit 1
fi

cd backend

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "[首次运行] 正在创建虚拟环境并安装依赖..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    echo ""
    echo "依赖安装完成！"
    echo ""
else
    source .venv/bin/activate
fi

# 启动后端
echo "启动后端服务器..."
echo "访问地址: http://localhost:8000"
echo ""
echo "提示: 按 Ctrl+C 停止服务"
echo ""

# 2秒后打开浏览器
(sleep 2 && open http://localhost:8000) &

# 启动 FastAPI
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
