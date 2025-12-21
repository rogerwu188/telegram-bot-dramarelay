import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

task_ids = [320, 321, 387]

print("检查缺失 webhook 记录的任务")
print("=" * 70)

for task_id in task_ids:
    print(f"\n【任务 {task_id}】")
    print("-" * 50)
    
    # 查询任务信息
    cur.execute("""
        SELECT task_id, title, callback_url, external_task_id, project_id
        FROM drama_tasks 
        WHERE task_id = %s
    """, (task_id,))
    task = cur.fetchone()
    if task:
        print(f"标题: {task['title']}")
        print(f"external_task_id: {task['external_task_id']}")
        print(f"project_id: {task['project_id']}")
        print(f"callback_url: {task['callback_url']}")
    
    # 查询用户提交记录
    cur.execute("""
        SELECT user_id, status, submission_link, submitted_at
        FROM user_tasks
        WHERE task_id = %s AND status = 'submitted'
    """, (task_id,))
    submissions = cur.fetchall()
    print(f"\n用户提交记录 ({len(submissions)} 条):")
    for sub in submissions:
        print(f"  - user_id={sub['user_id']}, submitted_at={sub['submitted_at']}")
        
    # 检查是否在最近7天内
    cur.execute("""
        SELECT submitted_at,
               submitted_at >= NOW() - INTERVAL '7 days' as within_7_days,
               NOW() as current_time
        FROM user_tasks
        WHERE task_id = %s AND status = 'submitted'
        LIMIT 1
    """, (task_id,))
    time_check = cur.fetchone()
    if time_check:
        print(f"\n时间检查:")
        print(f"  提交时间: {time_check['submitted_at']}")
        print(f"  当前时间: {time_check['current_time']}")
        print(f"  在最近7天内: {time_check['within_7_days']}")
    
    # 检查是否有 webhook 记录
    cur.execute("""
        SELECT COUNT(*) as count FROM webhook_logs WHERE task_id = %s
    """, (task_id,))
    webhook_count = cur.fetchone()['count']
    print(f"\nWebhook 记录数: {webhook_count}")
    
    # 检查是否有错误记录
    cur.execute("""
        SELECT error_type, error_message, created_at 
        FROM broadcaster_error_logs 
        WHERE task_id = %s
        ORDER BY created_at DESC
        LIMIT 3
    """, (task_id,))
    errors = cur.fetchall()
    if errors:
        print(f"\n错误记录 ({len(errors)} 条):")
        for err in errors:
            print(f"  - {err['error_type']}: {err['error_message'][:50]}... ({err['created_at']})")
    else:
        print(f"\n错误记录: 无")

cur.close()
conn.close()
