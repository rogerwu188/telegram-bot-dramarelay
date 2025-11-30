#!/usr/bin/env python3
"""
测试统计回传接口
模拟用户完成任务后的回调
"""
import os
import sys
import asyncio
import json

# 设置环境变量
os.environ['DATABASE_URL'] = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

# 导入 webhook_notifier
sys.path.insert(0, '/home/ubuntu/telegram-bot-dramarelay')
from webhook_notifier import notify_task_completion

async def test_callback():
    """测试回调功能"""
    print("=" * 60)
    print("测试统计回传接口")
    print("=" * 60)
    
    # 测试参数
    task_id = 52  # Bot 内部 task_id（对应 external_task_id=888）
    user_id = 5156570084  # 管理员用户
    platform = "YouTube"
    submission_link = "https://www.youtube.com/watch?v=test123"
    node_power_earned = 10
    verification_details = {
        'views': 150,
        'likes': 20,
        'comments': 5
    }
    
    print(f"\n测试参数：")
    print(f"  task_id (内部): {task_id}")
    print(f"  user_id: {user_id}")
    print(f"  platform: {platform}")
    print(f"  submission_link: {submission_link}")
    print(f"  verification_details: {json.dumps(verification_details, indent=2)}")
    
    print(f"\n发送回调...")
    success = await notify_task_completion(
        task_id=task_id,
        user_id=user_id,
        platform=platform,
        submission_link=submission_link,
        node_power_earned=node_power_earned,
        verification_details=verification_details
    )
    
    if success:
        print("\n✅ 回调发送成功！")
    else:
        print("\n❌ 回调发送失败！")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(test_callback())
