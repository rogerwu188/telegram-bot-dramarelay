#!/bin/bash
# 启动管理页面服务

export ADMIN_PORT=5001

echo "🚀 启动 DramaRelay Bot 管理页面..."
echo "📍 访问地址: http://localhost:5001"
echo ""

python3 admin_api.py
