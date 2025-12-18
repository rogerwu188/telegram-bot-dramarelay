#!/usr/bin/env python3
"""查询user_tasks表结构和数据"""

import psycopg2
from psycopg2.extras import RealDictCursor

# 使用公网PostgreSQL连接字符串
DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor
    )

def main():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 查询user_tasks表结构
    print("\n=== user_tasks表结构 ===")
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'user_tasks'
        ORDER BY ordinal_position
    """)
    
    columns = cur.fetchall()
    print(f"\n字段列表：\n")
    for col in columns:
        print(f"  {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")
    
    # 查询最近的user_tasks记录
    print("\n\n=== 最近的user_tasks记录（前5条）===")
    cur.execute("""
        SELECT *
        FROM user_tasks
        ORDER BY submitted_at DESC NULLS LAST
        LIMIT 5
    """)
    
    tasks = cur.fetchall()
    print(f"\n找到 {len(tasks)} 条记录：\n")
    
    for task in tasks:
        print(f"User Task ID: {task.get('id')}")
        print(f"User ID: {task.get('user_id')}")
        print(f"Task ID: {task.get('task_id')}")
        print(f"Status: {task.get('status')}")
        print(f"Submission Link: {task.get('submission_link')}")
        print(f"Submitted At: {task.get('submitted_at')}")
        # 打印所有字段
        print(f"All fields: {dict(task)}")
        print("-" * 60)
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
