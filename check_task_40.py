#!/usr/bin/env python3
"""
检查 task_id=40 的 Webhook 配置
"""

import psycopg2
import os

# 数据库连接
DATABASE_URL = os.getenv('DATABASE_URL')

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 查询 task_id=40 的配置
cur.execute("""
    SELECT 
        task_id,
        title,
        callback_url,
        callback_secret,
        callback_status,
        callback_retry_count,
        callback_last_attempt,
        created_at
    FROM drama_tasks
    WHERE task_id = 40
""")

result = cur.fetchone()

if result:
    print("=" * 80)
    print("📋 Task ID 40 配置信息")
    print("=" * 80)
    print(f"Task ID: {result[0]}")
    print(f"Title: {result[1]}")
    print(f"Callback URL: {result[2]}")
    print(f"Callback Secret: {result[3]}")
    print(f"Callback Status: {result[4]}")
    print(f"Callback Retry Count: {result[5]}")
    print(f"Callback Last Attempt: {result[6]}")
    print(f"Created At: {result[7]}")
    print("=" * 80)
    
    if result[2] is None:
        print("\n❌ 问题: callback_url 为 NULL")
        print("✅ 解决方案: 需要更新 task_id=40 的 callback_url")
    else:
        print(f"\n✅ callback_url 已配置: {result[2]}")
else:
    print("❌ Task ID 40 不存在")

# 查询所有任务的 callback_url 配置情况
cur.execute("""
    SELECT 
        COUNT(*) as total_tasks,
        COUNT(callback_url) as tasks_with_callback,
        COUNT(*) - COUNT(callback_url) as tasks_without_callback
    FROM drama_tasks
    WHERE status = 'active'
""")

stats = cur.fetchone()
print(f"\n📊 所有活跃任务的 Webhook 配置统计:")
print(f"总任务数: {stats[0]}")
print(f"已配置 Webhook: {stats[1]}")
print(f"未配置 Webhook: {stats[2]}")

cur.close()
conn.close()
