#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

echo "=== wangye-ge 升级脚本 ==="
echo "此脚本用于已安装机器后续升级；新机器首次安装请运行: bash scripts/install.sh"

if [ ! -f data.db ]; then
  echo "未检测到安装数据。请先运行安装向导: bash scripts/install.sh"
  exit 1
fi

python3 - <<'PY'
import sqlite3
import sys

conn = sqlite3.connect("data.db")
try:
    row = conn.execute(
        "select value from settings where key = 'install_completed'"
    ).fetchone()
finally:
    conn.close()

if not row or row[0] != "true":
    print("项目尚未通过安装向导完成安装。请先运行: bash scripts/install.sh")
    sys.exit(1)
PY

echo "开始从 GitHub 拉取并升级..."

git fetch --all
git reset --hard origin/main

echo "更新后端依赖..."
source backend/venv/bin/activate
pip install -r backend/requirements.txt

echo "更新前端并重新构建..."
cd frontend
npm install
npm run build
cd ..

echo "重启 PM2 服务..."
pm2 restart wangye-ge-backend

echo "升级完成！"
