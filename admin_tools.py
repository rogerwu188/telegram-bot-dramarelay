#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2C DramaRelayBot - 管理员工具
用于添加任务、管理用户等
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 数据库连接
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def add_demo_task():
    """添加演示任务"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 添加几个演示任务
    demo_tasks = [
        {
            'title': '霸道总裁爱上我 EP01',
            'description': '都市爱情短剧第一集，讲述霸道总裁与灰姑娘的浪漫邂逅',
            'duration': 15,
            'reward': 10,
            'platforms': 'TikTok,YouTube,Instagram'
        },
        {
            'title': '穿越之王妃驾到 EP01',
            'description': '古装穿越剧，现代女孩穿越成为古代王妃',
            'duration': 20,
            'reward': 15,
            'platforms': 'TikTok,YouTube,Instagram,Facebook'
        },
        {
            'title': '重生之商业帝国 EP01',
            'description': '商战题材，主角重生回到创业初期',
            'duration': 18,
            'reward': 12,
            'platforms': 'TikTok,YouTube,Instagram'
        },
        {
            'title': '都市修仙传 EP01',
            'description': '现代修仙题材，都市中的修仙者',
            'duration': 25,
            'reward': 20,
            'platforms': 'TikTok,YouTube,Instagram,Twitter'
        },
        {
            'title': '豪门千金的复仇 EP01',
            'description': '豪门恩怨，千金小姐的复仇之路',
            'duration': 16,
            'reward': 10,
            'platforms': 'TikTok,YouTube,Instagram'
        }
    ]
    
    for task in demo_tasks:
        try:
            cur.execute("""
                INSERT INTO drama_tasks 
                (title, description, duration, node_power_reward, platform_requirements, status)
                VALUES (%s, %s, %s, %s, %s, 'active')
                ON CONFLICT DO NOTHING
            """, (
                task['title'],
                task['description'],
                task['duration'],
                task['reward'],
                task['platforms']
            ))
            print(f"✅ 添加任务: {task['title']}")
        except Exception as e:
            print(f"❌ 添加任务失败: {task['title']} - {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print("\n✅ 演示任务添加完成！")

def list_all_tasks():
    """列出所有任务"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM drama_tasks ORDER BY created_at DESC")
    tasks = cur.fetchall()
    
    print("\n📋 所有任务列表：")
    print("-" * 80)
    
    for task in tasks:
        print(f"ID: {task['task_id']}")
        print(f"标题: {task['title']}")
        print(f"描述: {task['description']}")
        print(f"时长: {task['duration']}秒")
        print(f"奖励: {task['node_power_reward']} NP")
        print(f"平台: {task['platform_requirements']}")
        print(f"状态: {task['status']}")
        print(f"创建时间: {task['created_at']}")
        print("-" * 80)
    
    cur.close()
    conn.close()

def list_all_users():
    """列出所有用户"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_id, username, first_name, total_node_power, 
               completed_tasks, wallet_address, created_at
        FROM users 
        ORDER BY total_node_power DESC
    """)
    users = cur.fetchall()
    
    print("\n👥 所有用户列表：")
    print("-" * 80)
    
    for user in users:
        print(f"User ID: {user['user_id']}")
        print(f"用户名: @{user['username'] or 'N/A'}")
        print(f"名字: {user['first_name'] or 'N/A'}")
        print(f"总算力: {user['total_node_power']} NP")
        print(f"完成任务: {user['completed_tasks']}")
        print(f"钱包: {user['wallet_address'] or '未绑定'}")
        print(f"注册时间: {user['created_at']}")
        print("-" * 80)
    
    cur.close()
    conn.close()

def list_all_submissions():
    """列出所有提交"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT ut.*, u.username, u.first_name, dt.title
        FROM user_tasks ut
        JOIN users u ON ut.user_id = u.user_id
        JOIN drama_tasks dt ON ut.task_id = dt.task_id
        ORDER BY ut.created_at DESC
    """)
    submissions = cur.fetchall()
    
    print("\n📤 所有提交记录：")
    print("-" * 80)
    
    for sub in submissions:
        print(f"提交 ID: {sub['id']}")
        print(f"用户: {sub['first_name']} (@{sub['username'] or 'N/A'})")
        print(f"任务: {sub['title']}")
        print(f"平台: {sub['platform'] or '未提交'}")
        print(f"链接: {sub['submission_link'] or '未提交'}")
        print(f"状态: {sub['status']}")
        print(f"获得算力: {sub['node_power_earned']} NP")
        print(f"提交时间: {sub['submitted_at'] or '未提交'}")
        print("-" * 80)
    
    cur.close()
    conn.close()

def get_statistics():
    """获取统计信息"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 总用户数
    cur.execute("SELECT COUNT(*) as count FROM users")
    total_users = cur.fetchone()['count']
    
    # 总任务数
    cur.execute("SELECT COUNT(*) as count FROM drama_tasks WHERE status = 'active'")
    total_tasks = cur.fetchone()['count']
    
    # 总提交数
    cur.execute("SELECT COUNT(*) as count FROM user_tasks WHERE status = 'submitted'")
    total_submissions = cur.fetchone()['count']
    
    # 总算力
    cur.execute("SELECT SUM(total_node_power) as total FROM users")
    total_power = cur.fetchone()['total'] or 0
    
    print("\n📊 系统统计：")
    print("=" * 80)
    print(f"👥 总用户数: {total_users}")
    print(f"🎬 活跃任务数: {total_tasks}")
    print(f"📤 总提交数: {total_submissions}")
    print(f"💰 总算力: {total_power} NP")
    print("=" * 80)
    
    cur.close()
    conn.close()

def main():
    """主菜单"""
    print("\n" + "=" * 80)
    print("X2C DramaRelayBot - 管理员工具")
    print("=" * 80)
    
    while True:
        print("\n请选择操作：")
        print("1. 添加演示任务")
        print("2. 列出所有任务")
        print("3. 列出所有用户")
        print("4. 列出所有提交")
        print("5. 查看统计信息")
        print("0. 退出")
        
        choice = input("\n输入选项: ").strip()
        
        if choice == '1':
            add_demo_task()
        elif choice == '2':
            list_all_tasks()
        elif choice == '3':
            list_all_users()
        elif choice == '4':
            list_all_submissions()
        elif choice == '5':
            get_statistics()
        elif choice == '0':
            print("\n👋 再见！")
            break
        else:
            print("❌ 无效选项，请重新选择")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 再见！")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
