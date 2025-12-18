#!/usr/bin/env python3
"""测试webhook查询，找出video_url错误的根源"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 从环境变量获取数据库连接
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("错误：未找到DATABASE_URL环境变量")
    print("请在Railway中设置或手动提供数据库连接字符串")
    exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # 检查webhook_logs表是否存在
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'webhook_logs'
        )
    """)
    webhook_logs_exists = cur.fetchone()['exists']
    print(f"webhook_logs表存在: {webhook_logs_exists}")
    
    if webhook_logs_exists:
        # 检查webhook_logs表结构
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'webhook_logs'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        print("\nwebhook_logs表结构:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
        
        # 检查是否有数据
        cur.execute("SELECT COUNT(*) as count FROM webhook_logs")
        count = cur.fetchone()['count']
        print(f"\nwebhook_logs记录数: {count}")
        
        if count > 0:
            # 测试第一个查询（有时间过滤）
            print("\n测试查询1（24小时内）:")
            try:
                cur.execute("""
                    SELECT 
                        wl.id,
                        wl.task_id,
                        wl.task_title,
                        wl.project_id,
                        wl.callback_url,
                        wl.callback_status,
                        wl.payload,
                        wl.created_at,
                        t.external_task_id,
                        t.callback_retry_count,
                        t.callback_last_attempt,
                        t.video_url,
                        COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
                    FROM webhook_logs wl
                    LEFT JOIN drama_tasks t ON wl.task_id = t.task_id
                    LEFT JOIN user_tasks ut ON wl.task_id = ut.task_id
                    WHERE wl.created_at >= NOW() - INTERVAL '24 hours'
                    GROUP BY wl.id, wl.task_id, wl.task_title, wl.project_id, wl.callback_url, 
                             wl.callback_status, wl.payload, wl.created_at, t.external_task_id,
                             t.callback_retry_count, t.callback_last_attempt, t.video_url
                    ORDER BY wl.created_at DESC
                    LIMIT 1
                """)
                result = cur.fetchone()
                if result:
                    print("✓ 查询成功")
                    print(f"  task_id: {result['task_id']}")
                    print(f"  video_url: {result.get('video_url', 'NULL')}")
                else:
                    print("  没有24小时内的记录")
            except Exception as e:
                print(f"✗ 查询失败: {e}")
            
            # 测试第二个查询（无时间过滤）
            print("\n测试查询2（所有记录）:")
            try:
                cur.execute("""
                    SELECT 
                        wl.id,
                        wl.task_id,
                        wl.task_title,
                        wl.project_id,
                        wl.callback_url,
                        wl.callback_status,
                        wl.payload,
                        wl.created_at,
                        t.external_task_id,
                        t.callback_retry_count,
                        t.callback_last_attempt,
                        t.video_url,
                        COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
                    FROM webhook_logs wl
                    LEFT JOIN drama_tasks t ON wl.task_id = t.task_id
                    LEFT JOIN user_tasks ut ON wl.task_id = ut.task_id
                    GROUP BY wl.id, wl.task_id, wl.task_title, wl.project_id, wl.callback_url, 
                             wl.callback_status, wl.payload, wl.created_at, t.external_task_id,
                             t.callback_retry_count, t.callback_last_attempt, t.video_url
                    ORDER BY wl.created_at DESC
                    LIMIT 1
                """)
                result = cur.fetchone()
                if result:
                    print("✓ 查询成功")
                    print(f"  task_id: {result['task_id']}")
                    print(f"  video_url: {result.get('video_url', 'NULL')}")
                else:
                    print("  没有记录")
            except Exception as e:
                print(f"✗ 查询失败: {e}")
        else:
            print("\n警告: webhook_logs表为空，将使用drama_tasks fallback查询")
    
    # 测试drama_tasks fallback查询
    print("\n测试drama_tasks fallback查询:")
    try:
        cur.execute("""
            SELECT 
                t.task_id,
                t.external_task_id,
                t.project_id,
                t.title,
                t.duration,
                t.platform_requirements,
                t.callback_url,
                t.callback_status,
                t.callback_retry_count,
                t.callback_last_attempt,
                t.created_at,
                t.video_url,
                COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
            FROM drama_tasks t
            LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
            WHERE t.callback_url IS NOT NULL
            GROUP BY t.task_id
            ORDER BY t.callback_last_attempt DESC NULLS LAST, t.created_at DESC
            LIMIT 1
        """)
        result = cur.fetchone()
        if result:
            print("✓ 查询成功")
            print(f"  task_id: {result['task_id']}")
            print(f"  video_url: {result.get('video_url', 'NULL')}")
        else:
            print("  没有记录")
    except Exception as e:
        print(f"✗ 查询失败: {e}")
    
    cur.close()
    conn.close()
    print("\n测试完成")
    
except Exception as e:
    print(f"数据库连接错误: {e}")
    exit(1)
