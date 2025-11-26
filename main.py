#!/usr/bin/env python3
"""
主启动文件 - 同时运行 Telegram Bot 和 API 服务器
使用线程而不是进程，以确保在容器环境中正常工作
"""
import threading
import sys
import os
import time

def run_bot():
    """运行 Telegram Bot"""
    print("🤖 Starting Telegram Bot...")
    sys.stdout.flush()
    import bot
    # bot.py 会自动运行

def run_api():
    """运行 API 服务器"""
    print("🌐 Starting API Server...")
    sys.stdout.flush()
    import api_server
    # api_server.py 会自动运行

if __name__ == "__main__":
    print("=" * 60)
    print("X2C Drama Relay - Starting Services")
    print("=" * 60)
    sys.stdout.flush()
    
    # 创建两个线程
    api_thread = threading.Thread(target=run_api, name="APIServer", daemon=True)
    bot_thread = threading.Thread(target=run_bot, name="TelegramBot", daemon=False)
    
    try:
        # 先启动 API Server
        api_thread.start()
        time.sleep(2)  # 等待 API Server 启动
        
        # 再启动 Bot
        bot_thread.start()
        
        print("✅ Both services started successfully!")
        print("   - API Server (Thread: {})".format(api_thread.name))
        print("   - Telegram Bot (Thread: {})".format(bot_thread.name))
        print("=" * 60)
        sys.stdout.flush()
        
        # 等待 Bot 线程结束（主线程）
        bot_thread.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        sys.stdout.flush()
        print("✅ Services stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.stdout.flush()
        sys.exit(1)
