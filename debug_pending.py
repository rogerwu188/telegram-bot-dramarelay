#!/usr/bin/env python3
"""检查 pending_verifications 表状态"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def check_pending():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    print("=== 所有 pending 状态的记录 ===")
    cur.execute("""
        SELECT pv.*, dt.title as task_title
        FROM pending_verifications pv
        LEFT JOIN drama_tasks dt ON pv.task_id = dt.task_id
        WHERE pv.status = 'pending'
        ORDER BY pv.created_at DESC
    """)
    
    records = cur.fetchall()
    for r in records:
        print(f"ID: {r['id']}")
        print(f"  User: {r['user_id']}")
        print(f"  Task: {r['task_id']} - {r.get('task_title', 'N/A')}")
        print(f"  URL: {r['video_url'][:80]}...")
        print(f"  Status: {r['status']}")
        print(f"  Retry: {r['retry_count']}")
        print(f"  Created: {r['created_at']}")
        print(f"  Updated: {r['updated_at']}")
        print()
    
    print(f"共 {len(records)} 条 pending 记录")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    check_pending()
