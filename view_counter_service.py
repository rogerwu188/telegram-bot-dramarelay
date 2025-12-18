# -*- coding: utf-8 -*-
"""
TikTok 播放量抓取服务
每10分钟自动抓取任务完成日志中所有视频的播放量
使用外部 TikTok View Counter API
"""

import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse
from datetime import datetime
import time
import threading

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Video Analytics API (支持 TikTok 和 YouTube)
VIDEO_ANALYTICS_API_URL = 'https://tiktok-view-counter-production.up.railway.app/api/analyze'

# 数据库连接
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def get_db_connection():
    """获取数据库连接"""
    result = urlparse(DATABASE_URL)
    return psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        cursor_factory=RealDictCursor
    )

def ensure_view_count_columns():
    """确保user_tasks表有view_count和like_count字段"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查并添加view_count字段
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'user_tasks' AND column_name = 'view_count'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE user_tasks ADD COLUMN view_count INTEGER DEFAULT 0")
            logger.info("✅ 已添加 view_count 字段到 user_tasks 表")
        
        # 检查并添加like_count字段
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'user_tasks' AND column_name = 'like_count'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE user_tasks ADD COLUMN like_count INTEGER DEFAULT 0")
            logger.info("✅ 已添加 like_count 字段到 user_tasks 表")
        
        # 检查并添加view_count_updated_at字段
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'user_tasks' AND column_name = 'view_count_updated_at'
        """)
        if not cur.fetchone():
            cur.execute("ALTER TABLE user_tasks ADD COLUMN view_count_updated_at TIMESTAMP")
            logger.info("✅ 已添加 view_count_updated_at 字段到 user_tasks 表")
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ 确保字段存在失败: {e}")
        return False

