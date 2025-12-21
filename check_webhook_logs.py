import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

print("检查 webhook_logs 表")
print("=" * 70)

# 总记录数
cur.execute("SELECT COUNT(*) as total FROM webhook_logs")
total = cur.fetchone()['total']
print(f"总记录数: {total}")

# 不同 task_id 数量
cur.execute("SELECT COUNT(DISTINCT task_id) as unique_tasks FROM webhook_logs")
unique_tasks = cur.fetchone()['unique_tasks']
print(f"不同 task_id 数量: {unique_tasks}")

# 最新的记录
print("\n最新的10条记录:")
cur.execute("""
    SELECT task_id, task_title, callback_status, created_at
    FROM webhook_logs
    ORDER BY created_at DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  - task_id={row['task_id']}, title={row['task_title'][:25]}, status={row['callback_status']}, time={row['created_at']}")

# 检查是否有 320, 321, 387
print("\n检查目标任务 (320, 321, 387):")
for task_id in [320, 321, 387]:
    cur.execute("SELECT COUNT(*) as count FROM webhook_logs WHERE task_id = %s", (task_id,))
    count = cur.fetchone()['count']
    status = "✅" if count > 0 else "❌"
    print(f"  {status} task_id={task_id}: {count} 条记录")

# 按 task_id 统计记录数
print("\n按 task_id 统计记录数:")
cur.execute("""
    SELECT task_id, COUNT(*) as count
    FROM webhook_logs
    GROUP BY task_id
    ORDER BY task_id
""")
for row in cur.fetchall():
    print(f"  task_id={row['task_id']}: {row['count']} 条")

cur.close()
conn.close()
