#!/usr/bin/env python3
"""删除无效的TikTok链接记录（保留@aidramastudio的记录）"""

import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL公网连接
DATABASE_URL = "postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway"

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # 要删除的记录ID列表（排除ID 77 "Revenge - 第7集"）
    invalid_ids = [
        57, 50, 54, 55, 56, 52, 43, 42, 41, 40, 38, 37, 36, 35, 34, 33, 32, 31, 30, 28, 29, 27, 26, 25, 2, 22, 23, 14, 15, 16, 17, 18, 19, 20, 21, 6
    ]
    
    print(f"准备删除 {len(invalid_ids)} 条无效记录...")
    print(f"保留 ID 77 (Revenge - 第7集)")
    
    # 删除记录
    for record_id in invalid_ids:
        cur.execute("SELECT id, task_id, submission_link FROM user_tasks WHERE id = %s", (record_id,))
        record = cur.fetchone()
        if record:
            cur.execute("DELETE FROM user_tasks WHERE id = %s", (record_id,))
            print(f"  ✅ 已删除 ID {record_id}: {record['submission_link'][:60]}...")
        else:
            print(f"  ⚠️ ID {record_id} 不存在，跳过")
    
    conn.commit()
    
    # 统计剩余记录
    cur.execute("SELECT COUNT(*) as count FROM user_tasks WHERE status = 'submitted'")
    remaining = cur.fetchone()['count']
    
    print(f"\n✅ 删除完成！")
    print(f"剩余已完成任务记录: {remaining} 条")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
