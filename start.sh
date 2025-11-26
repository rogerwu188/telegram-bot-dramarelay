#!/bin/bash

# 安装 Playwright 浏览器（如果尚未安装）
echo "检查 Playwright 浏览器..."
if [ ! -d "/root/.cache/ms-playwright/chromium-1091" ]; then
    echo "安装 Playwright Chromium 浏览器..."
    playwright install chromium
    playwright install-deps chromium
else
    echo "Playwright 浏览器已安装"
fi

# 启动 Bot 在后台
python3 bot.py &

# 启动 API 服务器在前台
python3 api_server.py
