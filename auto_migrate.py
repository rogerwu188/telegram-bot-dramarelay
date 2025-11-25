#!/usr/bin/env python3
"""
自动数据库 migration 脚本
在 bot 启动时运行，确保数据库结构正确
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

def auto_migrate():
    """自动运行数据库迁移"""
    try:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            logger.error("❌ DATABASE_URL not found")
            return False
        
        logger.info(f"🔗 Connecting to database...")
        
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # 检查 total_node_power 字段是否存在
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'total_node_power'
        """)
        
        column_exists = cur.fetchone()
        
        if not column_exists:
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
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    auto_migrate()
