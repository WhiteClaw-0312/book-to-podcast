#!/bin/bash
# 枕边书部署脚本

set -e

echo "🚀 开始部署枕边书..."

# 进入项目目录
cd /home/admin/.openclaw/workspace/book-to-podcast

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull origin whiteclaw_0314

# 构建前端
echo "🔨 构建前端..."
cd frontend
VITE_BASE_PATH=/ npm run build

# 部署前端
echo "📦 部署前端..."
sudo rm -rf /var/www/zhenbianshu/*
sudo cp -r dist/* /var/www/zhenbianshu/
sudo chown -R www-data:www-data /var/www/zhenbianshu

# 重启后端
echo "🔄 重启后端..."
sudo systemctl restart book2podcast

# 检查状态
echo "✅ 检查服务状态..."
sudo systemctl status book2podcast --no-pager | head -10
curl -s http://139.196.211.206/health

echo ""
echo "🎉 部署完成！"
echo "HTTP:  http://139.196.211.206"
echo "HTTPS: https://139.196.211.206 (需要接受证书)"