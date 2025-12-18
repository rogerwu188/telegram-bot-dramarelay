import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# 从.env文件读取DATABASE_URL
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            database_url = line.strip().split('=', 1)[1]
            break

# 解析数据库URL
result = urlparse(database_url)
conn = psycopg2.connect(
    database=result.path[1:],
    user=result.username,
    password=result.password,
    host=result.hostname,
    port=result.port
)
cur = conn.cursor(cursor_factory=RealDictCursor)

# 查询所有表
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name
""")
tables = cur.fetchall()
print("数据库中的表:")
for table in tables:
    print(f"  - {table['table_name']}")

# 检查webhook_logs表是否存在
cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name = 'webhook_logs'
""")
webhook_logs_exists = cur.fetchone()

if webhook_logs_exists:
    print("\n✅ webhook_logs表存在")
    # 查询表结构
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'webhook_logs'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    print("\nwebhook_logs表结构:")
    for col in columns:
        print(f"  - {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']})")
else:
    print("\n❌ webhook_logs表不存在")

cur.close()
conn.close()
