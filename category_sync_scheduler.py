#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分类定时同步调度器
每15分钟从 X2C API 同步分类数据
"""

import logging
import asyncio
from datetime import datetime
from x2c_category_sync import sync_categories, get_last_sync_time

logger = logging.getLogger(__name__)

# 同步间隔（秒）
SYNC_INTERVAL = 15 * 60  # 15分钟


async def category_sync_task():
    """
    分类同步定时任务
    每15分钟执行一次
    """
    logger.info("🔄 启动分类同步定时任务...")
    
    # 首次立即同步
    logger.info("📥 执行首次分类同步...")
    sync_categories()
    
    while True:
        try:
            # 等待15分钟
            await asyncio.sleep(SYNC_INTERVAL)
            
            # 执行同步
            logger.info("📥 执行定时分类同步...")
            success = sync_categories()
            
            if success:
                last_sync = get_last_sync_time()
                logger.info(f"✅ 分类同步成功，最后同步时间: {last_sync}")
            else:
                logger.warning("⚠️ 分类同步失败，将在下次定时任务时重试")
                
        except Exception as e:
            logger.error(f"❌ 分类同步任务异常: {e}")
            # 继续运行，不中断定时任务


def start_category_sync_scheduler(application):
    """
    启动分类同步调度器
    
    Args:
        application: Telegram Bot Application 实例
    """
    # 使用 application.job_queue 来调度任务
    # 首次立即同步
    logger.info("📥 执行首次分类同步...")
    sync_categories()
    
    # 创建定时任务（每15分钟执行一次）
    async def sync_job(context):
        logger.info("📥 执行定时分类同步...")
        success = sync_categories()
        if success:
            last_sync = get_last_sync_time()
            logger.info(f"✅ 分类同步成功，最后同步时间: {last_sync}")
        else:
            logger.warning("⚠️ 分类同步失败，将在下次定时任务时重试")
    
    # 添加到job_queue（每15分钟执行一次）
    application.job_queue.run_repeating(sync_job, interval=900, first=10)
    logger.info("✅ 分类同步调度器已启动（每15分钟同步一次）")


if __name__ == '__main__':
    # 测试定时任务
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("测试分类同步调度器（按 Ctrl+C 停止）...")
    
    async def test():
        await category_sync_task()
    
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n停止测试")
