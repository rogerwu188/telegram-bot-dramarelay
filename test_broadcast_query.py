import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

print("模拟回传查询")
print("=" * 70)

# 检查全局 Callback URL
cur.execute("""
    SELECT config_value FROM system_config WHERE config_key = 'x2c_callback_url'
""")
config_result = cur.fetchone()
global_callback_url = config_result['config_value'] if config_result else None
print(f"全局 Callback URL: {global_callback_url}")

# 使用与 stats_broadcaster.py 相同的查询
if global_callback_url:
    print("\n使用全局 Callback URL 查询...")
    cur.execute("""
        SELECT DISTINCT
            t.task_id,
            t.external_task_id,
            t.project_id,
            t.title,
            ut.submission_link as video_url,
            t.callback_secret,
            t.duration,
            ut.user_id,
            ut.submitted_at
        FROM user_tasks ut
        JOIN drama_tasks t ON ut.task_id = t.task_id
        WHERE ut.status = 'submitted'
          AND ut.submitted_at >= NOW() - INTERVAL '7 days'
        ORDER BY ut.submitted_at DESC
    """)
else:
    print("\n使用任务级别 Callback URL 查询...")
    cur.execute("""
        SELECT DISTINCT
            t.task_id,
            t.external_task_id,
            t.project_id,
            t.title,
            ut.submission_link as video_url,
            t.callback_url,
            t.callback_secret,
            t.duration,
            ut.user_id,
            ut.submitted_at
        FROM user_tasks ut
        JOIN drama_tasks t ON ut.task_id = t.task_id
        WHERE ut.status = 'submitted'
          AND t.callback_url IS NOT NULL
          AND t.callback_url != ''
          AND ut.submitted_at >= NOW() - INTERVAL '7 days'
        ORDER BY ut.submitted_at DESC
    """)

tasks = cur.fetchall()
print(f"\n查询到 {len(tasks)} 个任务")

# 检查是否包含 320, 321, 387
target_ids = {320, 321, 387}
found_ids = set()
for task in tasks:
    if task['task_id'] in target_ids:
        found_ids.add(task['task_id'])
        print(f"\n✅ 找到任务 {task['task_id']}: {task['title']}")
        print(f"   user_id={task['user_id']}, submitted_at={task['submitted_at']}")

missing_ids = target_ids - found_ids
if missing_ids:
    print(f"\n❌ 未找到的任务: {missing_ids}")
else:
    print(f"\n✅ 所有目标任务都已找到")

# 列出所有查询到的 task_id
all_task_ids = sorted(set(task['task_id'] for task in tasks))
print(f"\n所有查询到的 task_id: {all_task_ids}")

cur.close()
conn.close()
