#!/bin/bash
# 部署章节管理功能更新

set -e

echo "🚀 开始部署章节管理功能..."

# 进入项目目录
cd /home/admin/.openclaw/workspace/book-to-podcast

# 1. 运行数据库迁移
echo "📦 运行数据库迁移..."
python3 scripts/migrate_add_chapter_fields.py

# 2. 重启后端服务
echo "🔄 重启后端服务..."
sudo systemctl restart book2podcast

# 等待服务启动
sleep 3

# 检查服务状态
if sudo systemctl is-active --quiet book2podcast; then
    echo "✅ 后端服务已启动"
else
    echo "❌ 后端服务启动失败"
    sudo systemctl status book2podcast
    exit 1
fi

# 3. 构建前端
echo "🔨 构建前端..."
cd frontend
npm run build

# 4. 部署到服务器静态目录
echo "📤 部署前端到服务器..."
sudo cp -r dist/* /var/www/book2podcast/

# 5. 同步到 GitHub Pages（如果配置了）
if [ -d "../gh-pages" ]; then
    echo "📤 同步到 GitHub Pages..."
    cd ../gh-pages
    cp -r ../book-to-podcast/frontend/dist/* .
    git add -A
    git commit -m "update: 章节管理功能" || true
    git push origin gh-pages --force
fi

echo "✅ 部署完成！"
echo ""
echo "访问地址："
echo "  - 服务器: http://139.196.211.206"
echo "  - GitHub Pages: https://whiteclaw-0312.github.io/book-to-podcast/"