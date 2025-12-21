import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

print("=" * 60)
print("1. 检查 webhook_logs 表")
print("=" * 60)
cur.execute("SELECT COUNT(*) as total FROM webhook_logs")
print(f"webhook_logs 总数: {cur.fetchone()['total']}")

cur.execute("SELECT * FROM webhook_logs ORDER BY created_at DESC LIMIT 5")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  - task_id={row['task_id']}, status={row['callback_status']}, created_at={row['created_at']}")
else:
    print("  (无记录)")

print("\n" + "=" * 60)
print("2. 检查 user_tasks 表中 submitted 状态的任务")
print("=" * 60)
cur.execute("SELECT COUNT(*) as total FROM user_tasks WHERE status = 'submitted'")
print(f"submitted 状态任务总数: {cur.fetchone()['total']}")

cur.execute("""
    SELECT ut.task_id, ut.user_id, ut.status, ut.submission_link, ut.submitted_at,
           t.title, t.callback_url
    FROM user_tasks ut
    JOIN drama_tasks t ON ut.task_id = t.task_id
    WHERE ut.status = 'submitted'
    ORDER BY ut.submitted_at DESC
    LIMIT 5
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        callback_preview = row['callback_url'][:50] if row['callback_url'] else 'NULL'
        print(f"  - task_id={row['task_id']}, title={row['title'][:30]}")
        print(f"    user_id={row['user_id']}, submitted_at={row['submitted_at']}")
        print(f"    callback_url={callback_preview}")
        print(f"    submission_link={row['submission_link'][:50] if row['submission_link'] else 'NULL'}")
        print()
else:
    print("  (无记录)")

print("\n" + "=" * 60)
print("3. 检查 system_config 表中的全局 Callback URL")
print("=" * 60)
try:
    cur.execute("SELECT * FROM system_config WHERE config_key = 'x2c_callback_url'")
    row = cur.fetchone()
    if row:
        print(f"全局 Callback URL: {row['config_value']}")
    else:
        print("未配置全局 Callback URL")
except Exception as e:
    print(f"system_config 表不存在或查询失败: {e}")

print("\n" + "=" * 60)
print("4. 检查最近7天内的 submitted 任务")
print("=" * 60)
cur.execute("""
    SELECT COUNT(*) as total
    FROM user_tasks
    WHERE status = 'submitted'
      AND submitted_at >= NOW() - INTERVAL '7 days'
""")
print(f"最近7天内 submitted 任务数: {cur.fetchone()['total']}")

cur.close()
conn.close()
