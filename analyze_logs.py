import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

print("=" * 70)
print("分析窗口1（Webhook日志）和窗口3（任务完成日志）的数量差异")
print("=" * 70)

# 1. 窗口1: Webhook日志 - 来自 webhook_logs 表，按 task_id 去重
print("\n【窗口1: 回传X2C Pool任务状态数据日志】")
print("-" * 50)
cur.execute("""
    SELECT COUNT(DISTINCT task_id) as unique_tasks
    FROM webhook_logs
""")
webhook_unique_tasks = cur.fetchone()['unique_tasks']
print(f"webhook_logs 表中不同 task_id 数量: {webhook_unique_tasks}")

cur.execute("SELECT COUNT(*) as total FROM webhook_logs")
webhook_total = cur.fetchone()['total']
print(f"webhook_logs 表总记录数: {webhook_total}")

# 获取所有有webhook记录的task_id
cur.execute("SELECT DISTINCT task_id FROM webhook_logs ORDER BY task_id")
webhook_task_ids = set(row['task_id'] for row in cur.fetchall())
print(f"有Webhook记录的task_id列表: {sorted(webhook_task_ids)}")

# 2. 窗口3: 任务完成日志 - 来自 user_tasks 表，status='submitted'
print("\n【窗口3: X2C Pool下发任务完成日志】")
print("-" * 50)
cur.execute("""
    SELECT COUNT(DISTINCT task_id) as unique_tasks
    FROM user_tasks
    WHERE status = 'submitted'
""")
completion_unique_tasks = cur.fetchone()['unique_tasks']
print(f"user_tasks 表中 submitted 状态的不同 task_id 数量: {completion_unique_tasks}")

cur.execute("""
    SELECT COUNT(*) as total
    FROM user_tasks
    WHERE status = 'submitted'
""")
completion_total = cur.fetchone()['total']
print(f"user_tasks 表中 submitted 状态的总记录数: {completion_total}")

# 获取所有已完成任务的task_id
cur.execute("""
    SELECT DISTINCT task_id 
    FROM user_tasks 
    WHERE status = 'submitted'
    ORDER BY task_id
""")
completion_task_ids = set(row['task_id'] for row in cur.fetchall())
print(f"已完成任务的task_id列表: {sorted(completion_task_ids)}")

# 3. 分析差异
print("\n【差异分析】")
print("-" * 50)

# 在完成日志中但不在webhook日志中的任务
missing_webhooks = completion_task_ids - webhook_task_ids
print(f"\n已完成但没有Webhook记录的任务 ({len(missing_webhooks)} 个):")
if missing_webhooks:
    for task_id in sorted(missing_webhooks):
        cur.execute("""
            SELECT ut.task_id, t.title, ut.submitted_at, t.callback_url
            FROM user_tasks ut
            JOIN drama_tasks t ON ut.task_id = t.task_id
            WHERE ut.task_id = %s AND ut.status = 'submitted'
            LIMIT 1
        """, (task_id,))
        task = cur.fetchone()
        if task:
            callback_status = "有" if task['callback_url'] else "无"
            print(f"  - task_id={task_id}, title={task['title'][:30]}, callback_url={callback_status}")

# 在webhook日志中但不在完成日志中的任务（不应该存在）
extra_webhooks = webhook_task_ids - completion_task_ids
print(f"\n有Webhook记录但没有完成记录的任务 ({len(extra_webhooks)} 个):")
if extra_webhooks:
    for task_id in sorted(extra_webhooks):
        print(f"  - task_id={task_id}")

print("\n【结论】")
print("-" * 50)
print(f"窗口1显示 {webhook_unique_tasks} 条（按task_id去重的webhook记录）")
print(f"窗口3显示 {completion_unique_tasks} 条（按task_id去重的完成记录）")
print(f"差异: {completion_unique_tasks - webhook_unique_tasks} 个任务已完成但尚未有Webhook回传记录")

cur.close()
conn.close()
