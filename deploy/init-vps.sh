#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Social Manager - VPS Init Script
#  One-time setup on a fresh Ubuntu 22.04+ VPS
#
#  Usage:
#    1. SSH to VPS: ssh root@your-vps-ip
#    2. Run: curl -sSL <raw-github-url> | bash
#       OR: scp this file to VPS, then: bash init-vps.sh
#
#  Prerequisites:
#    - Ubuntu 22.04 or newer
#    - Root or sudo access
#    - Domain pointed to this VPS IP (DNS A record)
#      e.g. *.sm.mayrichbe.cam → VPS_IP
#           sm.mayrichbe.cam   → VPS_IP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

# ─── Configuration ───
DOMAIN="${SM_DOMAIN:-sm.mayrichbe.cam}"
GIT_REPO="${SM_GIT_REPO:-https://github.com/randolphijames-dot/mayrichbe-manager.git}"
INSTALL_DIR="/opt/social-manager"

echo "================================================"
echo "  Social Manager - VPS Initialization"
echo "  Domain: $DOMAIN"
echo "================================================"
echo ""

# ─── 0. Check if running as root ───
if [ "$(id -u)" -ne 0 ]; then
    echo "Please run as root: sudo bash init-vps.sh"
    exit 1
fi

# ─── 1. System update ───
echo "--- Step 1: System update ---"
apt-get update
apt-get upgrade -y
echo ""

# ─── 2. Install Docker ───
echo "--- Step 2: Install Docker ---"
if command -v docker &>/dev/null; then
    echo "Docker already installed: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker installed: $(docker --version)"
fi
echo ""

# ─── 3. Install Docker Compose plugin ───
echo "--- Step 3: Docker Compose ---"
if docker compose version &>/dev/null; then
    echo "Docker Compose already installed: $(docker compose version)"
else
    apt-get install -y docker-compose-plugin
    echo "Docker Compose installed: $(docker compose version)"
fi
echo ""

# ─── 4. Install Certbot ───
echo "--- Step 4: Install Certbot ---"
if command -v certbot &>/dev/null; then
    echo "Certbot already installed: $(certbot --version)"
else
    apt-get install -y certbot
    echo "Certbot installed: $(certbot --version)"
fi
echo ""

# ─── 5. Install Git ───
echo "--- Step 5: Install Git ---"
if command -v git &>/dev/null; then
    echo "Git already installed: $(git --version)"
else
    apt-get install -y git
    echo "Git installed: $(git --version)"
fi
echo ""

# ─── 6. Clone project ───
echo "--- Step 6: Clone project ---"
if [ -d "$INSTALL_DIR" ]; then
    echo "Project already exists at $INSTALL_DIR, pulling latest..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    git clone "$GIT_REPO" "$INSTALL_DIR"
    echo "Cloned to $INSTALL_DIR"
fi
echo ""

# ─── 7. Create data directory ───
echo "--- Step 7: Create data directories ---"
mkdir -p /data/sm
mkdir -p /data/sm-backups
mkdir -p /var/www/certbot
echo "Created /data/sm and /data/sm-backups"
echo ""

# ─── 8. SSL Certificate ───
# (Docker image will be built by docker compose when first user is added)
echo "--- Step 9: SSL Certificate ---"
echo ""
echo "IMPORTANT: Before requesting SSL, make sure DNS is configured:"
echo "  A record: *.${DOMAIN} → $(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_VPS_IP')"
echo "  A record: ${DOMAIN}   → $(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_VPS_IP')"
echo ""
echo "To request a wildcard SSL certificate, run:"
echo ""
echo "  certbot certonly --manual --preferred-challenges dns \\"
echo "    -d '${DOMAIN}' -d '*.${DOMAIN}'"
echo ""
echo "  (Certbot will ask you to create a DNS TXT record for verification)"
echo ""
echo "After certificate is obtained, it will be at:"
echo "  /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
echo "  /etc/letsencrypt/live/${DOMAIN}/privkey.pem"
echo ""

# ─── 10. Setup crontab for backup ───
echo "--- Step 10: Setup backup crontab ---"
CRON_JOB="0 3 * * * $INSTALL_DIR/deploy/backup.sh >> /var/log/sm-backup.log 2>&1"
if crontab -l 2>/dev/null | grep -q "sm-backup"; then
    echo "Backup cron already configured"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Backup cron added: daily at 03:00"
fi
echo ""

# ─── 11. Setup certbot auto-renewal ───
echo "--- Step 11: Certbot auto-renewal ---"
RENEW_JOB="0 3 * * 0 certbot renew --quiet && docker exec sm-nginx nginx -s reload"
if crontab -l 2>/dev/null | grep -q "certbot renew"; then
    echo "Certbot renewal cron already configured"
else
    (crontab -l 2>/dev/null; echo "$RENEW_JOB") | crontab -
    echo "SSL renewal cron added: weekly on Sunday 03:00"
fi
echo ""

# ─── 12. Firewall ───
echo "--- Step 12: Configure firewall ---"
if command -v ufw &>/dev/null; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    echo "UFW enabled: ports 22, 80, 443 open"
else
    echo "UFW not installed, skipping firewall setup"
fi
echo ""

# ─── Done ───
echo "================================================"
echo "  VPS Initialization Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Configure DNS (A records for ${DOMAIN} and *.${DOMAIN})"
echo "  2. Request SSL certificate (see Step 9 output above)"
echo "  3. Update domain in Nginx config:"
echo "     - Edit $INSTALL_DIR/deploy/nginx-multi.conf"
echo "     - Replace 'sm.mayrichbe.cam' with '${DOMAIN}'"
echo "  4. Copy .env.multi.example to .env.multi and configure"
echo "  5. Add your first user:"
echo "     cd $INSTALL_DIR/deploy"
echo "     ./manage-users.sh add user01"
echo "  6. Start Nginx:"
echo "     docker compose -f docker-compose.multi.yml --env-file .env.multi up -d nginx"
echo ""
echo "================================================"
