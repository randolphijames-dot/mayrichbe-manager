#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Social Manager - 多租户用户管理
#  用法:
#    ./manage-users.sh add user01      创建用户
#    ./manage-users.sh remove user01   停止容器（数据保留）
#    ./manage-users.sh list            列出所有用户
#    ./manage-users.sh status          查看容器运行状态
#    ./manage-users.sh restart user01  重启指定用户
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.multi.yml"
ENV_FILE="$SCRIPT_DIR/.env.multi"
TEMPLATE="$SCRIPT_DIR/nginx-user.conf.template"
CONF_DIR="$SCRIPT_DIR/conf.d"
DATA_ROOT="/data/sm"

# ─── 颜色输出 ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ─── 用户名校验 ───
validate_username() {
    local name="$1"
    if [[ ! "$name" =~ ^[a-z][a-z0-9]{1,14}$ ]]; then
        error "Username must: start with lowercase letter, 2-15 chars, only a-z and 0-9"
        exit 1
    fi

    # 保留名检查
    local RESERVED="nginx net admin root system"
    for r in $RESERVED; do
        if [ "$name" = "$r" ]; then
            error "Username '$name' is reserved and cannot be used"
            exit 1
        fi
    done
}

# ─── ADD: 创建用户 ───
cmd_add() {
    local USERNAME="$1"
    if [ -z "$USERNAME" ]; then
        error "Usage: $0 add <username>"
        exit 1
    fi
    validate_username "$USERNAME"

    local UPPER_NAME
    UPPER_NAME=$(echo "$USERNAME" | tr '[:lower:]' '[:upper:]')

    echo "================================================"
    echo "  Adding user: $USERNAME"
    echo "================================================"

    # 1. 检查是否已存在
    if grep -q "sm-${USERNAME}:" "$COMPOSE_FILE" 2>/dev/null; then
        error "User '$USERNAME' already exists in compose file"
        exit 1
    fi

    # 2. 创建数据目录
    echo ""
    echo "--- Creating data directories ---"
    sudo mkdir -p "$DATA_ROOT/$USERNAME/data"
    sudo mkdir -p "$DATA_ROOT/$USERNAME/uploads"
    sudo mkdir -p "$DATA_ROOT/$USERNAME/sessions"
    sudo chown -R 1000:1000 "$DATA_ROOT/$USERNAME"
    info "Data dirs created: $DATA_ROOT/$USERNAME/"

    # 3. 生成密码和 SECRET_KEY
    echo ""
    echo "--- Generating credentials ---"
    local SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
    local ACCESS_PASS
    ACCESS_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))" 2>/dev/null || openssl rand -base64 16)

    # 追加到 .env.multi
    if [ ! -f "$ENV_FILE" ]; then
        cp "$SCRIPT_DIR/.env.multi.example" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
    fi

    # 检查是否已有此用户的环境变量
    if grep -q "${UPPER_NAME}_SECRET_KEY" "$ENV_FILE"; then
        warn "Env vars for $USERNAME already exist, skipping"
    else
        cat >> "$ENV_FILE" << EOF

# --- $USERNAME ---
${UPPER_NAME}_SECRET_KEY=$SECRET_KEY
${UPPER_NAME}_ACCESS_PASSWORD=$ACCESS_PASS
EOF
        info "Credentials added to .env.multi"
    fi

    # 4. 追加 service 到 docker-compose.multi.yml
    echo ""
    echo "--- Adding service to compose file ---"

    # 在 MARKER 注释前插入新 service
    local SERVICE_BLOCK
    SERVICE_BLOCK=$(cat << SERVICEEOF

  # --- ${USERNAME} (auto-added) ---
  sm-${USERNAME}:
    build:
      context: ..
      dockerfile: Dockerfile
    container_name: sm-${USERNAME}
    restart: unless-stopped
    environment:
      - TZ=Asia/Tokyo
      - PYTHONUNBUFFERED=1
      - SECRET_KEY=\${${UPPER_NAME}_SECRET_KEY:?Set ${UPPER_NAME}_SECRET_KEY in .env.multi}
      - ACCESS_PASSWORD=\${${UPPER_NAME}_ACCESS_PASSWORD:-}
      - DATABASE_URL=sqlite:////app/data/social_manager.db
      - UPLOAD_DIR=/app/uploads
    volumes:
      - ${DATA_ROOT}/${USERNAME}/data:/app/data
      - ${DATA_ROOT}/${USERNAME}/uploads:/app/uploads
      - ${DATA_ROOT}/${USERNAME}/sessions:/app/instagrapi_sessions
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - sm-net
SERVICEEOF
    )

    # 使用 Python 插入（避免 sed 跨平台问题）
    python3 << PYEOF
