#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DramaRelay Bot API 测试脚本
测试任务创建和回调功能
"""

import requests
import json
from datetime import datetime

# API 配置
API_BASE_URL = "https://web-production-b95cb.up.railway.app"
API_KEY = "x2c_admin_secret_key_2024"

# 测试用的 Webhook 接收地址
WEBHOOK_URL = "https://webhook.site/3bf99f67-9734-4a77-a976-ce59e51db9bd"

def test_create_task():
    """测试创建任务"""
    print("=" * 60)
    print("测试 1: 创建任务")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/api/tasks"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    
    # 任务数据
    task_data = {
        "project_id": f"test-project-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "task_id": 3001,
        "title": "【API测试】霸道总裁爱上我 第1集",
        "description": "这是一个通过API创建的测试任务，用于验证接口功能。",
        "video_url": "https://jfs.arkfs.co/soft-dl/video/adoptive-mother-surpasses-birth-mother/v1/clips/ep01-4-41s-49s-%E8%8B%B1%E9%9B%84%E6%95%91%E7%BE%8E.mp4",
        "duration": 30,
        "node_power_reward": 10,
        "platform_requirements": "YouTube,TikTok",
        "status": "active",
        "callback_url": WEBHOOK_URL,
        "callback_secret": "test_secret_2024"
    }
    
    print(f"\n📤 发送请求到: {url}")
    print(f"🔑 API Key: {API_KEY}")
    print(f"\n📦 请求数据:")
    print(json.dumps(task_data, indent=2, ensure_ascii=False))
    
    try:
        response = requests.post(url, headers=headers, json=task_data, timeout=10)
        
        print(f"\n📥 响应状态码: {response.status_code}")
        print(f"📥 响应内容:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200 and response.json().get('success'):
            print("\n✅ 任务创建成功!")
            return response.json()
        else:
            print("\n❌ 任务创建失败!")
            return None
            
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return None

def test_get_tasks():
    """测试获取任务列表"""
    print("\n" + "=" * 60)
    print("测试 2: 获取任务列表")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/api/tasks"
    headers = {
        "X-API-Key": API_KEY
    }
    
    print(f"\n📤 发送请求到: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"\n📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            tasks = response.json()
            print(f"\n✅ 获取成功! 共 {len(tasks)} 个任务")
            print(f"\n前 3 个任务:")
            for task in tasks[:3]:
                print(f"  - Task ID: {task.get('task_id')}, Title: {task.get('title')}")
            return tasks
        else:
            print(f"\n❌ 获取失败!")
            print(response.text)
            return None
            
    except Exception as e:
        print(f"\n❌ 请求失败: {e}")
        return None

def test_api_key_validation():
    """测试 API Key 验证"""
    print("\n" + "=" * 60)
    print("测试 3: API Key 验证")
    print("=" * 60)
    
    url = f"{API_BASE_URL}/api/tasks"
    
    # 测试无效的 API Key
    print("\n📤 测试无效的 API Key...")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": "invalid_key"
    }
    
    try:
        response = requests.post(url, headers=headers, json={}, timeout=10)
        print(f"📥 响应状态码: {response.status_code}")
        print(f"📥 响应内容: {response.json()}")
        
        if response.status_code == 401 or not response.json().get('success'):
            print("✅ API Key 验证正常工作!")
        else:
            print("❌ API Key 验证可能有问题!")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("DramaRelay Bot API 测试")
    print("🚀" * 30)
    
    # 测试 1: 创建任务
    result = test_create_task()
    
    # 测试 2: 获取任务列表
    test_get_tasks()
    
    # 测试 3: API Key 验证
    test_api_key_validation()
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    
    if result:
        print(f"\n💡 提示: 任务已创建，可以在 Telegram Bot 中查看")
        print(f"   Project ID: {result.get('project_id')}")
        print(f"   Task ID: {result.get('task_id')}")
        print(f"\n💡 完成任务后，可以在以下地址查看回调:")
        print(f"   {WEBHOOK_URL}")

if __name__ == "__main__":
    main()
