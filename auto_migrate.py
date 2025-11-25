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
        
        # 获取 users 表的所有字段
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        
        existing_columns = [row['column_name'] for row in cur.fetchall()]
        logger.info(f"📋 Existing columns in users table: {existing_columns}")
        
        # 添加 users 表缺失的字段
        user_fields_to_add = [
            ('username', 'TEXT'),
            ('first_name', 'TEXT'),
            ('language', 'VARCHAR(10) DEFAULT \'zh\''),
            ('wallet_address', 'VARCHAR(42)'),
            ('total_node_power', 'INTEGER DEFAULT 0'),
            ('completed_tasks', 'INTEGER DEFAULT 0'),
            ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
        ]
        
        # 逐个检查并添加 users 表缺失的字段
        for column_name, column_def in user_fields_to_add:
            if column_name not in existing_columns:
                logger.info(f"📝 Adding column '{column_name}' to users table...")
                try:
                    cur.execute(f"""
                        ALTER TABLE users 
                        ADD COLUMN {column_name} {column_def}
                    """)
                    conn.commit()
                    logger.info(f"✅ Column '{column_name}' added successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to add column '{column_name}': {e}")
                    conn.rollback()
            else:
                logger.info(f"✅ Column '{column_name}' already exists")
        
        # 添加 drama_tasks 表的新字段
        logger.info("\n📝 Checking drama_tasks table...")
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'drama_tasks'
        """)
        
        existing_task_columns = [row['column_name'] for row in cur.fetchall()]
        logger.info(f"📋 Existing columns in drama_tasks table: {existing_task_columns}")
        
        # 添加任务模板相关字段
        task_fields_to_add = [
            ('video_url', 'TEXT'),
            ('task_template', 'TEXT'),
            ('keywords_template', 'TEXT'),
            ('video_title', 'VARCHAR(500)'),
        ]
        
        for column_name, column_def in task_fields_to_add:
            if column_name not in existing_task_columns:
                logger.info(f"📝 Adding column '{column_name}' to drama_tasks table...")
                try:
                    cur.execute(f"""
                        ALTER TABLE drama_tasks 
                        ADD COLUMN {column_name} {column_def}
                    """)
                    conn.commit()
                    logger.info(f"✅ Column '{column_name}' added successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to add column '{column_name}': {e}")
                    conn.rollback()
            else:
                logger.info(f"✅ Column '{column_name}' already exists")
        
        cur.close()
        conn.close()
        logger.info("\n✅ All migrations completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Auto migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    auto_migrate()
