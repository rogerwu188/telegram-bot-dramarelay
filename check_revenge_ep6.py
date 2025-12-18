#!/usr/bin/env python3
"""查询Revenge第6集的提交链接和抓取状态"""
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # 查询Revenge第6集的所有提交记录
    cur.execute("""
        SELECT 
            ut.id,
            ut.user_id,
            ut.task_id,
            ut.submission_link,
            ut.view_count,
            ut.like_count,
            ut.view_count_updated_at,
            ut.submitted_at,
            t.title
        FROM user_tasks ut
        JOIN drama_tasks t ON ut.task_id = t.task_id
        WHERE t.title LIKE '%Revenge%第6集%'
        AND ut.status = 'submitted'
        ORDER BY ut.submitted_at DESC
    """)
    
    tasks = cur.fetchall()
    
    print(f"找到 {len(tasks)} 条 Revenge 第6集 记录:")
    print("=" * 80)
    
    for task in tasks:
        print(f"ID: {task['id']}")
        print(f"用户ID: {task['user_id']}")
        print(f"任务标题: {task['title']}")
        print(f"提交链接: {task['submission_link']}")
        print(f"播放量: {task['view_count']}")
        print(f"点赞数: {task['like_count']}")
        print(f"抓取时间: {task['view_count_updated_at']}")
        print(f"提交时间: {task['submitted_at']}")
        print("-" * 80)
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
