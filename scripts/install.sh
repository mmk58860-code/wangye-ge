#!/bin/bash

echo "=== wangye-ge Bittensor Dashboard 安装向导 ==="

# 1. 询问基本信息
read -p "请输入网页运行端口 (默认 8000): " PORT
PORT=${PORT:-8000}

read -p "请输入管理员账号: " ADMIN_USER
read -s -p "请输入管理员密码: " ADMIN_PASS
echo ""

# 2. 安装系统依赖
echo "安装系统依赖..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv nodejs npm git

# 3. 后端设置
echo "配置后端..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 初始化数据库
python3 -c "from database import init_db; init_db()"

# 保存初始设置
python3 -c "from database import SessionLocal; from models import Setting; db=SessionLocal(); db.add(Setting(key='admin_user', value='$ADMIN_USER')); db.add(Setting(key='admin_pass', value='$ADMIN_PASS')); db.commit(); db.close()"

cd ..

# 4. 前端设置
echo "配置前端..."
cd frontend
npm install
npm run build
cd ..

# 5. 使用 PM2 启动
echo "使用 PM2 启动服务..."
sudo npm install -g pm2
pm2 delete wangye-ge-backend 2>/dev/null
pm2 start "cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port $PORT" --name wangye-ge-backend

echo "安装完成！请访问 http://your-ip:$PORT"
