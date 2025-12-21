import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

print("检查 task_id=387 的详细信息")
print("=" * 60)

# 检查 drama_tasks 表
cur.execute("""
    SELECT task_id, title, callback_url, callback_secret, created_at
    FROM drama_tasks
    WHERE task_id = 387
""")
task = cur.fetchone()
if task:
    print(f"任务ID: {task['task_id']}")
    print(f"标题: {task['title']}")
    print(f"Callback URL: {task['callback_url']}")
    print(f"Callback Secret: {task['callback_secret']}")
    print(f"创建时间: {task['created_at']}")

# 检查 user_tasks 表
print("\n用户提交记录:")
cur.execute("""
    SELECT user_id, status, submission_link, submitted_at
    FROM user_tasks
    WHERE task_id = 387 AND status = 'submitted'
""")
for row in cur.fetchall():
    print(f"  - user_id={row['user_id']}, submitted_at={row['submitted_at']}")
    print(f"    link={row['submission_link']}")

# 检查是否在最近7天内
cur.execute("""
    SELECT submitted_at, 
           submitted_at >= NOW() - INTERVAL '7 days' as within_7_days
    FROM user_tasks
    WHERE task_id = 387 AND status = 'submitted'
""")
for row in cur.fetchall():
    print(f"\n提交时间: {row['submitted_at']}")
    print(f"是否在最近7天内: {row['within_7_days']}")

cur.close()
conn.close()
