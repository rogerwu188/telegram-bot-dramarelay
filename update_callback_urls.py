import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'
CALLBACK_URL = 'https://eumfmgwxwjyagsvqloac.supabase.co/functions/v1/distribution-callback'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

task_ids = [320, 321, 387]

print("更新任务的 callback_url")
print("=" * 60)

for task_id in task_ids:
    # 先查询当前状态
    cur.execute("SELECT task_id, title, callback_url FROM drama_tasks WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    if task:
        print(f"\n任务 {task_id}: {task['title']}")
        print(f"  原 callback_url: {task['callback_url'] or '(空)'}")
        
        # 更新 callback_url
        cur.execute("""
            UPDATE drama_tasks 
            SET callback_url = %s 
            WHERE task_id = %s
        """, (CALLBACK_URL, task_id))
        
        print(f"  新 callback_url: {CALLBACK_URL}")
    else:
        print(f"\n任务 {task_id}: 未找到")

conn.commit()
print("\n" + "=" * 60)
print("✅ 更新完成！")

# 验证更新
print("\n验证更新结果:")
for task_id in task_ids:
    cur.execute("SELECT task_id, title, callback_url FROM drama_tasks WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    if task:
        status = "✅" if task['callback_url'] == CALLBACK_URL else "❌"
        print(f"  {status} 任务 {task_id}: callback_url = {task['callback_url'][:50]}...")

cur.close()
conn.close()
