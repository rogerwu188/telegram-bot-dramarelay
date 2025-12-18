#!/usr/bin/env python3
"""检查任务完成日志中的提交链接，删除无法访问的记录"""

import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import time

# PostgreSQL公网连接
DATABASE_URL = "postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway"

# TikTok View Counter API
VIEW_COUNTER_API = "https://tiktok-view-counter-production.up.railway.app/api/analyze"

def check_tiktok_link(url):
    """检查TikTok链接是否可访问"""
    try:
        response = requests.post(
            VIEW_COUNTER_API,
            json={"url": url},
            timeout=30
        )
        data = response.json()
        
        if data.get('success'):
            return True, data.get('view_count', 0)
        else:
            error = data.get('error', 'Unknown error')
            return False, error
    except Exception as e:
        return False, str(e)

def check_youtube_link(url):
    """检查YouTube链接是否可访问（简单HTTP检查）"""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200, response.status_code
    except Exception as e:
        return False, str(e)

def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # 查询所有submitted状态的任务
    print("=" * 60)
    print("1. 查询所有已完成任务的提交链接")
    print("=" * 60)
    
    cur.execute("""
        SELECT 
            ut.id,
            ut.user_id,
            ut.task_id,
            ut.submission_link,
            ut.submitted_at,
            t.title
        FROM user_tasks ut
        LEFT JOIN drama_tasks t ON ut.task_id = t.task_id
        WHERE ut.status = 'submitted' AND ut.submission_link IS NOT NULL
        ORDER BY ut.submitted_at DESC
    """)
    
    tasks = cur.fetchall()
    print(f"共找到 {len(tasks)} 条已完成任务记录")
    
    # 检查每个链接
    print("\n" + "=" * 60)
    print("2. 检查每个链接的可访问性")
    print("=" * 60)
    
    invalid_tasks = []
    valid_tasks = []
    
    for i, task in enumerate(tasks):
        url = task['submission_link']
        task_id = task['task_id']
        title = task['title']
        record_id = task['id']
        
        print(f"\n[{i+1}/{len(tasks)}] 检查: {title}")
        print(f"  链接: {url}")
        
        # 根据链接类型选择检查方法
        if 'tiktok.com' in url:
            is_valid, result = check_tiktok_link(url)
            if is_valid:
                print(f"  ✅ 可访问 (播放量: {result})")
                valid_tasks.append(task)
            else:
                print(f"  ❌ 无法访问: {result}")
                invalid_tasks.append(task)
        elif 'youtube.com' in url or 'youtu.be' in url:
            is_valid, result = check_youtube_link(url)
            if is_valid:
                print(f"  ✅ 可访问")
                valid_tasks.append(task)
            else:
                print(f"  ❌ 无法访问: {result}")
                invalid_tasks.append(task)
        else:
            print(f"  ⚠️ 未知平台，跳过检查")
            valid_tasks.append(task)
        
        # 避免请求过快
        time.sleep(1)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("3. 检查结果汇总")
    print("=" * 60)
    print(f"✅ 有效链接: {len(valid_tasks)}")
    print(f"❌ 无效链接: {len(invalid_tasks)}")
    
    if invalid_tasks:
        print("\n无效链接列表:")
        for task in invalid_tasks:
            print(f"  - ID {task['id']}: {task['title']} - {task['submission_link']}")
        
        # 确认删除
        print("\n" + "=" * 60)
        print("4. 删除无效记录")
        print("=" * 60)
        
        confirm = input(f"确认删除 {len(invalid_tasks)} 条无效记录？(y/n): ")
        if confirm.lower() == 'y':
            for task in invalid_tasks:
                cur.execute("DELETE FROM user_tasks WHERE id = %s", (task['id'],))
                print(f"  已删除: ID {task['id']} - {task['title']}")
            
            conn.commit()
            print(f"\n✅ 已删除 {len(invalid_tasks)} 条无效记录")
        else:
            print("取消删除")
    else:
        print("\n✅ 所有链接都有效，无需删除")
    
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
