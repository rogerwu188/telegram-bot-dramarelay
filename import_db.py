#!/usr/bin/env python3
"""
导入数据到 Render PostgreSQL 数据库
"""
import os
import psycopg2
import json

def import_database():
    """从 JSON 导入数据"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ 错误：未找到 DATABASE_URL 环境变量")
        print("请设置：export DATABASE_URL='postgresql://...'")
        return
    
    # 读取导出的数据
    input_file = 'railway_db_export.json'
    if not os.path.exists(input_file):
        print(f"❌ 错误：未找到 {input_file}")
        return
    
    print(f"📖 读取导出文件...")
    with open(input_file, 'r', encoding='utf-8') as f:
        export_data = json.load(f)
    
    print(f"🔗 连接数据库...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # 导入 users 表
    if 'users' in export_data['tables']:
        print("📋 导入 users 表...")
        table_data = export_data['tables']['users']
        columns = table_data['columns']
        rows = table_data['rows']
        
        for row in rows:
            placeholders = ','.join(['%s'] * len(row))
            cols = ','.join(columns)
            query = f"INSERT INTO users ({cols}) VALUES ({placeholders}) ON CONFLICT (user_id) DO NOTHING"
            cursor.execute(query, row)
        
        conn.commit()
        print(f"   ✅ 导入 {len(rows)} 条用户记录")
    
    # 导入 drama_tasks 表
    if 'drama_tasks' in export_data['tables']:
        print("📋 导入 drama_tasks 表...")
        table_data = export_data['tables']['drama_tasks']
        columns = table_data['columns']
        rows = table_data['rows']
        
        for row in rows:
            placeholders = ','.join(['%s'] * len(row))
            cols = ','.join(columns)
            query = f"INSERT INTO drama_tasks ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            cursor.execute(query, row)
        
        conn.commit()
        print(f"   ✅ 导入 {len(rows)} 条任务记录")
    
    # 导入 task_submissions 表
    if 'task_submissions' in export_data['tables']:
        print("📋 导入 task_submissions 表...")
        table_data = export_data['tables']['task_submissions']
        columns = table_data['columns']
        rows = table_data['rows']
        
        for row in rows:
            placeholders = ','.join(['%s'] * len(row))
            cols = ','.join(columns)
            query = f"INSERT INTO task_submissions ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
            cursor.execute(query, row)
        
        conn.commit()
        print(f"   ✅ 导入 {len(rows)} 条提交记录")
    
    print(f"\n✅ 数据导入完成！")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    import_database()
