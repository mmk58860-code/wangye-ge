#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== wangye-ge Bittensor Dashboard 安装向导 ==="
echo "此脚本只用于新机器首次安装。已安装机器升级请运行: bash scripts/upgrade.sh"

if [ -f "$PROJECT_DIR/data.db" ]; then
  if (cd "$PROJECT_DIR" && python3 - <<'PY'
import sqlite3
import sys

try:
    conn = sqlite3.connect("data.db")
    row = conn.execute(
        "select value from settings where key = 'install_completed'"
    ).fetchone()
    conn.close()
except sqlite3.Error:
    sys.exit(1)

sys.exit(0 if row and row[0] == "true" else 1)
PY
  )
  then
    echo "检测到本项目已经完成安装。"
    echo "后续升级请运行: bash scripts/upgrade.sh"
    echo "如需重新安装，请先手动备份并删除 data.db。"
    exit 1
  fi
fi

if [ -n "${VIRTUAL_ENV:-}" ]; then
  echo "检测到当前处于 Python 虚拟环境，安装向导将退出该环境后继续。"
  deactivate 2>/dev/null || true
fi

read -p "请输入网页访问端口 (默认 80): " WEB_PORT
WEB_PORT=${WEB_PORT:-80}

while true; do
  read -p "请输入后端服务端口 (默认 18000): " BACKEND_PORT
  BACKEND_PORT=${BACKEND_PORT:-18000}

  if [ "$WEB_PORT" = "$BACKEND_PORT" ]; then
    echo "后端端口不能和网页访问端口相同，请重新输入。"
  else
    break
  fi
done

read -p "请输入网页管理员账号 (默认 admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

while true; do
  read -s -p "请输入网页管理员密码: " ADMIN_PASS
  echo ""
  read -s -p "请再次输入网页管理员密码: " ADMIN_PASS_CONFIRM
  echo ""

  if [ -z "$ADMIN_PASS" ]; then
    echo "密码不能为空，请重新输入。"
  elif [ "$ADMIN_PASS" != "$ADMIN_PASS_CONFIRM" ]; then
    echo "两次密码不一致，请重新输入。"
  else
    break
  fi
done

echo "安装系统依赖..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nodejs git nginx

if ! command -v npm >/dev/null 2>&1; then
  sudo apt-get install -y npm
fi

for cmd in python3 node npm nginx git; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "依赖安装失败，未找到命令: $cmd"
    exit 1
  fi
done

echo "配置后端..."
cd "$PROJECT_DIR"
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt

ADMIN_USER="$ADMIN_USER" ADMIN_PASS="$ADMIN_PASS" WEB_PORT="$WEB_PORT" BACKEND_PORT="$BACKEND_PORT" python - <<'PY'
import os

from backend.database import init_db
from backend.security import configure_admin, mark_install_complete

init_db()
configure_admin(os.environ["ADMIN_USER"], os.environ["ADMIN_PASS"])
mark_install_complete(os.environ["WEB_PORT"], os.environ["BACKEND_PORT"])
PY

echo "配置前端..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build

echo "配置 PM2 后端服务..."
sudo npm install -g pm2
if ! command -v pm2 >/dev/null 2>&1; then
  echo "PM2 安装失败，请检查 npm 全局安装路径。"
  exit 1
fi
pm2 delete wangye-ge-backend 2>/dev/null || true
pm2 start "$PROJECT_DIR/backend/venv/bin/python" \
  --name wangye-ge-backend \
  --cwd "$PROJECT_DIR" \
  -- -m uvicorn backend.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
pm2 save

echo "配置 Nginx..."
sudo tee /etc/nginx/sites-available/wangye-ge >/dev/null <<EOF
server {
    listen $WEB_PORT;
    server_name _;

    root $PROJECT_DIR/frontend/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri /index.html;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/wangye-ge /etc/nginx/sites-enabled/wangye-ge
if [ "$WEB_PORT" = "80" ] && [ -e /etc/nginx/sites-enabled/default ]; then
  echo "关闭 Nginx 默认站点，避免占用 80 端口..."
  sudo rm -f /etc/nginx/sites-enabled/default
fi
sudo nginx -t
sudo systemctl reload nginx

if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow "$WEB_PORT"/tcp
fi

SERVER_IP=$(hostname -I | awk '{print $1}')

if [ ! -f "$PROJECT_DIR/frontend/build/index.html" ]; then
  echo "前端构建失败，未找到 $PROJECT_DIR/frontend/build/index.html"
  exit 1
fi

if ! curl -fsS "http://127.0.0.1:$WEB_PORT" >/dev/null; then
  echo "本机访问 http://127.0.0.1:$WEB_PORT 失败，请检查 Nginx 状态。"
  exit 1
fi

echo ""
echo "安装完成！"
echo "访问地址: http://$SERVER_IP:$WEB_PORT"
echo "管理员账号: $ADMIN_USER"
echo "后端内部端口: $BACKEND_PORT"
