#!/usr/bin/env python3
"""查询有callback_url的任务"""

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
    
    # 查询有callback_url的任务
    print("\n=== 查询有callback_url的任务（前10条）===")
    cur.execute("""
        SELECT task_id, title, callback_url, callback_secret, external_task_id, project_id
        FROM drama_tasks
        WHERE callback_url IS NOT NULL AND callback_url != ''
        ORDER BY task_id DESC
        LIMIT 10
    """)
    
    tasks = cur.fetchall()
    print(f"\n找到 {len(tasks)} 个有callback_url的任务：\n")
    
    for task in tasks:
        print(f"Task ID: {task['task_id']}")
        print(f"Title: {task['title']}")
        print(f"Project ID: {task['project_id']}")
        print(f"External Task ID: {task['external_task_id']}")
        print(f"Callback URL: {task['callback_url']}")
        print(f"Callback Secret: {task['callback_secret']}")
        print("-" * 60)
    
    # 统计callback_url的分布
    print("\n=== Callback URL统计 ===")
    cur.execute("""
        SELECT 
            CASE 
                WHEN callback_url IS NULL THEN 'NULL'
                WHEN callback_url = '' THEN 'EMPTY'
                ELSE callback_url
            END as url_value,
            COUNT(*) as count
        FROM drama_tasks
        GROUP BY url_value
        ORDER BY count DESC
    """)
    
    stats = cur.fetchall()
    print(f"\nCallback URL分布：\n")
    for stat in stats:
        print(f"{stat['url_value']}: {stat['count']} 个任务")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
