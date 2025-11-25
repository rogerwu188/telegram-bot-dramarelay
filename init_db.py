#!/usr/bin/env python3
"""
完整的数据库初始化脚本
创建所有必要的表
"""
import os
import pymysql.cursors

def init_database():
    db_url = os.getenv('DATABASE_URL', 'mysql://root:OBPpGxLjNGFUjlEHPWJZTNdNbfcQXHjD@junction.proxy.rlwy.net:51984/railway')
    
    # 解析 DATABASE_URL
    import re
    match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
    if not match:
        print("❌ Invalid DATABASE_URL format")
        return
    
    user, password, host, port, database = match.groups()
    
    # 提取 SSL 参数
    ssl_config = None
    if '?' in database:
        database, params = database.split('?', 1)
        if 'ssl=' in params:
            ssl_config = {'ca': None}
    
    print(f"🔗 Connecting to database: {host}:{port}/{database}")
    
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
        # 用户表
        print("📝 Creating users table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
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
        
        # 短剧任务表
        print("📝 Creating drama_tasks table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS drama_tasks (
                task_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                video_file_id TEXT,
                thumbnail_url TEXT,
                duration INTEGER DEFAULT 15,
                node_power_reward INTEGER DEFAULT 10,
                platform_requirements VARCHAR(500) DEFAULT 'TikTok,YouTube,Instagram',
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 用户任务关联表
        print("📝 Creating user_tasks table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                task_id INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'in_progress',
                platform VARCHAR(50),
                submission_link TEXT,
                submitted_at TIMESTAMP,
                verified_at TIMESTAMP,
                node_power_earned INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id)
            )
        """)
        
        # 空投快照表
        print("📝 Creating airdrop_snapshots table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS airdrop_snapshots (
                id INT AUTO_INCREMENT PRIMARY KEY,
                round_number INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                node_power INTEGER NOT NULL,
                user_rank INTEGER,
                estimated_airdrop DECIMAL(18, 6),
                snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        conn.commit()
        print("✅ All tables created successfully")
        
        # 验证
        cur.execute("SHOW TABLES")
        tables = cur.fetchall()
        print("\n📊 Current database tables:")
        for table in tables:
            table_name = list(table.values())[0]
            print(f"  ✓ {table_name}")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    init_database()
