#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== wangye-ge Bittensor Dashboard 安装向导 ==="

read -p "请输入网页访问端口 (默认 80): " WEB_PORT
WEB_PORT=${WEB_PORT:-80}

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

BACKEND_PORT=18000
if [ "$WEB_PORT" = "$BACKEND_PORT" ]; then
  BACKEND_PORT=18001
fi

echo "安装系统依赖..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nodejs npm git nginx

echo "配置后端..."
cd "$PROJECT_DIR"
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt

ADMIN_USER="$ADMIN_USER" ADMIN_PASS="$ADMIN_PASS" python - <<'PY'
import os

from backend.database import init_db
from backend.security import configure_admin

init_db()
configure_admin(os.environ["ADMIN_USER"], os.environ["ADMIN_PASS"])
PY

echo "配置前端..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build

echo "配置 PM2 后端服务..."
sudo npm install -g pm2
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

echo ""
echo "安装完成！"
echo "访问地址: http://$SERVER_IP:$WEB_PORT"
echo "管理员账号: $ADMIN_USER"
echo "后端内部端口: $BACKEND_PORT"
