#!/bin/bash

echo "=== wangye-ge 强制升级中 ==="

# 强制重置本地修改，确保能拉取最新代码
git fetch --all
git reset --hard origin/main

# 重新安装依赖并构建
echo "更新后端依赖..."
cd backend
source venv/bin/activate
pip install -r requirements.txt
cd ..

echo "更新前端并重新构建..."
cd frontend
npm install
npm run build
cd ..

# 重启服务
echo "重启 PM2 服务..."
pm2 restart wangye-ge-backend

echo "升级完成！"
