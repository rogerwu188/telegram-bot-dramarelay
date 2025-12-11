#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日统计功能测试脚本
"""

import os
import asyncio
from datetime import date, timedelta
from daily_stats_scanner import DailyStatsScanner

async def test_scanner():
    """测试扫描器功能"""
    print("="*70)
    print("🧪 测试每日统计扫描器")
    print("="*70)
    
    # 检查环境变量
    print("\n1️⃣ 检查环境变量...")
    database_url = os.getenv('DATABASE_URL')
    tikhub_key = os.getenv('TIKHUB_API_KEY')
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    
    if not database_url:
        print("❌ DATABASE_URL 未设置")
        return
    else:
        print("✅ DATABASE_URL 已设置")
    
    if not tikhub_key:
        print("⚠️ TIKHUB_API_KEY 未设置（抖音数据抓取将失败）")
    else:
        print("✅ TIKHUB_API_KEY 已设置")
    
    if not youtube_key:
        print("⚠️ YOUTUBE_API_KEY 未设置（YouTube数据抓取将失败）")
    else:
        print("✅ YOUTUBE_API_KEY 已设置")
    
    # 创建扫描器实例
    print("\n2️⃣ 创建扫描器实例...")
    try:
        scanner = DailyStatsScanner()
        print("✅ 扫描器创建成功")
    except Exception as e:
        print(f"❌ 扫描器创建失败: {e}")
        return
    
    # 测试扫描（使用昨天的日期）
    print("\n3️⃣ 测试扫描功能...")
    target_date = date.today() - timedelta(days=1)
    print(f"📅 目标日期: {target_date}")
    
    try:
        result = await scanner.scan_and_aggregate(target_date)
        
        print("\n" + "="*70)
        print("📊 扫描结果")
        print("="*70)
        print(f"✅ 成功: {result['success']}")
        print(f"📅 日期: {result['date']}")
        print(f"📋 处理任务数: {result['tasks_processed']}")
        print(f"💾 创建统计数: {result['stats_created']}")
        print(f"📤 发送Webhook数: {result['webhooks_sent']}")
        
        if result['errors']:
            print(f"\n❌ 错误 ({len(result['errors'])}个):")
            for error in result['errors']:
                print(f"  - {error}")
        
        print("="*70)
        
        if result['success']:
            print("\n✅ 测试通过！")
        else:
            print("\n⚠️ 测试完成，但有错误")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scanner())
