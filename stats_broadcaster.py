#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分发数据回传服务
每隔3分钟自动回传所有下发任务的播放量数据到X2C Pool
"""

import os
import asyncio
import logging
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DATABASE_URL = os.getenv('DATABASE_URL')

# 全局状态
broadcaster_running = False
broadcaster_task = None

def log_webhook_success(task_id, task_title, project_id, callback_url, payload):
    """
    记录成功的webhook日志
    """
    try:
        import json
        
        # 使用统一的数据库连接函数
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 记录到webhook_logs表
        cur.execute("""
            INSERT INTO webhook_logs 
            (task_id, task_title, project_id, callback_url, callback_status, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (task_id, task_title, project_id, callback_url, 'success', json.dumps(payload, ensure_ascii=False)))
        
        conn.commit()
        
        # 验证是否插入成功
        cur.execute("SELECT COUNT(*) as total FROM webhook_logs WHERE task_id = %s", (task_id,))
        count = cur.fetchone()['total']
        
        cur.close()
        conn.close()
        
        logger.info(f"✅ 记录webhook成功日志: 任务 {task_id}, 表中该任务记录数: {count}")
    except Exception as e:
        logger.error(f"❌ 记录webhook成功日志失败: {e}")
        import traceback
        traceback.print_exc()

def log_broadcaster_error(task_id, task_title, project_id, video_url, platform, error_type, error_message, callback_url):
    """
    记录回传错误日志
    """
    try:
        # 使用统一的数据库连接函数
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO broadcaster_error_logs 
            (task_id, task_title, project_id, video_url, platform, error_type, error_message, callback_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (task_id, task_title, project_id, video_url, platform, error_type, error_message, callback_url))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"📝 已记录任务 {task_id} 的错误日志")
        
    except Exception as e:
        logger.error(f"❌ 记录错误日志失败: {e}")

def get_db_connection():
    """获取数据库连接"""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # 直接使用DATABASE_URL连接，保留所有连接参数（如SSL等）
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

async def fetch_task_stats(task_id: int, video_url: str, platform: str):
    """
    获取任务的视频统计数据
    
    Args:
        task_id: 任务ID
        video_url: 视频链接
        platform: 平台类型
        
    Returns:
        dict: 视频统计数据
    """
    try:
        from video_stats_fetcher import VideoStatsFetcher
        fetcher = VideoStatsFetcher()
        stats = await fetcher.fetch_video_stats(video_url, platform)
        
        if stats:
            logger.info(f"✅ 任务 {task_id} 数据抓取成功: {stats}")
            return stats
        else:
            logger.warning(f"⚠️ 任务 {task_id} 数据抓取失败")
            return None
            
    except Exception as e:
        logger.error(f"❌ 任务 {task_id} 数据抓取异常: {e}")
        return None

