import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('POSTGRES_URL')
if not DATABASE_URL:
    print("ERROR: No DATABASE_URL found")
    exit(1)

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
cur = conn.cursor()

print("=== bot_settings 表内容 ===")
try:
    cur.execute("SELECT * FROM bot_settings ORDER BY key")
    rows = cur.fetchall()
    for row in rows:
        print(f"  {row['key']}: {row['value']} (updated: {row.get('updated_at', 'N/A')})")
except Exception as e:
    print(f"  Error: {e}")

cur.close()
conn.close()
