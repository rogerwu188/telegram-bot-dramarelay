#!/usr/bin/env python3
"""检查Revenge任务的callback_url"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os

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
    
    # 查询Revenge相关的任务
    print("\n=== 查询drama_tasks表中Revenge相关任务 ===")
    cur.execute("""
        SELECT task_id, title, callback_url, callback_secret, external_task_id
        FROM drama_tasks
        WHERE title LIKE '%Revenge%'
        ORDER BY task_id
    """)
    
    tasks = cur.fetchall()
    print(f"\n找到 {len(tasks)} 个Revenge相关任务：\n")
    
    for task in tasks:
        print(f"Task ID: {task['task_id']}")
        print(f"Title: {task['title']}")
        print(f"External Task ID: {task['external_task_id']}")
        print(f"Callback URL: {task['callback_url']}")
        print(f"Callback Secret: {task['callback_secret']}")
        print("-" * 60)
    
    # 查询user_tasks中Revenge相关的提交
    print("\n=== 查询user_tasks表中Revenge相关的提交 ===")
    cur.execute("""
        SELECT ut.user_id, ut.task_id, ut.status, ut.submission_link, ut.submitted_at,
               t.title, t.callback_url
        FROM user_tasks ut
        JOIN drama_tasks t ON ut.task_id = t.task_id
        WHERE t.title LIKE '%Revenge%'
          AND ut.status = 'submitted'
        ORDER BY ut.submitted_at DESC
    """)
    
    submissions = cur.fetchall()
    print(f"\n找到 {len(submissions)} 个Revenge相关的用户提交：\n")
    
    for sub in submissions:
        print(f"User ID: {sub['user_id']}")
        print(f"Task ID: {sub['task_id']}")
        print(f"Title: {sub['title']}")
        print(f"Status: {sub['status']}")
        print(f"Submitted At: {sub['submitted_at']}")
        print(f"Submission Link: {sub['submission_link']}")
        print(f"Callback URL: {sub['callback_url']}")
        print("-" * 60)
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