import sys

marker = "  # MARKER:NEW_USER_ABOVE"
service_block = """$SERVICE_BLOCK"""

with open("$COMPOSE_FILE", "r") as f:
    content = f.read()

if marker in content:
    content = content.replace(marker, service_block + "\n" + marker)
else:
    print("WARNING: Marker not found, appending before networks section")
    content = content.replace("networks:", service_block + "\n\nnetworks:")

with open("$COMPOSE_FILE", "w") as f:
    f.write(content)

print("OK")
PYEOF
    info "Service 'sm-${USERNAME}' added to compose file"

    # 5. 生成 Nginx 配置
    echo ""
    echo "--- Generating Nginx config ---"
    mkdir -p "$CONF_DIR"
    sed "s/__USERNAME__/${USERNAME}/g" "$TEMPLATE" > "$CONF_DIR/${USERNAME}.conf"
    info "Nginx config: $CONF_DIR/${USERNAME}.conf"

    # 6. 启动容器
    echo ""
    echo "--- Starting container ---"
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.multi.yml --env-file .env.multi up -d --build "sm-${USERNAME}"

    # 7. 重载 Nginx
    docker compose -f docker-compose.multi.yml exec nginx nginx -s reload 2>/dev/null || \
        docker compose -f docker-compose.multi.yml restart nginx

    echo ""
    echo "================================================"
    info "User '$USERNAME' created successfully!"
    echo ""
    echo "  URL:      https://${USERNAME}.sm.mayrichbe.cam"
    echo "  Password: $ACCESS_PASS"
    echo ""
    echo "  IMPORTANT: Save the password above!"
    echo "  It is also stored in: $ENV_FILE"
    echo "================================================"
}

# ─── REMOVE: 停止用户容器（保留数据） ───
cmd_remove() {
    local USERNAME="$1"
    if [ -z "$USERNAME" ]; then
        error "Usage: $0 remove <username>"
        exit 1
    fi

    echo "Stopping container sm-${USERNAME}..."
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.multi.yml stop "sm-${USERNAME}" 2>/dev/null || true

    warn "Container stopped. Data preserved at: $DATA_ROOT/$USERNAME/"
    echo "  To permanently delete data: sudo rm -rf $DATA_ROOT/$USERNAME/"
    echo "  To remove from compose: manually delete the sm-${USERNAME} section"
}

# ─── LIST: 列出所有用户 ───
cmd_list() {
    echo "================================================"
    echo "  Registered users (in compose file)"
    echo "================================================"

    grep -oE 'container_name: sm-[a-z0-9]+' "$COMPOSE_FILE" 2>/dev/null | \
        sed 's/container_name: sm-//' | \
        grep -v '^nginx$' | while read -r user; do
        echo "  - $user"
    done

    echo ""
    echo "Data directories:"
    ls -d "$DATA_ROOT"/*/ 2>/dev/null | while read -r dir; do
        local name
        name=$(basename "$dir")
        local size
        size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        echo "  - $name ($size)"
    done
}

# ─── STATUS: 查看容器运行状态 ───
cmd_status() {
    echo "================================================"
    echo "  Container status"
    echo "================================================"
    docker ps -a --filter "name=sm-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
}

# ─── RESTART: 重启指定用户 ───
cmd_restart() {
    local USERNAME="$1"
    if [ -z "$USERNAME" ]; then
        error "Usage: $0 restart <username>"
        exit 1
    fi

    echo "Restarting sm-${USERNAME}..."
    cd "$SCRIPT_DIR"
    docker compose -f docker-compose.multi.yml --env-file .env.multi restart "sm-${USERNAME}"
    info "sm-${USERNAME} restarted"
}

# ─── 主入口 ───
case "${1:-}" in
    add)     cmd_add "$2" ;;
    remove)  cmd_remove "$2" ;;
    list)    cmd_list ;;
    status)  cmd_status ;;
    restart) cmd_restart "$2" ;;
    *)
        echo "Usage: $0 {add|remove|list|status|restart} [username]"
        echo ""
        echo "Commands:"
        echo "  add <username>      Create user (dirs + credentials + container)"
        echo "  remove <username>   Stop container (data preserved)"
        echo "  list                List all registered users"
        echo "  status              Show container status"
        echo "  restart <username>  Restart user container"
        exit 1
        ;;
esac