async def broadcast_task_stats(task):
    """
    回传单个任务的统计数据
    
    Args:
        task: 任务信息字典
        
    Returns:
        bool: 是否成功
    """
    try:
        from webhook_notifier import send_webhook
        task_id = task['task_id']
        external_task_id = task['external_task_id']
        project_id = task['project_id']
        callback_url = task['callback_url']
        callback_secret = task['callback_secret']
        video_url = task['video_url']
        duration = task['duration']
        
        # 检查必要字段
        if not callback_url:
            logger.warning(f"⚠️ 任务 {task_id} 没有配置 callback_url，跳过")
            return False
        
        if not video_url:
            logger.warning(f"⚠️ 任务 {task_id} 没有视频链接，跳过")
            return False
        
        # 判断平台类型
        platform = 'youtube'  # 默认YouTube
        if 'tiktok.com' in video_url or 'vm.tiktok.com' in video_url:
            platform = 'tiktok'
        elif 'douyin.com' in video_url or 'v.douyin.com' in video_url:
            platform = 'douyin'
        
        # 抓取视频数据
        stats = await fetch_task_stats(task_id, video_url, platform)
        
        if not stats:
            logger.warning(f"⚠️ 任务 {task_id} 无法获取视频数据，使用默认值")
            # 记录视频抓取失败的错误日志
            log_broadcaster_error(
                task_id=task_id,
                task_title=task.get('title', ''),
                project_id=task.get('project_id', ''),
                video_url=video_url,
                platform=platform,
                error_type='VIDEO_FETCH_FAILED',
                error_message=f'无法从{platform}平台获取视频统计数据',
                callback_url=callback_url
            )
            stats = {}
        
        # 构建回传数据
        stats_data = {
            'project_id': project_id,
            'task_id': external_task_id,
            'duration': duration,
            'account_count': 0  # 分发数据回传不统计账号数
        }
        
        # 提取数据
        view_count = stats.get('views') or stats.get('view_count', 0)
        like_count = stats.get('likes') or stats.get('like_count', 0)
        
        # 添加总播放量和总点赞数（X2C Pool要求）
        if view_count > 0:
            stats_data['view_count'] = view_count
        if like_count > 0:
            stats_data['like_count'] = like_count
        
        # 根据平台填充字段（抖音计入yt_*）
        if platform == 'youtube' or platform == 'douyin':
            if view_count > 0:
                stats_data['yt_view_count'] = view_count
            if like_count > 0:
                stats_data['yt_like_count'] = like_count
            if view_count > 0 or like_count > 0:
                stats_data['yt_account_count'] = 0  # 分发数据不统计账号
        elif platform == 'tiktok':
            if view_count > 0:
                stats_data['tt_view_count'] = view_count
            if like_count > 0:
                stats_data['tt_like_count'] = like_count
            if view_count > 0 or like_count > 0:
                stats_data['tt_account_count'] = 0  # 分发数据不统计账号
        
        # 构建payload（符合X2C Pool批量更新格式）
        payload = {
            'site_name': 'DramaRelayBot',
            'production_source': 'ai_factory',  # X2C Pool要求的字段
            'stats': [stats_data]
        }
        
        logger.info(f"📤 回传任务 {task_id} 数据: {json.dumps(payload, ensure_ascii=False)}")
        
        # 发送Webhook
        success, error = await send_webhook(
            callback_url,
            payload,
            callback_secret,
            timeout=30
        )
        
        if success:
            logger.info(f"✅ 任务 {task_id} 数据回传成功")
            # 记录成功日志
            log_webhook_success(
                task_id=task_id,
                task_title=task.get('title', ''),
                project_id=task.get('project_id', ''),
                callback_url=callback_url,
                payload=payload
            )
            return True
        else:
            logger.error(f"❌ 任务 {task_id} 数据回传失败: {error}")
            # 记录错误日志
            log_broadcaster_error(
                task_id=task_id,
                task_title=task.get('title', ''),
                project_id=task.get('project_id', ''),
                video_url=task.get('video_url', ''),
                platform='unknown',
                error_type='CALLBACK_FAILED',
                error_message=str(error),
                callback_url=callback_url
            )
            return False
            
    except Exception as e:
        logger.error(f"❌ 任务 {task_id} 回传异常: {e}")
        import traceback
        traceback.print_exc()
        # 记录错误日志
        log_broadcaster_error(
            task_id=task_id,
            task_title=task.get('title', ''),
            project_id=task.get('project_id', ''),
            video_url=task.get('video_url', ''),
            platform='unknown',
            error_type='BROADCAST_ERROR',
            error_message=str(e),
            callback_url=task.get('callback_url', '')
        )
        return False

