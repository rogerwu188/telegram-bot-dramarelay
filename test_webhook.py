#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook 功能测试脚本
用于测试 Webhook 回调功能是否正常工作
"""

import asyncio
import sys
from webhook_notifier import send_task_completed_webhook

async def test_webhook_callback():
    """测试 Webhook 回调功能"""
    print("=" * 80)
    print("🧪 开始测试 Webhook 回调功能")
    print("=" * 80)
    
    # 测试数据
    test_task_id = 1  # 假设任务 ID 为 1
    test_user_id = 123456789
    test_platform = "tiktok"
    test_submission_link = "https://www.tiktok.com/@test/video/123456"
    test_node_power = 10
    test_verification_details = {
        "matched": True,
        "match_rate": 100,
        "matched_keywords": ["测试关键词1", "测试关键词2"]
    }
    
    print(f"\n📋 测试参数:")
    print(f"  - Task ID: {test_task_id}")
    print(f"  - User ID: {test_user_id}")
    print(f"  - Platform: {test_platform}")
    print(f"  - Submission Link: {test_submission_link}")
    print(f"  - Node Power: {test_node_power}")
    print(f"  - Verification Details: {test_verification_details}")
    
    print(f"\n⚠️  注意: 请确保任务 {test_task_id} 已配置 callback_url")
    print(f"  可以使用以下 SQL 命令配置测试回调 URL:")
    print(f"  UPDATE drama_tasks SET callback_url = 'https://webhook.site/your-unique-id' WHERE task_id = {test_task_id};")
    
    input("\n按 Enter 键继续测试...")
    
    print("\n📤 开始发送 Webhook 回调...")
    
    try:
        success = await send_task_completed_webhook(
            task_id=test_task_id,
            user_id=test_user_id,
            platform=test_platform,
            submission_link=test_submission_link,
            node_power_earned=test_node_power,
            verification_details=test_verification_details
        )
        
        print("\n" + "=" * 80)
        if success:
            print("✅ Webhook 回调测试成功!")
            print("请检查回调 URL 是否收到请求")
        else:
            print("❌ Webhook 回调测试失败!")
            print("请查看日志了解详细错误信息")
        print("=" * 80)
        
        return success
    
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ 测试过程中发生异常: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    # 运行测试
    result = asyncio.run(test_webhook_callback())
    sys.exit(0 if result else 1)
