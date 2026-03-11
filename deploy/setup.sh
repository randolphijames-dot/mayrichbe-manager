#!/bin/bash
# 专用主机一键部署脚本（Mac / Windows WSL / Linux）
# 使用 Cloudflare Tunnel 提供公网访问

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "================================================"
echo "  Social Manager 生产环境部署"
echo "================================================"

# ─── 1. 检查 Docker ───
if ! command -v docker &>/dev/null; then
    echo "❌ 需要安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo "✅ Docker 已安装"

# ─── 2. 生成随机 SECRET_KEY ───
if [ ! -f "$SCRIPT_DIR/.env.prod" ]; then
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
    cat > "$SCRIPT_DIR/.env.prod" << EOF
# 自动生成的生产环境配置
SECRET_KEY=$SECRET
ACCESS_PASSWORD=

# 指纹浏览器（运行在同一台机器上，用 host.docker.internal 访问宿主机）
ADSPOWER_API_URL=http://host.docker.internal:50325
BITBROWSER_API_URL=http://host.docker.internal:54345

# 通知（可选）
LINE_NOTIFY_TOKEN=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# YouTube OAuth（可选）
YT_CLIENT_ID=
YT_CLIENT_SECRET=
EOF
    echo "✅ 已生成 .env.prod（SECRET_KEY 已随机生成）"
fi

# ─── 3. 生成访问密码文件（htpasswd）───
if [ ! -f "$SCRIPT_DIR/htpasswd" ]; then
    echo ""
    read -p "设置访问密码（留空=不设密码）: " ACCESS_PASS
    if [ -n "$ACCESS_PASS" ]; then
        if command -v htpasswd &>/dev/null; then
            htpasswd -bc "$SCRIPT_DIR/htpasswd" admin "$ACCESS_PASS"
        else
            # 用 Python 生成 bcrypt 哈希
            python3 -c "
import crypt, sys
pw = sys.argv[1]
hashed = crypt.crypt(pw, crypt.mksalt(crypt.METHOD_SHA512))
print(f'admin:{hashed}')
" "$ACCESS_PASS" > "$SCRIPT_DIR/htpasswd" 2>/dev/null || touch "$SCRIPT_DIR/htpasswd"
        fi
        # 同时在 nginx.conf 里启用密码
        sed -i '' 's/# auth_basic /auth_basic /g' "$SCRIPT_DIR/nginx.conf" 2>/dev/null || \
        sed -i 's/# auth_basic /auth_basic /g' "$SCRIPT_DIR/nginx.conf"
        echo "✅ 访问密码已设置（用户名：admin）"
    else
        touch "$SCRIPT_DIR/htpasswd"
        echo "⚠️  未设置访问密码，任何人都可以访问"
    fi
fi

# ─── 4. 构建前端 ───
echo ""
echo "📦 构建前端..."
cd "$ROOT_DIR/frontend"
npm install --silent
npm run build

# ─── 5. 启动 Docker 服务 ───
echo ""
echo "🚀 启动所有服务..."
cd "$SCRIPT_DIR"
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

echo ""
echo "✅ 服务已启动"
echo "   本机访问：http://localhost"
echo ""

# ─── 6. Cloudflare Tunnel（可选）───
echo "================================================"
echo "  下一步：用 Cloudflare Tunnel 实现公网访问"
echo "================================================"
echo ""
echo "步骤："
echo "1. 安装 cloudflared:"
echo "   Mac:     brew install cloudflared"
echo "   Windows: winget install Cloudflare.cloudflared"
echo "   Linux:   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb"
echo ""
echo "2. 临时隧道（无需账号，有效期24小时）:"
echo "   cloudflared tunnel --url http://localhost:80"
echo "   → 会输出一个 https://xxxxx.trycloudflare.com 的链接，发给团队即可"
echo ""
echo "3. 永久隧道（需要 Cloudflare 免费账号）:"
echo "   cloudflared login"
echo "   cloudflared tunnel create social-manager"
echo "   cloudflared tunnel route dns social-manager your-domain.com"
echo "   cloudflared tunnel run social-manager"
echo ""
echo "================================================"