def ensure_view_count_error_log_table():
    """确保播放量抓取错误日志表存在"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS view_count_error_logs (
                id SERIAL PRIMARY KEY,
                user_task_id INTEGER,
                submission_link TEXT,
                error_type VARCHAR(100),
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("✅ view_count_error_logs 表已就绪")
        return True
    except Exception as e:
        logger.error(f"❌ 创建错误日志表失败: {e}")
        return False

def get_video_stats(video_url):
    """
    调用 Video Analytics API 获取视频统计数据
    支持 TikTok 和 YouTube
    
    Args:
        video_url (str): 视频 URL (TikTok 或 YouTube)
        
    Returns:
        dict: 包含 view_count, like_count, platform 等信息的字典，失败返回 None
    """
    try:
        response = requests.post(
            VIDEO_ANALYTICS_API_URL,
            json={'url': video_url},
            headers={'Content-Type': 'application/json'},
            timeout=60  # 60秒超时
        )
        
        if response.status_code == 200:
            data = response.json()
            platform = data.get('platform', 'unknown')
            logger.info(f"✅ 获取播放量成功 [{platform}]: {video_url} -> 播放量: {data.get('view_count', 0)}, 点赞: {data.get('like_count', 0)}")
            return data
        else:
            error_detail = response.json().get('detail', f'HTTP {response.status_code}')
            logger.warning(f"⚠️ API返回错误: {video_url} -> {error_detail}")
            return {'error': error_detail, 'error_type': 'api_error'}
            
    except requests.exceptions.Timeout:
        logger.warning(f"⚠️ 请求超时: {video_url}")
        return {'error': '请求超时', 'error_type': 'timeout'}
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 请求失败: {video_url} -> {str(e)}")
        return {'error': str(e), 'error_type': 'request_error'}
    except Exception as e:
        logger.error(f"❌ 未知错误: {video_url} -> {str(e)}")
        return {'error': str(e), 'error_type': 'unknown_error'}

def log_view_count_error(user_task_id, submission_link, error_type, error_message):
    """记录播放量抓取错误到数据库"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO view_count_error_logs (user_task_id, submission_link, error_type, error_message)
            VALUES (%s, %s, %s, %s)
        """, (user_task_id, submission_link, error_type, error_message))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ 记录错误日志失败: {e}")

def update_view_count(user_task_id, view_count, like_count):
    """
    增量更新播放量（只有当新值大于旧值时才更新）
    
    Args:
        user_task_id: 用户任务ID
        view_count: 新的播放量
        like_count: 新的点赞数
        
    Returns:
        bool: 是否更新成功
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取当前值
        cur.execute("""
            SELECT view_count, like_count FROM user_tasks WHERE id = %s
        """, (user_task_id,))
        current = cur.fetchone()
        
        if not current:
            cur.close()
            conn.close()
            return False
        
        current_view = current['view_count'] or 0
        current_like = current['like_count'] or 0
        
        # 增量更新：只有新值大于旧值时才更新数值
        new_view = max(view_count, current_view)
        new_like = max(like_count, current_like)
        
        # 无论数值是否变化，都更新时间戳（表示已抓取）
        cur.execute("""
            UPDATE user_tasks 
            SET view_count = %s, like_count = %s, view_count_updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_view, new_like, user_task_id))
        conn.commit()
        
        if new_view > current_view or new_like > current_like:
            logger.info(f"✅ 更新播放量: task_id={user_task_id}, view: {current_view} -> {new_view}, like: {current_like} -> {new_like}")
        else:
            logger.info(f"📊 播放量无变化: task_id={user_task_id}, view={current_view}, like={current_like} (已更新抓取时间)")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ 更新播放量失败: {e}")
        return False

def is_supported_video_url(url):
    """
    检查是否是支持的视频链接（TikTok 或 YouTube）
    
    Args:
        url: 视频链接
        
    Returns:
        tuple: (is_supported: bool, platform: str)
    """
    if not url:
        return False, None
    
    url_lower = url.lower()
    
    if 'tiktok.com' in url_lower:
        return True, 'tiktok'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return True, 'youtube'
    else:
        return False, None

def fetch_all_view_counts():
    """
    抓取所有已完成任务的播放量
    """
    logger.info("🔄 开始抓取所有任务的播放量...")
    
    # 确保表结构正确
    ensure_view_count_columns()
    ensure_view_count_error_log_table()
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取所有已提交的任务（TikTok 和 YouTube）
        cur.execute("""
            SELECT id, submission_link, view_count, like_count
            FROM user_tasks
            WHERE status = 'submitted'
              AND submission_link IS NOT NULL
              AND submission_link != ''
              AND (submission_link LIKE '%tiktok.com%' 
                   OR submission_link LIKE '%youtube.com%' 
                   OR submission_link LIKE '%youtu.be%')
            ORDER BY submitted_at DESC
        """)
        
        tasks = cur.fetchall()
        cur.close()
        conn.close()
        
        logger.info(f"📊 找到 {len(tasks)} 个视频任务需要更新播放量 (TikTok + YouTube)")
        
        success_count = 0
        error_count = 0
        skip_count = 0
        
        for task in tasks:
            task_id = task['id']
            submission_link = task['submission_link']
            
            # 检查是否是支持的视频链接
            is_supported, platform = is_supported_video_url(submission_link)
            if not is_supported:
                skip_count += 1
                continue
            
            # 调用API获取播放量
            result = get_video_stats(submission_link)
            
            if result and 'error' not in result:
                # 成功获取，增量更新
                view_count = result.get('view_count', 0)
                like_count = result.get('like_count', 0)
                
                if update_view_count(task_id, view_count, like_count):
                    success_count += 1
                else:
                    error_count += 1
            else:
                # 失败，记录错误
                error_type = result.get('error_type', 'unknown') if result else 'no_response'
                error_message = result.get('error', '未知错误') if result else '无响应'
                log_view_count_error(task_id, submission_link, error_type, error_message)
                error_count += 1
            
            # 避免请求过于频繁，每个请求间隔1秒
            time.sleep(1)
        
        logger.info(f"✅ 播放量抓取完成: 成功={success_count}, 失败={error_count}, 跳过={skip_count}")
        return {
            'success': True,
            'total': len(tasks),
            'success_count': success_count,
            'error_count': error_count,
            'skip_count': skip_count
        }
        
    except Exception as e:
        logger.error(f"❌ 抓取播放量失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# 定时器相关
_timer_thread = None
_timer_running = False

def start_view_count_timer(interval_minutes=10):
    """
    启动播放量抓取定时器
    
    Args:
        interval_minutes: 抓取间隔（分钟）
    """
    global _timer_thread, _timer_running
    
    if _timer_running:
        logger.warning("⚠️ 定时器已在运行中")
        return False
    
    _timer_running = True
    
    def timer_loop():
        global _timer_running
        while _timer_running:
            try:
                fetch_all_view_counts()
            except Exception as e:
                logger.error(f"❌ 定时任务执行失败: {e}")
            
            # 等待指定时间
            for _ in range(interval_minutes * 60):
                if not _timer_running:
                    break
                time.sleep(1)
    
    _timer_thread = threading.Thread(target=timer_loop, daemon=True)
    _timer_thread.start()
    logger.info(f"✅ 播放量抓取定时器已启动，间隔: {interval_minutes} 分钟")
    return True

def stop_view_count_timer():
    """停止播放量抓取定时器"""
    global _timer_running
    _timer_running = False
    logger.info("⏹️ 播放量抓取定时器已停止")
    return True

def is_timer_running():
    """检查定时器是否在运行"""
    return _timer_running

if __name__ == '__main__':
    # 测试运行
    print("测试播放量抓取服务...")
    result = fetch_all_view_counts()
    print(f"结果: {result}")
