#!/usr/bin/env python3
"""
自动数据库 migration 脚本
在 bot 启动时运行，确保数据库结构正确
"""
import os
import pymysql.cursors
import logging

logger = logging.getLogger(__name__)

def auto_migrate():
    """自动运行数据库迁移"""
    try:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.error("❌ DATABASE_URL not found")
            return False
        
        # 解析 DATABASE_URL
        import re
        match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if not match:
            logger.error("❌ Invalid DATABASE_URL format")
            return False
        
        user, password, host, port, database = match.groups()
        
        logger.info(f"🔗 Connecting to database: {host}:{port}/{database}")
        
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
        
        # 检查并添加 total_node_power 字段
        cur.execute("DESCRIBE users")
        columns = [col['Field'] for col in cur.fetchall()]
        
        if 'total_node_power' not in columns:
            logger.info("📝 Adding column 'total_node_power' to users table...")
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN total_node_power INTEGER DEFAULT 0
            """)
            conn.commit()
            logger.info("✅ Column 'total_node_power' added successfully")
        else:
            logger.info("✅ Column 'total_node_power' already exists")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Auto migration failed: {e}")
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    auto_migrate()
