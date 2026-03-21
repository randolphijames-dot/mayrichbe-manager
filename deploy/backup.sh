#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Social Manager - Daily Backup
#  备份内容: 每个用户的 db + sessions
#  保留策略: 最近 7 天
#  不备份:   uploads（太大，单独处理）
#
#  Crontab 设置:
#    crontab -e
#    0 3 * * * /path/to/deploy/backup.sh >> /var/log/sm-backup.log 2>&1
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

DATA_ROOT="/data/sm"
BACKUP_ROOT="/data/sm-backups"
DATE=$(date '+%Y%m%d')
KEEP_DAYS=7

echo "================================================"
echo "  Social Manager Backup - $DATE"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "================================================"

# 确保备份目录存在
mkdir -p "$BACKUP_ROOT"

# 遍历每个用户目录
for user_dir in "$DATA_ROOT"/*/; do
    USERNAME=$(basename "$user_dir")

    # 跳过非用户目录
    if [ ! -d "$user_dir/data" ]; then
        continue
    fi

    echo ""
    echo "--- Backing up: $USERNAME ---"

    # SQLite WAL checkpoint: flush WAL to main db for consistent backup
    DB_FILE="$user_dir/data/social_manager.db"
    if [ -f "$DB_FILE" ] && command -v sqlite3 &>/dev/null; then
        sqlite3 "$DB_FILE" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
    fi

    BACKUP_DIR="$BACKUP_ROOT/$USERNAME"
    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="$BACKUP_DIR/${USERNAME}_${DATE}.tar.gz"

    # 打包 data(db) + sessions，排除 uploads
    tar -czf "$BACKUP_FILE" \
        -C "$DATA_ROOT" \
        "$USERNAME/data" \
        "$USERNAME/sessions" \
        2>/dev/null || true

    SIZE=$(du -sh "$BACKUP_FILE" 2>/dev/null | cut -f1)
    echo "  Created: $BACKUP_FILE ($SIZE)"
done

# 清理超过 KEEP_DAYS 天的旧备份
echo ""
echo "--- Cleaning backups older than $KEEP_DAYS days ---"
find "$BACKUP_ROOT" -name "*.tar.gz" -mtime +$KEEP_DAYS -delete -print 2>/dev/null | while read -r f; do
    echo "  Deleted: $f"
done

# 统计备份占用空间
echo ""
TOTAL=$(du -sh "$BACKUP_ROOT" 2>/dev/null | cut -f1)
echo "Total backup size: $TOTAL"
echo ""
echo "Done at $(date '+%Y-%m-%d %H:%M:%S')"
