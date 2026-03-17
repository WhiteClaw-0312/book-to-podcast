#!/bin/bash
# 枕边书部署脚本

set -e

echo "🚀 开始部署枕边书..."

# 进入项目目录
cd /home/admin/.openclaw/workspace/book-to-podcast

# 构建前端 - 服务器版本（根路径）
echo "🔨 构建服务器版本前端..."
cd frontend
VITE_BASE_PATH=/ npm run build

# 部署前端到服务器
echo "📦 部署前端到服务器..."
sudo rm -rf /var/www/zhenbianshu/*
sudo cp -r dist/* /var/www/zhenbianshu/
sudo chown -R www-data:www-data /var/www/zhenbianshu

# 构建 GitHub Pages 版本（子路径）
echo "🔨 构建 GitHub Pages 版本前端..."
npm run build

# 提交到 GitHub（自动部署到 GitHub Pages）
echo "📤 提交到 GitHub Pages..."
cd ..
git add -A
git commit -m "deploy: 更新前端" || true
git push origin whiteclaw_0314

# 重启后端服务（使用 systemd）
echo "🔄 重启后端服务..."
sudo systemctl restart book2podcast

# 检查状态
echo "✅ 检查服务状态..."
sleep 3
sudo systemctl status book2podcast --no-pager
curl -s http://localhost/health

echo ""
echo "🎉 部署完成！"
echo "服务器版本: http://139.196.211.206"
echo "GitHub Pages: https://whiteclaw-0312.github.io/book-to-podcast/"