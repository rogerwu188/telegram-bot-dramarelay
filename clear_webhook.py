#!/usr/bin/env python3
"""
清除 Telegram Bot Webhook 配置
用于解决 Polling 模式下的 Conflict 错误
"""
import os
import requests
import sys

# 从环境变量获取 Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN') or '8580007118:AAfmA9OlAT1iD_XzUnKGL-0qU_FPK7G6uwyQ'

def clear_webhook():
    """清除 Webhook 配置"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    print("🔧 正在清除 Telegram Webhook 配置...")
    print(f"📡 API URL: {url}")
    
    try:
        # 发送请求删除 Webhook
        response = requests.post(url, params={'drop_pending_updates': True})
        result = response.json()
        
        print(f"\n📥 响应状态码: {response.status_code}")
        print(f"📄 响应内容: {result}")
        
        if result.get('ok'):
            print("\n✅ Webhook 已成功清除!")
            print("   现在可以使用 Polling 模式了。")
            return True
        else:
            print(f"\n❌ 清除失败: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False

def get_webhook_info():
    """获取当前 Webhook 配置信息"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    print("\n🔍 查询当前 Webhook 配置...")
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if result.get('ok'):
            info = result.get('result', {})
            print(f"\n📋 Webhook 信息:")
            print(f"   URL: {info.get('url') or '(未设置)'}")
            print(f"   Pending Updates: {info.get('pending_update_count', 0)}")
            print(f"   Last Error: {info.get('last_error_message') or '(无)'}")
            print(f"   Max Connections: {info.get('max_connections', 0)}")
            return info
        else:
            print(f"❌ 查询失败: {result.get('description')}")
            return None
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

def get_me():
    """测试 Bot Token 是否有效"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
    
    print("\n🤖 测试 Bot Token...")
    
    try:
        response = requests.get(url)
        result = response.json()
        
        if result.get('ok'):
            bot_info = result.get('result', {})
            print(f"\n✅ Bot Token 有效!")
            print(f"   Bot ID: {bot_info.get('id')}")
            print(f"   Bot Name: {bot_info.get('first_name')}")
            print(f"   Username: @{bot_info.get('username')}")
            return True
        else:
            print(f"\n❌ Token 无效: {result.get('description')}")
            return False
            
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Telegram Bot Webhook 清除工具")
    print("=" * 60)
    
    # 1. 测试 Token
    if not get_me():
        print("\n❌ Bot Token 无效，请检查环境变量 BOT_TOKEN")
        sys.exit(1)
    
    # 2. 查看当前 Webhook 配置
    webhook_info = get_webhook_info()
    
    # 3. 清除 Webhook
    if clear_webhook():
        print("\n" + "=" * 60)
        print("✅ 操作完成！现在可以重启 Bot 使用 Polling 模式了。")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("❌ 操作失败，请检查错误信息。")
        print("=" * 60)
        sys.exit(1)
