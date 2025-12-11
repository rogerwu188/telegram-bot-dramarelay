#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日汇总统计扫描器
用于定期扫描已完成的任务，聚合每日统计数据并回传到X2C平台
"""

import os
import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import json

from video_stats_fetcher import VideoStatsFetcher
from webhook_notifier import send_webhook

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DATABASE_URL = os.getenv('DATABASE_URL')

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


class DailyStatsScanner:
    """每日统计扫描器"""
    
    def __init__(self):
        """初始化扫描器"""
        self.video_fetcher = VideoStatsFetcher(
            tikhub_api_key=os.getenv('TIKHUB_API_KEY'),
            youtube_api_key=os.getenv('YOUTUBE_API_KEY')
        )
    
    async def scan_and_aggregate(self, target_date: Optional[date] = None) -> Dict:
        """
        扫描并聚合指定日期的任务统计数据
        
        Args:
            target_date: 目标日期，默认为昨天
        
        Returns:
            dict: {
                'success': bool,
                'date': str,
                'tasks_processed': int,
                'stats_created': int,
                'webhooks_sent': int,
                'errors': list
            }
        """
        if not target_date:
            target_date = date.today() - timedelta(days=1)
        
        logger.info(f"🔍 开始扫描 {target_date} 的任务统计数据...")
        
        result = {
            'success': True,
            'date': str(target_date),
            'tasks_processed': 0,
            'stats_created': 0,
            'webhooks_sent': 0,
            'errors': []
        }
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 1. 获取在目标日期有完成记录的所有任务
            cur.execute("""
                SELECT DISTINCT dt.task_id, dt.project_id, dt.external_task_id, 
                       dt.duration, dt.callback_url, dt.callback_secret
                FROM drama_tasks dt
                INNER JOIN user_tasks ut ON dt.task_id = ut.task_id
                WHERE ut.status = 'submitted'
                  AND DATE(ut.submitted_at) = %s
                  AND dt.status = 'active'
            """, (target_date,))
            
            tasks = cur.fetchall()
            logger.info(f"📊 找到 {len(tasks)} 个任务在 {target_date} 有完成记录")
            
            for task in tasks:
                try:
                    result['tasks_processed'] += 1
                    
                    # 2. 聚合该任务在目标日期的统计数据
                    stats = await self._aggregate_task_stats(
                        cur, 
                        task['task_id'], 
                        target_date
                    )
                    
                    # 3. 保存到 task_daily_stats 表
                    stats_id = self._save_daily_stats(
                        cur, 
                        conn,
                        task['task_id'],
                        task['project_id'],
                        task['external_task_id'],
                        target_date,
                        stats
                    )
                    
                    if stats_id:
                        result['stats_created'] += 1
                        logger.info(f"✅ 任务 {task['task_id']} 的每日统计已保存 (ID: {stats_id})")
                        
                        # 4. 如果有callback_url，发送Webhook
                        if task['callback_url']:
                            webhook_success = await self._send_daily_webhook(
                                task['callback_url'],
                                task['callback_secret'],
                                task['project_id'],
                                task['external_task_id'],
                                task['duration'],
                                stats
                            )
                            
                            if webhook_success:
                                result['webhooks_sent'] += 1
                                
                                # 更新回传状态
                                cur.execute("""
                                    UPDATE task_daily_stats
                                    SET webhook_sent = TRUE,
                                        webhook_sent_at = CURRENT_TIMESTAMP
                                    WHERE id = %s
                                """, (stats_id,))
                                conn.commit()
                    
                except Exception as e:
                    error_msg = f"处理任务 {task['task_id']} 失败: {e}"
                    logger.error(f"❌ {error_msg}")
                    result['errors'].append(error_msg)
                    continue
            
            cur.close()
            conn.close()
            
            logger.info(f"✅ 扫描完成: 处理 {result['tasks_processed']} 个任务, "
                       f"创建 {result['stats_created']} 条统计, "
                       f"发送 {result['webhooks_sent']} 个Webhook")
            
        except Exception as e:
            result['success'] = False
            result['errors'].append(f"扫描失败: {e}")
            logger.error(f"❌ 扫描失败: {e}", exc_info=True)
        
        return result
    
    async def _aggregate_task_stats(self, cur, task_id: int, target_date: date) -> Dict:
        """
        聚合指定任务在指定日期的统计数据
        
        Args:
            cur: 数据库游标
            task_id: 任务ID
            target_date: 目标日期
        
        Returns:
            dict: 聚合后的统计数据
        """
        stats = {
            'total_account_count': 0,
            'total_completion_count': 0,
            'yt_account_count': 0,
            'yt_view_count': 0,
            'yt_like_count': 0,
            'yt_comment_count': 0,
            'tt_account_count': 0,
            'tt_view_count': 0,
            'tt_like_count': 0,
            'tt_comment_count': 0,
            'dy_account_count': 0,
            'dy_view_count': 0,
            'dy_like_count': 0,
            'dy_comment_count': 0,
            'dy_share_count': 0,
            'dy_collect_count': 0,
        }
        
        # 获取该任务在目标日期的所有完成记录
        cur.execute("""
            SELECT user_id, platform, submission_link, verification_details
            FROM user_tasks
            WHERE task_id = %s
              AND status = 'submitted'
              AND DATE(submitted_at) = %s
        """, (task_id, target_date))
        
        completions = cur.fetchall()
        
        # 统计账号数（去重）
        unique_users = set()
        platform_users = {'youtube': set(), 'tiktok': set(), 'douyin': set()}
        
        for completion in completions:
            user_id = completion['user_id']
            platform = (completion['platform'] or '').lower()
            
            unique_users.add(user_id)
            stats['total_completion_count'] += 1
            
            # 按平台统计
            if platform in ['youtube', 'yt']:
                platform_users['youtube'].add(user_id)
                
                # 尝试从verification_details提取数据
                if completion['verification_details']:
                    try:
                        details = json.loads(completion['verification_details']) if isinstance(completion['verification_details'], str) else completion['verification_details']
                        stats['yt_view_count'] += details.get('view_count', 0)
                        stats['yt_like_count'] += details.get('like_count', 0)
                        stats['yt_comment_count'] += details.get('comment_count', 0)
                    except:
                        pass
                
                # 如果没有数据，尝试实时抓取
                if stats['yt_view_count'] == 0 and completion['submission_link']:
                    video_stats = await self.video_fetcher.fetch_video_stats(
                        completion['submission_link'],
                        platform='youtube'
                    )
                    if video_stats['success']:
                        stats['yt_view_count'] += video_stats.get('view_count', 0)
                        stats['yt_like_count'] += video_stats.get('like_count', 0)
                        stats['yt_comment_count'] += video_stats.get('comment_count', 0)
            
            elif platform in ['tiktok', 'tt']:
                platform_users['tiktok'].add(user_id)
                
                if completion['verification_details']:
                    try:
                        details = json.loads(completion['verification_details']) if isinstance(completion['verification_details'], str) else completion['verification_details']
                        stats['tt_view_count'] += details.get('view_count', 0)
                        stats['tt_like_count'] += details.get('like_count', 0)
                        stats['tt_comment_count'] += details.get('comment_count', 0)
                    except:
                        pass
            
            elif platform in ['douyin', 'dy']:
                platform_users['douyin'].add(user_id)
                
                if completion['verification_details']:
                    try:
                        details = json.loads(completion['verification_details']) if isinstance(completion['verification_details'], str) else completion['verification_details']
                        stats['dy_view_count'] += details.get('view_count', 0)
                        stats['dy_like_count'] += details.get('like_count', 0)
                        stats['dy_comment_count'] += details.get('comment_count', 0)
                        stats['dy_share_count'] += details.get('share_count', 0)
                        stats['dy_collect_count'] += details.get('collect_count', 0)
                    except:
                        pass
                
                # 如果没有数据，尝试实时抓取
                if stats['dy_view_count'] == 0 and completion['submission_link']:
                    video_stats = await self.video_fetcher.fetch_video_stats(
                        completion['submission_link'],
                        platform='douyin'
                    )
                    if video_stats['success']:
                        stats['dy_view_count'] += video_stats.get('view_count', 0)
                        stats['dy_like_count'] += video_stats.get('like_count', 0)
                        stats['dy_comment_count'] += video_stats.get('comment_count', 0)
                        stats['dy_share_count'] += video_stats.get('share_count', 0)
                        stats['dy_collect_count'] += video_stats.get('collect_count', 0)
        
        # 设置账号数
        stats['total_account_count'] = len(unique_users)
        stats['yt_account_count'] = len(platform_users['youtube'])
        stats['tt_account_count'] = len(platform_users['tiktok'])
        stats['dy_account_count'] = len(platform_users['douyin'])
        
        logger.info(f"📊 任务 {task_id} 在 {target_date} 的统计: "
                   f"总账号数={stats['total_account_count']}, "
                   f"YT={stats['yt_account_count']}, "
                   f"TT={stats['tt_account_count']}, "
                   f"DY={stats['dy_account_count']}")
        
        return stats
    
    def _save_daily_stats(self, cur, conn, task_id: int, project_id: str, 
                         external_task_id: int, stats_date: date, stats: Dict) -> Optional[int]:
        """
        保存每日统计数据到数据库
        
        Returns:
            int: 统计记录ID，失败返回None
        """
        try:
            # 使用 INSERT ... ON CONFLICT 实现 upsert
            cur.execute("""
                INSERT INTO task_daily_stats (
                    task_id, project_id, external_task_id, stats_date,
                    total_account_count, total_completion_count,
                    yt_account_count, yt_view_count, yt_like_count, yt_comment_count,
                    tt_account_count, tt_view_count, tt_like_count, tt_comment_count,
                    dy_account_count, dy_view_count, dy_like_count, dy_comment_count,
                    dy_share_count, dy_collect_count
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (task_id, stats_date)
                DO UPDATE SET
                    total_account_count = EXCLUDED.total_account_count,
                    total_completion_count = EXCLUDED.total_completion_count,
                    yt_account_count = EXCLUDED.yt_account_count,
                    yt_view_count = EXCLUDED.yt_view_count,
                    yt_like_count = EXCLUDED.yt_like_count,
                    yt_comment_count = EXCLUDED.yt_comment_count,
                    tt_account_count = EXCLUDED.tt_account_count,
                    tt_view_count = EXCLUDED.tt_view_count,
                    tt_like_count = EXCLUDED.tt_like_count,
                    tt_comment_count = EXCLUDED.tt_comment_count,
                    dy_account_count = EXCLUDED.dy_account_count,
                    dy_view_count = EXCLUDED.dy_view_count,
                    dy_like_count = EXCLUDED.dy_like_count,
                    dy_comment_count = EXCLUDED.dy_comment_count,
                    dy_share_count = EXCLUDED.dy_share_count,
                    dy_collect_count = EXCLUDED.dy_collect_count,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                task_id, project_id, external_task_id, stats_date,
                stats['total_account_count'], stats['total_completion_count'],
                stats['yt_account_count'], stats['yt_view_count'], 
                stats['yt_like_count'], stats['yt_comment_count'],
                stats['tt_account_count'], stats['tt_view_count'], 
                stats['tt_like_count'], stats['tt_comment_count'],
                stats['dy_account_count'], stats['dy_view_count'], 
                stats['dy_like_count'], stats['dy_comment_count'],
                stats['dy_share_count'], stats['dy_collect_count']
            ))
            
            result = cur.fetchone()
            conn.commit()
            
            return result['id'] if result else None
            
        except Exception as e:
            logger.error(f"❌ 保存每日统计失败: {e}")
            conn.rollback()
            return None
    
    async def _send_daily_webhook(self, callback_url: str, callback_secret: str,
                                  project_id: str, external_task_id: int,
                                  duration: int, stats: Dict) -> bool:
        """
        发送每日汇总Webhook
        
        Returns:
            bool: 是否发送成功
        """
        # 构建回调数据（只包含有数据的字段）
        stat_item = {
            'project_id': project_id,
            'task_id': external_task_id,
            'duration': duration,
            'account_count': stats['total_account_count']
        }
        
        # YouTube数据
        if stats['yt_account_count'] > 0:
            stat_item['yt_account_count'] = stats['yt_account_count']
            if stats['yt_view_count'] > 0:
                stat_item['yt_view_count'] = stats['yt_view_count']
            if stats['yt_like_count'] > 0:
                stat_item['yt_like_count'] = stats['yt_like_count']
        
        # TikTok数据
        if stats['tt_account_count'] > 0:
            stat_item['tt_account_count'] = stats['tt_account_count']
            if stats['tt_view_count'] > 0:
                stat_item['tt_view_count'] = stats['tt_view_count']
            if stats['tt_like_count'] > 0:
                stat_item['tt_like_count'] = stats['tt_like_count']
        
        # 抖音数据：计入YouTube总量，不单独回传dy_*字段
        # 抖音数据只在本地展现，但播放量和点赞数计入yt_*总量
        if stats['dy_account_count'] > 0:
            # 将抖音账号数计入YouTube账号数
            if 'yt_account_count' not in stat_item:
                stat_item['yt_account_count'] = 0
            stat_item['yt_account_count'] += stats['dy_account_count']
            
            # 将抖音播放量计入YouTube播放量
            if stats['dy_view_count'] > 0:
                if 'yt_view_count' not in stat_item:
                    stat_item['yt_view_count'] = 0
                stat_item['yt_view_count'] += stats['dy_view_count']
            
            # 将抖音点赞数计入YouTube点赞数
            if stats['dy_like_count'] > 0:
                if 'yt_like_count' not in stat_item:
                    stat_item['yt_like_count'] = 0
                stat_item['yt_like_count'] += stats['dy_like_count']
        
        payload = {
            'site_name': 'DramaRelayBot',
            'stats': [stat_item]
        }
        
        logger.info(f"📤 发送每日汇总Webhook: {callback_url}")
        logger.info(f"📊 数据: {json.dumps(payload, ensure_ascii=False)}")
        
        success, error = await send_webhook(
            callback_url,
            payload,
            callback_secret,
            timeout=30
        )
        
        if success:
            logger.info(f"✅ Webhook发送成功")
        else:
            logger.error(f"❌ Webhook发送失败: {error}")
        
        return success


async def run_daily_scan(target_date: Optional[date] = None):
    """
    运行每日扫描（便捷函数）
    
    Args:
        target_date: 目标日期，默认为昨天
    """
    scanner = DailyStatsScanner()
    result = await scanner.scan_and_aggregate(target_date)
    
    print(f"\n{'='*70}")
    print(f"📊 每日统计扫描结果")
    print(f"{'='*70}")
    print(f"日期: {result['date']}")
    print(f"处理任务数: {result['tasks_processed']}")
    print(f"创建统计数: {result['stats_created']}")
    print(f"发送Webhook数: {result['webhooks_sent']}")
    
    if result['errors']:
        print(f"\n❌ 错误 ({len(result['errors'])}个):")
        for error in result['errors']:
            print(f"  - {error}")
    
    print(f"{'='*70}\n")
    
    return result


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数指定日期
    target_date = None
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        except ValueError:
            print(f"❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            sys.exit(1)
    
    asyncio.run(run_daily_scan(target_date))
