#!/usr/bin/env python3
"""
手动触发 Webhook 回调测试脚本
用于验证 Webhook 功能是否正常工作
"""

import asyncio
import sys
from webhook_notifier import send_task_completed_webhook

async def main():
    """手动触发 Webhook 测试"""
    
    # 测试数据
    task_id = 38  # 使用任务 38 进行测试
    user_id = 5156570084  # 您的用户 ID
    platform = "tiktok"
    submission_link = "https://www.tiktok.com/@wu.roger7/video/7577587517487107341"
    node_power_earned = 10
    verification_details = {
        "matched": True,
        "match_rate": 100,
        "matched_keywords": ["test"]
    }
    
    print("=" * 60)
    print("🧪 手动 Webhook 回调测试")
    print("=" * 60)
    print(f"\n📋 测试参数:")
    print(f"  - Task ID: {task_id}")
    print(f"  - User ID: {user_id}")
    print(f"  - Platform: {platform}")
    print(f"  - Link: {submission_link}")
    print(f"  - Node Power: {node_power_earned}")
    print(f"\n🚀 开始发送 Webhook...\n")
    
    try:
        success = await send_task_completed_webhook(
            task_id=task_id,
            user_id=user_id,
            platform=platform,
            submission_link=submission_link,
            node_power_earned=node_power_earned,
            verification_details=verification_details
        )
        
        print("\n" + "=" * 60)
        if success:
            print("✅ Webhook 发送成功!")
            print("\n请检查:")
            print("  1. Supabase task_completions 表是否有新记录")
            print("  2. 数据统计页面是否更新")
        else:
            print("❌ Webhook 发送失败!")
            print("\n请检查:")
            print("  1. Railway 日志中的错误信息")
            print("  2. Supabase 函数是否正常运行")
        print("=" * 60)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
