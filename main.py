#!/usr/bin/env python3
"""
主启动文件 - 同时运行 Telegram Bot 和 API 服务器
"""
import multiprocessing
import sys
import os

def run_bot():
    """运行 Telegram Bot"""
    print("🤖 Starting Telegram Bot...")
    os.system("python3 bot.py")

def run_api():
    """运行 API 服务器"""
    print("🌐 Starting API Server...")
    os.system("python3 api_server.py")

if __name__ == "__main__":
    # 创建两个进程
    bot_process = multiprocessing.Process(target=run_bot, name="TelegramBot")
    api_process = multiprocessing.Process(target=run_api, name="APIServer")
    
    try:
        # 启动进程
        bot_process.start()
        api_process.start()
        
        print("✅ Both services started successfully!")
        print("   - Telegram Bot (PID: {})".format(bot_process.pid))
        print("   - API Server (PID: {})".format(api_process.pid))
        
        # 等待进程结束
        bot_process.join()
        api_process.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        bot_process.terminate()
        api_process.terminate()
        bot_process.join()
        api_process.join()
        print("✅ Services stopped")
        sys.exit(0)
