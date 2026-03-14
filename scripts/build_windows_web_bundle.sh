#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT/dist-web-windows"
BUNDLE_DIR="$OUT_DIR/Mayrichbe-Manager-Web"
ZIP_FILE="$OUT_DIR/Mayrichbe-Manager-Web.zip"

echo "[1/4] 清理旧产物..."
rm -rf "$BUNDLE_DIR" "$ZIP_FILE"
mkdir -p "$BUNDLE_DIR"

echo "[2/4] 复制启动与说明文件..."
cp "$ROOT/START_WINDOWS.bat" "$BUNDLE_DIR/"
cp "$ROOT/CHECK_WINDOWS_WEB.bat" "$BUNDLE_DIR/"
cp "$ROOT/README_WINDOWS_WEB.md" "$BUNDLE_DIR/"
cp "$ROOT/ACCOUNT_IMPORT_TEMPLATE.csv" "$BUNDLE_DIR/"

echo "[3/4] 复制 backend（保留完整功能，排除运行时垃圾）..."
rsync -a \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude "dist" \
  --exclude "uploads" \
  --exclude "social_manager.db" \
  --exclude "debug_screens" \
  "$ROOT/backend/" "$BUNDLE_DIR/backend/"

mkdir -p "$BUNDLE_DIR/backend/uploads"

echo "[4/4] 生成 zip..."
(
  cd "$OUT_DIR"
  zip -rq "$(basename "$ZIP_FILE")" "$(basename "$BUNDLE_DIR")"
)

echo
echo "打包完成：$ZIP_FILE"
echo "可将该 zip 发送到 Windows 电脑，解压后双击 START_WINDOWS.bat。"
