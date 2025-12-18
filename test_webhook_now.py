#!/usr/bin/env python3
"""
立即测试Webhook发送和日志记录功能
使用最近提交的任务数据进行测试
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/home/ubuntu/telegram-bot-dramarelay')

async def main():
    """主测试函数"""
    print("=" * 80)
    print("🧪 Webhook发送测试")
    print("=" * 80)
    
    # 导入必要的模块
    from webhook_notifier import send_task_completed_webhook
    from bot import get_db_connection
    
    # 连接数据库，查找最近提交的任务
    print("\n📊 正在查询最近提交的任务...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 查找最近的用户提交记录
    cur.execute("""
        SELECT 
            ut.user_id,
            ut.task_id,
            ut.platform,
            ut.submission_link,
            ut.node_power_earned,
            dt.title,
            dt.callback_url
        FROM user_tasks ut
        JOIN drama_tasks dt ON ut.task_id = dt.task_id
        WHERE ut.status = 'submitted'
        ORDER BY ut.submitted_at DESC
        LIMIT 1
    """)
    
    submission = cur.fetchone()
    
    if not submission:
        print("\n❌ 没有找到已提交的任务记录")
        print("💡 请先在Telegram Bot中提交一个任务，然后再运行此脚本")
        cur.close()
        conn.close()
        return False
    
    # 提取数据
    user_id = submission['user_id']
    task_id = submission['task_id']
    platform = submission['platform']
    submission_link = submission['submission_link']
    node_power_earned = submission['node_power_earned']
    task_title = submission['title']
    callback_url = submission['callback_url']
    
    cur.close()
    conn.close()
    
    # 显示测试信息
    print("\n✅ 找到最近提交的任务：")
    print(f"  - 任务ID: {task_id}")
    print(f"  - 任务标题: {task_title}")
    print(f"  - 用户ID: {user_id}")
    print(f"  - 平台: {platform}")
    print(f"  - 提交链接: {submission_link[:60]}...")
    print(f"  - 奖励: {node_power_earned} X2C")
    print(f"  - 回调URL: {callback_url[:60] if callback_url else '未配置'}...")
    
    if not callback_url:
        print("\n⚠️ 警告：该任务没有配置callback_url")
        print("   Webhook不会实际发送到X2C平台，但会记录到webhook_logs表")
    
    # 确认是否继续
    print("\n" + "=" * 80)
    print("📤 准备发送Webhook测试...")
    print("=" * 80)
    
    # 发送webhook
    try:
        success = await send_task_completed_webhook(
            task_id=task_id,
            user_id=user_id,
            platform=platform,
            submission_link=submission_link,
            node_power_earned=node_power_earned,
            verification_details={}
        )
        
        print("\n" + "=" * 80)
        if success:
            print("✅ Webhook发送成功！")
        else:
            print("❌ Webhook发送失败")
        print("=" * 80)
        
        # 查询webhook_logs表，确认是否记录
        print("\n📋 查询webhook_logs表...")
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, task_id, task_title, callback_status, created_at
            FROM webhook_logs
            WHERE task_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (task_id,))
        
        log_record = cur.fetchone()
        
        if log_record:
            print("\n✅ 找到webhook日志记录：")
            print(f"  - 日志ID: {log_record['id']}")
            print(f"  - 任务ID: {log_record['task_id']}")
            print(f"  - 任务标题: {log_record['task_title']}")
            print(f"  - 回调状态: {log_record['callback_status']}")
            print(f"  - 创建时间: {log_record['created_at']}")
            print("\n🎉 日志记录功能正常工作！")
        else:
            print("\n❌ 没有找到webhook日志记录")
            print("   可能是webhook_logs表插入失败")
        
        cur.close()
        conn.close()
        
        return success
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("\n🚀 开始测试...\n")
    result = asyncio.run(main())
    
    print("\n" + "=" * 80)
    if result:
        print("✅ 测试完成！请刷新管理后台查看webhook日志")
    else:
        print("❌ 测试失败，请查看上面的错误信息")
    print("=" * 80)
    
    sys.exit(0 if result else 1)
