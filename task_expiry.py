#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务过期清理模块
- 任务分发后超过48小时自动过期
- 过期的任务不再允许领取
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 默认任务过期时间（小时）- 7天
DEFAULT_TASK_EXPIRY_HOURS = 168


def get_task_expiry_hours() -> int:
    """
    从数据库获取任务过期时间配置
    
    Returns:
        int: 任务过期时间（小时）
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT value FROM bot_settings WHERE key = 'task_expiry_hours'
        """)
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if result:
            return int(result['value'])
        return DEFAULT_TASK_EXPIRY_HOURS
    except Exception as e:
        logger.error(f"❌ 获取任务过期时间配置失败: {e}")
        return DEFAULT_TASK_EXPIRY_HOURS


def set_task_expiry_hours(hours: int) -> bool:
    """
    设置任务过期时间
    
    Args:
        hours: 过期时间（小时）
        
    Returns:
        bool: 是否设置成功
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 使用 UPSERT 语法
        cur.execute("""
            INSERT INTO bot_settings (key, value, description, updated_at)
            VALUES ('task_expiry_hours', %s, '任务有效期（小时）', CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
        """, (str(hours), str(hours)))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ 任务过期时间已设置为 {hours} 小时")
        return True
    except Exception as e:
        logger.error(f"❌ 设置任务过期时间失败: {e}")
        return False


def init_bot_settings_table():
    """
    初始化 bot_settings 表
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入默认配置
        cur.execute("""
            INSERT INTO bot_settings (key, value, description)
            VALUES ('task_expiry_hours', %s, '任务有效期（小时）')
            ON CONFLICT (key) DO NOTHING
        """, (str(DEFAULT_TASK_EXPIRY_HOURS),))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ bot_settings 表初始化完成")
    except Exception as e:
        logger.error(f"❌ 初始化 bot_settings 表失败: {e}")


def get_db_connection():
    """获取数据库连接"""
    from bot import get_db_connection as _get_db_connection
    return _get_db_connection()


def is_task_expired(task: dict) -> bool:
    """
    检查任务是否已过期
    
    Args:
        task: 任务字典，需要包含 created_at 字段
        
    Returns:
        bool: True 表示已过期，False 表示未过期
    """
    if not task:
        return True
    
    created_at = task.get('created_at')
    if not created_at:
        return False  # 没有创建时间的任务不过期
    
    # 获取配置的过期时间
    expiry_hours = get_task_expiry_hours()
    
    # 计算过期时间
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    
    expiry_time = created_at + timedelta(hours=expiry_hours)
    
    return datetime.now(created_at.tzinfo if created_at.tzinfo else None) > expiry_time


def cleanup_expired_tasks() -> dict:
    """
    清理过期的任务
    - 将超过48小时的活跃任务标记为 inactive
    - 清理相关的用户领取记录
    
    Returns:
        dict: 清理结果统计
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    result = {
        'expired_tasks': 0,
        'cleaned_user_tasks': 0
    }
    
    # 获取配置的过期时间
    expiry_hours = get_task_expiry_hours()
    
    try:
        # 1. 查找并标记过期的任务
        # 注意：drama_tasks 表可能没有 updated_at 字段，所以只更新 status
        cur.execute("""
            UPDATE drama_tasks
            SET status = 'expired'
            WHERE status = 'active'
            AND created_at < NOW() - INTERVAL '%s hours'
            RETURNING task_id
        """, (expiry_hours,))
        
        expired_tasks = cur.fetchall()
        result['expired_tasks'] = len(expired_tasks)
        
        if expired_tasks:
            expired_task_ids = [t['task_id'] for t in expired_tasks]
            logger.info(f"🕐 发现 {len(expired_task_ids)} 个过期任务: {expired_task_ids}")
            
            # 2. 清理这些任务的用户领取记录（仅清理未完成的）
            cur.execute("""
                DELETE FROM user_tasks
                WHERE task_id = ANY(%s)
                AND status IN ('in_progress', 'claimed')
                RETURNING id
            """, (expired_task_ids,))
            
            cleaned_records = cur.fetchall()
            result['cleaned_user_tasks'] = len(cleaned_records)
            
            logger.info(f"🧹 清理了 {len(cleaned_records)} 条未完成的用户任务记录")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"❌ 清理过期任务失败: {e}", exc_info=True)
        conn.rollback()
    finally:
        cur.close()
        conn.close()
    
    return result


def get_active_non_expired_tasks_query() -> str:
    """
    获取查询活跃且未过期任务的 SQL 条件
    
    Returns:
        str: SQL WHERE 条件片段
    """
    return f"status = 'active' AND created_at > NOW() - INTERVAL '{TASK_EXPIRY_HOURS} hours'"


def filter_expired_tasks(tasks: list) -> list:
    """
    过滤掉已过期的任务
    
    Args:
        tasks: 任务列表
        
    Returns:
        list: 过滤后的未过期任务列表
    """
    return [task for task in tasks if not is_task_expired(task)]


def start_expiry_cleanup_scheduler(application):
    """
    启动过期任务清理调度器
    每小时执行一次清理
    
    Args:
        application: Telegram Application 对象
    """
    from telegram.ext import ContextTypes
    
    async def cleanup_job(context: ContextTypes.DEFAULT_TYPE):
        """定时清理任务"""
        try:
            result = cleanup_expired_tasks()
            if result['expired_tasks'] > 0 or result['cleaned_user_tasks'] > 0:
                logger.info(f"🧹 过期任务清理完成: {result}")
        except Exception as e:
            logger.error(f"❌ 过期任务清理失败: {e}", exc_info=True)
    
    # 使用 application 的 job_queue 注册定时任务
    # 每小时执行一次，首次执行在 60 秒后
    application.job_queue.run_repeating(
        cleanup_job,
        interval=3600,  # 每小时
        first=60,  # 首次执行在 60 秒后
        name='expiry_cleanup'
    )
    logger.info("✅ 任务过期清理调度器已注册（每小时执行一次）")
