#!/usr/bin/env python3
"""
数据库 migration 脚本
添加 total_node_power 字段到 users 表
"""
import os
import pymysql.cursors

def migrate():
    db_url = os.getenv('DATABASE_URL', 'mysql://root:OBPpGxLjNGFUjlEHPWJZTNdNbfcQXHjD@junction.proxy.rlwy.net:51984/railway')
    
    # 解析 DATABASE_URL
    import re
    match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if not match:
        print("❌ Invalid DATABASE_URL format")
        return
    
    user, password, host, port, database = match.groups()
    
    print(f"🔗 Connecting to database: {host}:{port}/{database}")
    
    # 提取 SSL 参数
    ssl_config = None
    if '?' in database:
        database, params = database.split('?', 1)
        if 'ssl=' in params:
            ssl_config = {'ca': None}  # 使用默认 CA
    
    conn = pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        ssl=ssl_config
    )
    
    cur = conn.cursor()
    
    try:
        # 检查表是否存在
        cur.execute("SHOW TABLES LIKE 'users'")
        table_exists = cur.fetchone()
        
        if not table_exists:
            print("📝 Creating users table...")
            cur.execute("""
                CREATE TABLE users (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    language VARCHAR(10) DEFAULT 'zh',
                    wallet_address VARCHAR(42),
                    total_node_power INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            print("✅ Users table created successfully")
        else:
            # 检查字段是否已存在
            cur.execute("DESCRIBE users")
            columns = [col['Field'] for col in cur.fetchall()]
            
            if 'total_node_power' in columns:
                print("✅ Column 'total_node_power' already exists")
            else:
                print("📝 Adding column 'total_node_power' to users table...")
                cur.execute("""
                    ALTER TABLE users 
                    ADD COLUMN total_node_power INTEGER DEFAULT 0
                """)
                conn.commit()
                print("✅ Column 'total_node_power' added successfully")
        
        # 验证
        cur.execute("DESCRIBE users")
        columns = cur.fetchall()
        print("\n📊 Current users table structure:")
        for col in columns:
            print(f"  {col['Field']}: {col['Type']}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    migrate()
