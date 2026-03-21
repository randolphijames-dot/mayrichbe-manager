#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT/dist-web-windows"
BUNDLE_DIR="$OUT_DIR/Mayrichbe-Manager-Web"
ZIP_FILE="$OUT_DIR/Mayrichbe-Manager-Web.zip"

echo "[1/5] 清理旧产物..."
rm -rf "$BUNDLE_DIR" "$ZIP_FILE"
mkdir -p "$BUNDLE_DIR"

echo "[2/5] 复制启动与说明文件..."
cp "$ROOT/START_WINDOWS_20260321_v2.bat" "$BUNDLE_DIR/START_WINDOWS.bat"
cp "$ROOT/CHECK_WINDOWS_WEB.bat" "$BUNDLE_DIR/"
cp "$ROOT/TEST_CLICK_ME.bat" "$BUNDLE_DIR/"
cp "$ROOT/README_WINDOWS_WEB.md" "$BUNDLE_DIR/"
cp "$ROOT/ACCOUNT_IMPORT_TEMPLATE.csv" "$BUNDLE_DIR/"

echo "[2.5/5] 转换 bat 文件为 CRLF（Windows 换行符）..."
for batfile in "$BUNDLE_DIR"/*.bat; do
  perl -pi -e 's/\r?\n/\r\n/' "$batfile"
done
echo "   bat 文件已转换为 CRLF"

echo "[3/5] 复制 backend（保留完整功能，排除运行时垃圾）..."
rsync -a \
  --exclude ".venv" \
  --exclude "venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude "dist" \
  --exclude "dist-*" \
  --exclude "build" \
  --exclude "uploads" \
  --exclude "social_manager.db" \
  --exclude "debug_screens" \
  --exclude "backend_mac" \
  --exclude "backend_win" \
  --exclude "*.spec" \
  --exclude "debug_*" \
  --exclude "instagrapi_sessions" \
  --exclude "*.log" \
  --exclude ".DS_Store" \
  "$ROOT/backend/" "$BUNDLE_DIR/backend/"

mkdir -p "$BUNDLE_DIR/backend/uploads"

echo "[4/5] 验证关键文件..."
missing=0
for f in backend/app/main.py backend/static/index.html backend/run_server.py backend/requirements.txt; do
  if [ ! -f "$BUNDLE_DIR/$f" ]; then
    echo "   [FAIL] 缺失: $f"
    missing=1
  fi
done
for f in START_WINDOWS.bat CHECK_WINDOWS_WEB.bat; do
  if [ ! -f "$BUNDLE_DIR/$f" ]; then
    echo "   [FAIL] 缺失: $f"
    missing=1
  fi
done
if [ "$missing" -eq 1 ]; then
  echo "   打包中止：关键文件缺失"
  exit 1
fi
echo "   所有关键文件已确认"

echo "[5/5] 生成 zip..."
(
  cd "$OUT_DIR"
  zip -rq "$(basename "$ZIP_FILE")" "$(basename "$BUNDLE_DIR")"
)

SIZE=$(du -h "$ZIP_FILE" | cut -f1)
echo
echo "打包完成：$ZIP_FILE ($SIZE)"
echo "可将该 zip 发送到 Windows 电脑，解压后双击 START_WINDOWS.bat。"
