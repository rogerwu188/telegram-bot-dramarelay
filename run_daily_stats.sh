#!/bin/bash
# 每日统计扫描定时任务脚本
# 用于 cron 定时执行

# 设置工作目录
cd "$(dirname "$0")"

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 执行扫描（默认扫描昨天的数据）
echo "=========================================="
echo "开始每日统计扫描: $(date)"
echo "=========================================="

python3 daily_stats_scanner.py

echo "=========================================="
echo "扫描完成: $(date)"
echo "=========================================="