async def broadcast_all_tasks():
    """
    回传所有活跃任务的统计数据
    
    Returns:
        dict: 回传结果统计
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询所有活跃且配置了callback_url的任务
        cur.execute("""
            SELECT 
                task_id,
                external_task_id,
                project_id,
                title,
                video_url,
                callback_url,
                callback_secret,
                duration
            FROM drama_tasks
            WHERE status = 'active'
              AND callback_url IS NOT NULL
              AND callback_url != ''
            ORDER BY task_id
        """)
        
        tasks = cur.fetchall()
        cur.close()
        conn.close()
        
        if not tasks:
            logger.info("ℹ️ 没有需要回传的任务")
            return {
                'success': True,
                'total': 0,
                'success_count': 0,
                'failed_count': 0
            }
        
        logger.info(f"📊 开始回传 {len(tasks)} 个任务的数据")
        
        # 逐个回传
        success_count = 0
        failed_count = 0
        total_views = 0  # 统计总播放量
        
        for task in tasks:
            # 先获取视频统计数据
            video_url = task['video_url']
            platform = 'youtube'
            if 'tiktok.com' in video_url or 'vm.tiktok.com' in video_url:
                platform = 'tiktok'
            elif 'douyin.com' in video_url or 'v.douyin.com' in video_url:
                platform = 'douyin'
            
            stats = await fetch_task_stats(task['task_id'], video_url, platform)
            if stats:
                views = stats.get('views', 0) or stats.get('view_count', 0)
                total_views += views
            
            # 回传数据
            success = await broadcast_task_stats(task)
            if success:
                success_count += 1
            else:
                failed_count += 1
            
            # 每个任务之间间隔1秒，避免请求过快
            await asyncio.sleep(1)
        
        logger.info(f"✅ 回传完成: 成功 {success_count}, 失败 {failed_count}, 总播放量 {total_views}")
        
        return {
            'success': True,
            'total': len(tasks),
            'success_count': success_count,
            'failed_count': failed_count,
            'total_views': total_views,  # 添加总播放量字段
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ 回传任务失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

async def broadcaster_loop():
    """
    分发数据回传循环
    每3分钟执行一次
    """
    global broadcaster_running
    
    logger.info("🚀 分发数据回传服务已启动")
    
    while broadcaster_running:
        try:
            logger.info("="*70)
            logger.info(f"📡 开始新一轮数据回传 - {datetime.now()}")
            logger.info("="*70)
            
            result = await broadcast_all_tasks()
            
            logger.info("="*70)
            logger.info(f"📊 回传结果: {json.dumps(result, ensure_ascii=False)}")
            logger.info("="*70)
            
            # 等待3分钟
            logger.info("⏰ 等待3分钟后进行下一轮回传...")
            await asyncio.sleep(180)  # 3分钟 = 180秒
            
        except Exception as e:
            logger.error(f"❌ 回传循环异常: {e}")
            import traceback
            traceback.print_exc()
            # 发生异常后等待30秒再重试
            await asyncio.sleep(30)
    
    logger.info("🛑 分发数据回传服务已停止")

def start_broadcaster():
    """启动分发数据回传服务"""
    global broadcaster_running, broadcaster_task
    
    if broadcaster_running:
        logger.warning("⚠️ 分发数据回传服务已在运行中")
        return False
    
    try:
        broadcaster_running = True
        
        # 检查是否有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，直接创建任务
            broadcaster_task = loop.create_task(broadcaster_loop())
        except RuntimeError:
            # 没有运行中的循环，创建新的循环并在后台运行
            import threading
            
            def run_broadcaster():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(broadcaster_loop())
            
            thread = threading.Thread(target=run_broadcaster, daemon=True)
            thread.start()
            broadcaster_task = thread
        
        logger.info("✅ 分发数据回传服务启动成功")
        return True
        
    except Exception as e:
        broadcaster_running = False
        logger.error(f"❌ 启动分发数据回传服务失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def stop_broadcaster():
    """停止分发数据回传服务"""
    global broadcaster_running, broadcaster_task
    
    if not broadcaster_running:
        logger.warning("⚠️ 分发数据回传服务未运行")
        return False
    
    broadcaster_running = False
    if broadcaster_task:
        broadcaster_task.cancel()
    logger.info("✅ 分发数据回传服务停止成功")
    return True

def get_broadcaster_status():
    """获取分发数据回传服务状态"""
    return {
        'running': broadcaster_running,
        'timestamp': datetime.now().isoformat()
    }

# 如果直接运行此脚本，启动服务
if __name__ == "__main__":
    async def main():
        start_broadcaster()
        try:
            # 保持运行
            while broadcaster_running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号，停止服务...")
            stop_broadcaster()
    
    asyncio.run(main())
