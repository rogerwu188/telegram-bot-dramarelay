#!/usr/bin/env python3
"""
主启动文件 - 同时运行 Telegram Bot 和 API 服务器
"""
import subprocess
import sys
import time
import signal
import os

# 存储子进程
processes = []

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    print("\n🛑 Shutting down services...")
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait()
    print("✅ Services stopped")
    sys.exit(0)

if __name__ == "__main__":
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 60)
    print("X2C Drama Relay - Starting Services")
    print("=" * 60)
    sys.stdout.flush()
    
    # 运行数据库迁移
    print("💾 Running database migrations...")
    sys.stdout.flush()
    try:
        from auto_migrate import auto_migrate
        if auto_migrate():
            print("✅ Database migrations completed successfully")
        else:
            print("⚠️  Warning: Database migrations failed")
    except Exception as e:
        print(f"⚠️  Warning: Failed to run database migrations: {e}")
    sys.stdout.flush()
    
    # 检查并安装 Playwright 浏览器
    print("🔍 Checking Playwright browsers...")
    sys.stdout.flush()
    playwright_cache = os.path.expanduser("~/.cache/ms-playwright/chromium-1091")
    if not os.path.exists(playwright_cache):
        print("📥 Installing Playwright Chromium browser...")
        sys.stdout.flush()
        try:
            subprocess.run(["playwright", "install", "chromium"], check=True)
            subprocess.run(["playwright", "install-deps", "chromium"], check=True)
            print("✅ Playwright browser installed successfully!")
        except Exception as e:
            print(f"⚠️  Warning: Failed to install Playwright browser: {e}")
            print("   Link verification may not work properly.")
        sys.stdout.flush()
    else:
        print("✅ Playwright browser already installed")
        sys.stdout.flush()
    
    try:
        # 启动 API Server
        print("🌐 Starting API Server...")
        sys.stdout.flush()
        api_process = subprocess.Popen(
            [sys.executable, "api_server.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(api_process)
        time.sleep(3)  # 等待 API Server 启动
        
        # 启动 Telegram Bot
        print("🤖 Starting Telegram Bot...")
        sys.stdout.flush()
        bot_process = subprocess.Popen(
            [sys.executable, "bot.py"],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(bot_process)
        
        print("✅ Both services started successfully!")
        print(f"   - API Server (PID: {api_process.pid})")
        print(f"   - Telegram Bot (PID: {bot_process.pid})")
        print("=" * 60)
        sys.stdout.flush()
        
        # 等待任一进程结束
        while True:
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️  Process {p.pid} exited with code {p.returncode}")
                    sys.exit(p.returncode)
            time.sleep(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.stdout.flush()
        for p in processes:
            p.terminate()
        sys.exit(1)
