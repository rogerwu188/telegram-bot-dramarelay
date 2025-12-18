#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接查询webhook_logs表验证数据
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# 添加项目路径
sys.path.insert(0, '/home/ubuntu/telegram-bot-dramarelay')

DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def check_webhook_logs():
    """检查webhook_logs表"""
    try:
        print("🔍 连接数据库...")
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # 1. 检查表是否存在
        print("\n1️⃣ 检查webhook_logs表是否存在...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'webhook_logs'
            )
        """)
        exists = cur.fetchone()['exists']
        print(f"   表存在: {exists}")
        
        if not exists:
            print("   ❌ webhook_logs表不存在！")
            return
        
        # 2. 查询总记录数
        print("\n2️⃣ 查询总记录数...")
        cur.execute("SELECT COUNT(*) as total FROM webhook_logs")
        total = cur.fetchone()['total']
        print(f"   总记录数: {total}")
        
        # 3. 查询最新的10条记录
        print("\n3️⃣ 查询最新的10条记录...")
        cur.execute("""
            SELECT 
                id,
                task_id,
                task_title,
                callback_status,
                created_at
            FROM webhook_logs
            ORDER BY created_at DESC
            LIMIT 10
        """)
        records = cur.fetchall()
        
        if records:
            print(f"   找到 {len(records)} 条记录:\n")
            for r in records:
                print(f"   ID: {r['id']}")
                print(f"   任务ID: {r['task_id']}")
                print(f"   任务标题: {r['task_title']}")
                print(f"   状态: {r['callback_status']}")
                print(f"   时间: {r['created_at']}")
                print("   " + "-" * 50)
        else:
            print("   ❌ 没有找到任何记录！")
        
        # 4. 查询今天的记录
        print("\n4️⃣ 查询今天的记录...")
        cur.execute("""
            SELECT COUNT(*) as today_total
            FROM webhook_logs
            WHERE created_at >= CURRENT_DATE
        """)
        today_total = cur.fetchone()['today_total']
        print(f"   今天的记录数: {today_total}")
        
        # 5. 查询最近1小时的记录
        print("\n5️⃣ 查询最近1小时的记录...")
        cur.execute("""
            SELECT COUNT(*) as recent_total
            FROM webhook_logs
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """)
        recent_total = cur.fetchone()['recent_total']
        print(f"   最近1小时的记录数: {recent_total}")
        
        cur.close()
        conn.close()
        
        print("\n✅ 检查完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_webhook_logs()
