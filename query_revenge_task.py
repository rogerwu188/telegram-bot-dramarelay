#!/usr/bin/env python3
"""查询Revenge - 第7集任务的完整数据"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL环境变量未设置")
    sys.exit(1)

try:
    # 连接数据库
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # 查询Revenge - 第7集任务
    cur.execute("""
        SELECT *
        FROM drama_tasks
        WHERE title LIKE '%Revenge%第7集%'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    task = cur.fetchone()
    
    if not task:
        print("❌ 未找到'Revenge - 第7集'任务")
        sys.exit(1)
    
    print("=" * 80)
    print("📋 Revenge - 第7集 任务完整数据")
    print("=" * 80)
    print()
    
    # 按字段输出
    for key, value in task.items():
        # 格式化显示
        if value is None:
            display_value = "NULL"
        elif isinstance(value, (dict, list)):
            display_value = json.dumps(value, ensure_ascii=False, indent=2)
        else:
            display_value = str(value)
        
        print(f"{key:30s}: {display_value}")
    
    print()
    print("=" * 80)
    
    # 特别检查callback相关字段
    print("\n🔍 关键字段检查：")
    print(f"  - callback_url: {task.get('callback_url') or 'NULL'}")
    print(f"  - callback_secret: {task.get('callback_secret') or 'NULL'}")
    print(f"  - callback_status: {task.get('callback_status') or 'NULL'}")
    print(f"  - callback_retry_count: {task.get('callback_retry_count') or 0}")
    print(f"  - external_task_id: {task.get('external_task_id') or 'NULL'}")
    print(f"  - project_id: {task.get('project_id') or 'NULL'}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ 查询失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
