#!/bin/bash
# 自动更新前端和后端（crontab 定时任务）

cd /home/admin/.openclaw/workspace/book-to-podcast

# 拉取代码
git pull origin whiteclaw_0314 > /dev/null 2>&1

# 检查是否有更新
if git diff --quiet HEAD@{1} HEAD 2>/dev/null; then
    echo "No updates"
    exit 0
fi

echo "Updates detected, deploying..."

# 构建前端
cd frontend
VITE_BASE_PATH=/ npm run build > /dev/null 2>&1

# 部署
sudo rm -rf /var/www/zhenbianshu/*
sudo cp -r dist/* /var/www/zhenbianshu/
sudo chown -R www-data:www-data /var/www/zhenbianshu

# 重启后端
sudo systemctl restart book2podcast

echo "Deployed at $(date)" >> /var/log/book2podcast/deploy.log