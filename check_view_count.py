#!/usr/bin/env python3
"""查询user_tasks表中的播放量数据"""

import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL公网连接
DATABASE_URL = "postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway"

def check_view_count():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # 查询user_tasks表结构
    print("=" * 60)
    print("1. 检查user_tasks表是否有view_count字段")
    print("=" * 60)
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'user_tasks'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    for col in columns:
        print(f"  {col['column_name']}: {col['data_type']}")
    
    # 查询submitted状态的任务的播放量
    print("\n" + "=" * 60)
    print("2. 查询submitted状态任务的播放量")
    print("=" * 60)
    
    # 先检查view_count字段是否存在
    has_view_count = any(col['column_name'] == 'view_count' for col in columns)
    
    if has_view_count:
        cur.execute("""
            SELECT 
                ut.id,
                ut.user_id,
                ut.task_id,
                ut.submission_link,
                ut.view_count,
                ut.like_count,
                ut.view_count_updated_at,
                t.title
            FROM user_tasks ut
            LEFT JOIN drama_tasks t ON ut.task_id = t.task_id
            WHERE ut.status = 'submitted'
            ORDER BY ut.submitted_at DESC
            LIMIT 10
        """)
        tasks = cur.fetchall()
        
        for task in tasks:
            print(f"\n任务ID: {task['task_id']}")
            print(f"  标题: {task['title']}")
            print(f"  用户ID: {task['user_id']}")
            print(f"  提交链接: {task['submission_link']}")
            print(f"  播放量: {task['view_count']}")
            print(f"  点赞数: {task['like_count']}")
            print(f"  更新时间: {task['view_count_updated_at']}")
    else:
        print("❌ user_tasks表中没有view_count字段！")
        print("需要先运行播放量抓取服务来创建这些字段。")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    check_view_count()
