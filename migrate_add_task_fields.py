#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加任务模板字段的数据库迁移脚本
"""
import os
import psycopg2

def migrate():
    """添加任务模板相关字段"""
    database_url = os.getenv('DATABASE_URL', '')
    
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        print("🔗 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # 检查并添加字段
        fields_to_add = [
            ('video_url', 'TEXT', '任务视频链接'),
            ('task_template', 'TEXT', '任务下发模板'),
            ('keywords_template', 'TEXT', '关键词模板（用于验证）'),
            ('video_title', 'VARCHAR(500)', '视频标题'),
        ]
        
        for field_name, field_type, description in fields_to_add:
            # 检查字段是否存在
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='drama_tasks' AND column_name=%s
            """, (field_name,))
            
            if not cur.fetchone():
                print(f"📝 Adding column '{field_name}' ({description})...")
                cur.execute(f"""
                    ALTER TABLE drama_tasks 
                    ADD COLUMN {field_name} {field_type}
                """)
                conn.commit()
                print(f"✅ Column '{field_name}' added successfully")
            else:
                print(f"ℹ️  Column '{field_name}' already exists")
        
        cur.close()
        conn.close()
        print("✅ Migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    migrate()
