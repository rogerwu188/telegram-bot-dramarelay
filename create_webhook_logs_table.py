#!/usr/bin/env python3
"""
一次性脚本：创建webhook_logs表
"""
import os
import psycopg2
from urllib.parse import urlparse

def create_webhook_logs_table():
    """创建webhook_logs表"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL 未设置")
            return False
        
        # 解析数据库URL
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cur = conn.cursor()
        
        # 检查表是否已存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'webhook_logs'
            )
        """)
        
        exists = cur.fetchone()[0]
        
        if exists:
            print("✅ webhook_logs表已存在")
            cur.close()
            conn.close()
            return True
        
        print("📝 创建webhook_logs表...")
        
        # 创建表
        cur.execute("""
            CREATE TABLE webhook_logs (
                id SERIAL PRIMARY KEY,
                task_id INTEGER,
                task_title VARCHAR(500),
                project_id VARCHAR(100),
                callback_url TEXT,
                callback_status VARCHAR(50) DEFAULT 'success',
                payload JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cur.execute("""
            CREATE INDEX idx_webhook_logs_task_id ON webhook_logs(task_id);
        """)
        cur.execute("""
            CREATE INDEX idx_webhook_logs_created_at ON webhook_logs(created_at);
        """)
        cur.execute("""
            CREATE INDEX idx_webhook_logs_callback_status ON webhook_logs(callback_status);
        """)
        cur.execute("""
            CREATE INDEX idx_webhook_logs_project_id ON webhook_logs(project_id);
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ webhook_logs表创建成功！")
        return True
        
    except Exception as e:
        print(f"❌ 创建webhook_logs表失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    create_webhook_logs_table()
