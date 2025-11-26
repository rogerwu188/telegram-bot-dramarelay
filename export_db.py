#!/usr/bin/env python3
"""
导出 Railway PostgreSQL 数据库
"""
import os
import psycopg2
import json
from datetime import datetime

def export_database():
    """导出所有表数据为 JSON"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ 错误：未找到 DATABASE_URL 环境变量")
        print("请设置：export DATABASE_URL='postgresql://...'")
        return
    
    print(f"🔗 连接数据库...")
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # 导出数据
    export_data = {
        'exported_at': datetime.now().isoformat(),
        'tables': {}
    }
    
    # 导出 users 表
    print("📋 导出 users 表...")
    cursor.execute("SELECT * FROM users")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    export_data['tables']['users'] = {
        'columns': columns,
        'rows': [list(row) for row in rows]
    }
    print(f"   ✅ 导出 {len(rows)} 条用户记录")
    
    # 导出 drama_tasks 表
    print("📋 导出 drama_tasks 表...")
    cursor.execute("SELECT * FROM drama_tasks")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    export_data['tables']['drama_tasks'] = {
        'columns': columns,
        'rows': [list(row) for row in rows]
    }
    print(f"   ✅ 导出 {len(rows)} 条任务记录")
    
    # 导出 task_submissions 表
    print("📋 导出 task_submissions 表...")
    cursor.execute("SELECT * FROM task_submissions")
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    
    export_data['tables']['task_submissions'] = {
        'columns': columns,
        'rows': [list(row) for row in rows]
    }
    print(f"   ✅ 导出 {len(rows)} 条提交记录")
    
    # 保存为 JSON
    output_file = 'railway_db_export.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 数据导出完成！")
    print(f"📄 文件：{output_file}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    export_database()
