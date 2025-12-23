#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步验证 Worker - 后台处理视频链接验证
"""

import os
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 数据库连接
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_pending_verifications_table():
    """初始化 pending_verifications 表"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_verifications (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                task_id INTEGER NOT NULL,
                video_url TEXT NOT NULL,
                platform VARCHAR(50),
                status VARCHAR(20) DEFAULT 'pending',
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                UNIQUE(user_id, task_id, video_url)
            )
        """)
        
        # 创建索引
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_verifications_status 
            ON pending_verifications(status)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_verifications_user 
            ON pending_verifications(user_id)
        """)
        
        conn.commit()
        logger.info("✅ pending_verifications 表已创建/确认")
    except Exception as e:
        logger.error(f"❌ 创建 pending_verifications 表失败: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def add_to_verification_queue(user_id: int, task_id: int, video_url: str, platform: str) -> Optional[int]:
    """
    将链接添加到验证队列
    返回队列记录 ID，如果已存在则返回 None
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 检查是否已存在相同的待验证记录
        cur.execute("""
            SELECT id, status FROM pending_verifications 
            WHERE user_id = %s AND task_id = %s AND video_url = %s
        """, (user_id, task_id, video_url))
        
        existing = cur.fetchone()
        if existing:
            if existing['status'] == 'pending':
                logger.info(f"⚠️ 相同的验证请求已在队列中: id={existing['id']}")
                return existing['id']
            elif existing['status'] == 'failed':
                # 如果之前失败了，重置状态重新验证
                # 注意：同时更新 created_at，避免被超时清理误删
                # 重置 retry_count 为 0，确保任务会被 Worker 处理
                cur.execute("""
                    UPDATE pending_verifications 
                    SET status = 'pending', retry_count = 0, 
                        updated_at = CURRENT_TIMESTAMP, 
                        created_at = CURRENT_TIMESTAMP,
                        error_message = NULL
                    WHERE id = %s
                """, (existing['id'],))
                conn.commit()
                logger.info(f"🔄 重新加入验证队列: id={existing['id']}")
                return existing['id']
            else:
                # 已完成的任务不再重复验证
                logger.info(f"✅ 该链接已验证完成: id={existing['id']}")
                return None
        
        # 插入新记录
        cur.execute("""
            INSERT INTO pending_verifications (user_id, task_id, video_url, platform, status)
            VALUES (%s, %s, %s, %s, 'pending')
            RETURNING id
        """, (user_id, task_id, video_url, platform))
        
        record_id = cur.fetchone()['id']
        conn.commit()
        logger.info(f"✅ 已添加到验证队列: id={record_id}, user={user_id}, task={task_id}")
        return record_id
        
    except Exception as e:
        logger.error(f"❌ 添加到验证队列失败: {e}")
        conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()


def cleanup_stale_pending_verifications(timeout_minutes: int = 5) -> int:
    """
    清理超时的 pending 任务
    将超过 timeout_minutes 分钟的 pending 任务标记为 failed
    返回清理的记录数
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE pending_verifications 
            SET status = 'failed', 
                error_message = '验证超时，请重新提交',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'pending' 
            AND created_at < NOW() - INTERVAL '%s minutes'
            RETURNING id
        """, (timeout_minutes,))
        
        cleaned = cur.fetchall()
        conn.commit()
        
        if cleaned:
            logger.info(f"🧹 清理了 {len(cleaned)} 条超时的 pending 任务")
        
        return len(cleaned)
    except Exception as e:
        logger.error(f"❌ 清理超时任务失败: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()


def force_fail_all_pending() -> int:
    """
    强制将所有 pending 任务标记为 failed
    用于管理员手动清理
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE pending_verifications 
            SET status = 'failed', 
                error_message = '管理员手动清理，请重新提交',
                updated_at = CURRENT_TIMESTAMP
            WHERE status = 'pending'
            RETURNING id, user_id, task_id
        """)
        
        cleaned = cur.fetchall()
        conn.commit()
        
        logger.info(f"🧹 强制清理了 {len(cleaned)} 条 pending 任务")
        return len(cleaned)
    except Exception as e:
        logger.error(f"❌ 强制清理失败: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()


def get_pending_verifications(limit: int = 10) -> list:
    """获取待验证的记录"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT pv.*, dt.title as task_title, dt.description as task_description,
                   dt.node_power_reward as reward
            FROM pending_verifications pv
            JOIN drama_tasks dt ON pv.task_id = dt.task_id
            WHERE pv.status = 'pending' AND pv.retry_count < 3
            ORDER BY pv.created_at ASC
            LIMIT %s
        """, (limit,))
        
        records = cur.fetchall()
        return [dict(r) for r in records]
    except Exception as e:
        logger.error(f"❌ 获取待验证记录失败: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def update_verification_status(record_id: int, status: str, error_message: str = None):
    """更新验证状态"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if status == 'completed':
            cur.execute("""
                UPDATE pending_verifications 
                SET status = %s, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, record_id))
        else:
            cur.execute("""
                UPDATE pending_verifications 
                SET status = %s, error_message = %s, updated_at = CURRENT_TIMESTAMP,
                    retry_count = retry_count + 1
                WHERE id = %s
            """, (status, error_message, record_id))
        
        conn.commit()
        logger.info(f"✅ 更新验证状态: id={record_id}, status={status}")
    except Exception as e:
        logger.error(f"❌ 更新验证状态失败: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


async def process_single_verification(record: dict, bot, link_verifier) -> bool:
    """
    处理单个验证任务
    返回 True 表示验证成功，False 表示失败
    """
    record_id = record['id']
    user_id = record['user_id']
    task_id = record['task_id']
    video_url = record['video_url']
    platform = record['platform']
    task_title = record['task_title']
    task_description = record['task_description'] or ''
    reward = record['reward']
    
    logger.info(f"🔍 开始验证: id={record_id}, user={user_id}, task={task_id}")
    
    try:
        # 调用验证器
        # 超时时间设置为 300 秒（5分钟），以容纳 3 次重试（每次间隔 60 秒 + 请求时间）
        verify_result = await asyncio.wait_for(
            link_verifier.verify_link(
                url=video_url,
                task_title=task_title,
                task_description=task_description
            ),
            timeout=300.0
        )
        
        if verify_result.get('success') and verify_result.get('matched'):
            # 验证成功，提交任务
            from bot import submit_task_link, get_user_stats, get_user_language
            
            try:
                actual_reward = submit_task_link(user_id, task_id, platform, video_url)
                logger.info(f"✅ 任务提交成功: user={user_id}, task={task_id}, reward={actual_reward}")
                
                # 更新状态为完成
                update_verification_status(record_id, 'completed')
                
                # 获取用户语言
                user_lang = get_user_language(user_id)
                
                # 获取用户统计
                stats = get_user_stats(user_id)
                total_power = stats.get('total_power', 0) or 0
                
                # 发送成功通知给用户
                success_msg = (
                    f"🎉 <b>核验通过！</b>\n\n"
                    f"🎬 任务：{task_title}\n"
                    f"💰 奖励：<b>+{actual_reward} X2C</b> 已到账！\n\n"
                    f"📊 当前总算力：{total_power} X2C\n\n"
                    f"继续分发更多内容，解锁更高等级与更多 X2C 奖励！"
                ) if user_lang.startswith('zh') else (
                    f"🎉 <b>Verification Passed!</b>\n\n"
                    f"🎬 Task: {task_title}\n"
                    f"💰 Reward: <b>+{actual_reward} X2C</b> credited!\n\n"
                    f"📊 Total Power: {total_power} X2C\n\n"
                    f"Keep distributing to unlock higher levels and more X2C rewards!"
                )
                
                # 发送成功通知并附带主菜单
                # 只对 Bot 端用户发送 Telegram 通知（Web 端用户 ID >= 9000000000）
                if user_id < 9000000000:
                    from bot import get_main_menu_keyboard
                    await bot.send_message(
                        chat_id=user_id,
                        text=success_msg,
                        parse_mode='HTML',
                        disable_web_page_preview=True,
                        reply_markup=get_main_menu_keyboard(user_lang)
                    )
                else:
                    logger.info(f"⏭️ 跳过 Telegram 通知（Web 端用户验证成功）: user_id={user_id}, task_id={task_id}")
                
                # 发送 Webhook 回调
                try:
                    from webhook_notifier import send_task_completed_webhook
                    await send_task_completed_webhook(
                        task_id=task_id,
                        user_id=user_id,
                        platform=platform.lower(),
                        submission_link=video_url,
                        node_power_earned=actual_reward,
                        verification_details=verify_result
                    )
                except Exception as webhook_error:
                    logger.error(f"⚠️ Webhook 回调失败: {webhook_error}")
                
                return True
                
            except Exception as submit_error:
                logger.error(f"❌ 提交任务失败: {submit_error}")
                update_verification_status(record_id, 'failed', str(submit_error))
                return False
        else:
            # 验证失败
            error_reason = verify_result.get('error', '内容不匹配')
            update_verification_status(record_id, 'failed', error_reason)
            
            # 获取用户语言
            from bot import get_user_language
            user_lang = get_user_language(user_id)
            
            # 发送失败通知给用户
            fail_msg = (
                f"❌ <b>核验失败</b>\n\n"
                f"🎬 任务：{task_title}\n"
                f"🔗 链接：{video_url[:50]}...\n\n"
                f"📝 原因：{error_reason}\n\n"
                f"请检查后重新提交。"
            ) if user_lang.startswith('zh') else (
                f"❌ <b>Verification Failed</b>\n\n"
                f"🎬 Task: {task_title}\n"
                f"🔗 Link: {video_url[:50]}...\n\n"
                f"📝 Reason: {error_reason}\n\n"
                f"Please check and resubmit."
            )
            
            # 发送失败通知并附带主菜单
            # 只对 Bot 端用户发送 Telegram 通知（Web 端用户 ID >= 9000000000）
            if user_id < 9000000000:
                from bot import get_main_menu_keyboard
                await bot.send_message(
                    chat_id=user_id,
                    text=fail_msg,
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                    reply_markup=get_main_menu_keyboard(user_lang)
                )
            else:
                logger.info(f"⏭️ 跳过 Telegram 通知（Web 端用户验证失败）: user_id={user_id}, task_id={task_id}, error={error_reason}")
            
            return False
            
    except asyncio.TimeoutError:
        logger.error(f"⚠️ 验证超时: id={record_id}")
        update_verification_status(record_id, 'failed', '验证超时，请稍后重试')
        return False
    except Exception as e:
        logger.error(f"❌ 验证异常: {e}")
        update_verification_status(record_id, 'failed', str(e))
        return False


async def run_verification_worker(bot, link_verifier, interval: int = 5):
    """
    运行验证 Worker
    每隔 interval 秒检查一次队列
    """
    logger.info(f"🚀 验证 Worker 启动，检查间隔: {interval}秒")
    
    check_count = 0
    while True:
        try:
            check_count += 1
            # 每10次输出一次心跳日志
            if check_count % 10 == 0:
                logger.info(f"💓 Worker 心跳: 已检查 {check_count} 次")
            
            # 每次循环先清理超时的任务（5分钟超时）
            cleanup_stale_pending_verifications(timeout_minutes=5)
            
            # 获取待验证记录
            pending_records = get_pending_verifications(limit=5)
            
            if pending_records:
                logger.info(f"📋 发现 {len(pending_records)} 条待验证记录")
                
                for record in pending_records:
                    try:
                        logger.info(f"🔄 开始处理: id={record['id']}, task={record['task_id']}")
                        await process_single_verification(record, bot, link_verifier)
                        logger.info(f"✅ 处理完成: id={record['id']}")
                    except Exception as e:
                        logger.error(f"❌ 处理验证任务失败: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                    
                    # 每个任务之间随机间隔 3-8 秒，避免触发反爬虫机制
                    delay = random.uniform(3, 8)
                    logger.info(f"⏳ 等待 {delay:.1f} 秒后处理下一个任务...")
                    await asyncio.sleep(delay)
            
        except Exception as e:
            logger.error(f"❌ Worker 循环异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # 等待下一次检查
        await asyncio.sleep(interval)


# 初始化表
if __name__ == '__main__':
    init_pending_verifications_table()
    print("✅ 数据库表初始化完成")
