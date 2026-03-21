#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Social Manager - 一键更新所有用户容器
#  流程: git pull → docker build → 重启所有容器
#
#  使用场景:
#    AK 在 Mac 上改完代码 → git push
#    SSH 到 VPS → cd /path/to/social-manager/deploy
#    → ./update-all.sh
#    → 所有用户无感更新
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo "  Social Manager - Update All Containers"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# 1. 拉取最新代码
echo ""
echo "--- Step 1: git pull ---"
cd "$ROOT_DIR"
git pull origin main
echo ""

# 2. 重新构建镜像
echo "--- Step 2: docker build ---"
cd "$SCRIPT_DIR"
docker compose -f docker-compose.multi.yml --env-file .env.multi build
echo ""

# 3. 滚动重启所有用户容器（非 Nginx）
echo "--- Step 3: Restarting user containers ---"
# 获取所有 sm- 开头的 service（排除 nginx）
SERVICES=$(docker compose -f docker-compose.multi.yml config --services 2>/dev/null | grep '^sm-' || true)

if [ -z "$SERVICES" ]; then
    echo "No user containers found."
    exit 0
fi

for svc in $SERVICES; do
    echo "  Restarting $svc..."
    docker compose -f docker-compose.multi.yml --env-file .env.multi up -d --no-deps "$svc"
done
echo ""

# 4. 重载 Nginx（不重启，避免断连）
echo "--- Step 4: Reload Nginx ---"
docker compose -f docker-compose.multi.yml exec nginx nginx -s reload 2>/dev/null || \
    echo "  Nginx reload skipped (not running or not applicable)"
echo ""

# 5. 清理旧镜像
echo "--- Step 5: Cleanup old images ---"
docker image prune -f
echo ""

# 6. 显示状态
echo "================================================"
echo "  Update complete! Container status:"
echo "================================================"
docker ps -a --filter "name=sm-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Done at $(date '+%Y-%m-%d %H:%M:%S')"
