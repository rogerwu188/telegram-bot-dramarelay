# -*- coding: utf-8 -*-
"""
管理页面 API
提供日志查询接口
"""

import logging
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse
from datetime import datetime, timedelta
import requests
import json

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

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

def get_reward_config():
    """获取奖励配置"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT key, value FROM bot_settings 
            WHERE key IN ('task_reward_x2c', 'newcomer_reward_multiplier', 'enable_newcomer_reward')
        """)
        
        settings = cur.fetchall()
        cur.close()
        conn.close()
        
        config = {
            'task_reward_x2c': 100,
            'newcomer_reward_multiplier': 5,
            'enable_newcomer_reward': True
        }
        
        for setting in settings:
            key = setting['key']
            value = setting['value']
            
            if key == 'task_reward_x2c':
                config['task_reward_x2c'] = int(value)
            elif key == 'newcomer_reward_multiplier':
                config['newcomer_reward_multiplier'] = int(value)
            elif key == 'enable_newcomer_reward':
                config['enable_newcomer_reward'] = value.lower() in ('true', '1', 'yes')
        
        return config
    except Exception as e:
        logger.error(f"获取奖励配置失败: {e}")
        return {
            'task_reward_x2c': 100,
            'newcomer_reward_multiplier': 5,
            'enable_newcomer_reward': True
        }

@app.route('/')
def index():
    """管理页面首页"""
    return render_template('admin.html')

@app.route('/api/logs/tasks', methods=['GET'])
def get_task_logs():
    """
    获取任务日志
    包括：任务接收、用户领取、任务完成
    """
    try:
        # 获取查询参数
        limit = int(request.args.get('limit', 50))
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询最近的任务活动
        # 获取基础奖励配置
        reward_config = get_reward_config()
        base_reward = reward_config['task_reward_x2c']
        
        if hours > 0:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.description,
                    t.category,
                    t.platform_requirements,
                    t.node_power_reward,
                    t.duration,
                    t.video_file_id,
                    t.video_url,
                    t.thumbnail_url,
                    t.task_template,
                    t.keywords_template,
                    t.video_title,
                    t.callback_url,
                    t.callback_secret,
                    t.status as task_status,
                    t.created_at,
                    COALESCE(t.max_completions, 100) as max_completions,
                    COUNT(DISTINCT ut.user_id) as assigned_users,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_users,
                    MAX(ut.submitted_at) as last_completed_at,
                    SUM(COALESCE(ut.node_power_earned, 0)) as total_earned_reward
                FROM drama_tasks t
                LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
                WHERE t.created_at >= NOW() - INTERVAL '%s hours'
                GROUP BY t.task_id
                ORDER BY t.created_at DESC
                LIMIT %s
            """, (hours, limit))
        else:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.description,
                    t.category,
                    t.platform_requirements,
                    t.node_power_reward,
                    t.duration,
                    t.video_file_id,
                    t.video_url,
                    t.thumbnail_url,
                    t.task_template,
                    t.keywords_template,
                    t.video_title,
                    t.callback_url,
                    t.callback_secret,
                    t.status as task_status,
                    t.created_at,
                    COALESCE(t.max_completions, 100) as max_completions,
                    COUNT(DISTINCT ut.user_id) as assigned_users,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_users,
                    MAX(ut.submitted_at) as last_completed_at,
                    SUM(COALESCE(ut.node_power_earned, 0)) as total_earned_reward
                FROM drama_tasks t
                LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
                GROUP BY t.task_id
                ORDER BY t.created_at DESC
                LIMIT %s
            """, (limit,))
        
        tasks = cur.fetchall()
        
        # 转换日期格式并生成原始请求数据
        for task in tasks:
            if task['created_at']:
                task['created_at'] = task['created_at'].isoformat()
            if task['last_completed_at']:
                task['last_completed_at'] = task['last_completed_at'].isoformat()
            
            # 添加基础奖励和实际奖励
            task['base_reward_x2c'] = base_reward  # 接收日志显示的基础奖励
            task['total_earned_reward'] = task.get('total_earned_reward') or 0  # 完成日志显示的实际奖励
            
            # 生成原始请求数据（模拟 X2C 平台下发的数据）
            task['original_request'] = {
                'project_id': task.get('project_id'),
                'task_id': task.get('external_task_id'),
                'title': task.get('title'),
                'description': task.get('description'),
                'video_url': task.get('video_url') or task.get('video_file_id'),
                'thumbnail_url': task.get('thumbnail_url'),
                'duration': task.get('duration'),
                'node_power_reward': task.get('node_power_reward'),
                'platform_requirements': task.get('platform_requirements'),
                'status': task.get('task_status'),
                'callback_url': task.get('callback_url'),
                'callback_secret': task.get('callback_secret') if task.get('callback_secret') else None,
                'task_template': task.get('task_template'),
                'keywords_template': task.get('keywords_template'),
                'video_title': task.get('video_title')
            }
            # 移除 None 值
            task['original_request'] = {k: v for k, v in task['original_request'].items() if v is not None}
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': tasks,
            'count': len(tasks)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/completions', methods=['GET'])
def get_completion_logs():
    """
    获取任务完成日志
    按任务分组，同一任务的多个完成者整合到一行
    """
    try:
        limit = int(request.args.get('limit', 50))
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询最近完成的任务（按任务分组）
        if hours > 0:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.category,
                    t.platform_requirements,
                    t.node_power_reward,
                    t.max_completions,
                    COUNT(DISTINCT ut.user_id) as completion_count,
                    SUM(COALESCE(ut.view_count, 0)) as total_view_count,
                    SUM(COALESCE(ut.like_count, 0)) as total_like_count,
                    MAX(ut.submitted_at) as latest_completed_at,
                    MIN(ut.submitted_at) as earliest_completed_at,
                    MAX(ut.view_count_updated_at) as view_count_updated_at
                FROM user_tasks ut
                JOIN drama_tasks t ON ut.task_id = t.task_id
                WHERE ut.status = 'submitted'
                    AND ut.submitted_at >= NOW() - INTERVAL '%s hours'
                GROUP BY t.task_id, t.external_task_id, t.project_id, t.title, t.category, t.platform_requirements, t.node_power_reward, t.max_completions
                ORDER BY MAX(ut.submitted_at) DESC
                LIMIT %s
            """, (hours, limit))
        else:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.category,
                    t.platform_requirements,
                    t.node_power_reward,
                    t.max_completions,
                    COUNT(DISTINCT ut.user_id) as completion_count,
                    SUM(COALESCE(ut.view_count, 0)) as total_view_count,
                    SUM(COALESCE(ut.like_count, 0)) as total_like_count,
                    MAX(ut.submitted_at) as latest_completed_at,
                    MIN(ut.submitted_at) as earliest_completed_at,
                    MAX(ut.view_count_updated_at) as view_count_updated_at
                FROM user_tasks ut
                JOIN drama_tasks t ON ut.task_id = t.task_id
                WHERE ut.status = 'submitted'
                GROUP BY t.task_id, t.external_task_id, t.project_id, t.title, t.category, t.platform_requirements, t.node_power_reward, t.max_completions
                ORDER BY MAX(ut.submitted_at) DESC
                LIMIT %s
            """, (limit,))
        
        tasks = cur.fetchall()
        
        # 为每个任务获取完成者详情
        result_data = []
        for task in tasks:
            task_id = task['task_id']
            
            # 获取该任务的所有完成者
            cur.execute("""
                SELECT 
                    ut.user_id,
                    u.username,
                    u.first_name,
                    ut.submission_link,
                    ut.submitted_at as completed_at,
                    COALESCE(ut.view_count, 0) as view_count,
                    COALESCE(ut.like_count, 0) as like_count,
                    ut.view_count_updated_at,
                    EXTRACT(EPOCH FROM (ut.submitted_at - ut.created_at)) as duration_seconds,
                    COALESCE(ut.node_power_earned, 0) as earned_reward
                FROM user_tasks ut
                LEFT JOIN users u ON ut.user_id = u.user_id
                WHERE ut.task_id = %s AND ut.status = 'submitted'
                ORDER BY ut.submitted_at ASC
            """, (task_id,))
            
            completers = cur.fetchall()
            
            # 格式化完成者数据
            completers_list = []
            for c in completers:
                display_name = c.get('first_name') or c.get('username') or f"User_{c['user_id']}"
                completers_list.append({
                    'user_id': c['user_id'],
                    'display_name': display_name,
                    'submission_link': c['submission_link'],
                    'completed_at': c['completed_at'].isoformat() if c['completed_at'] else None,
                    'view_count': c['view_count'],
                    'like_count': c['like_count'],
                    'view_count_updated_at': c['view_count_updated_at'].isoformat() if c.get('view_count_updated_at') else None,
                    'duration_seconds': c['duration_seconds'],
                    'earned_reward': c['earned_reward']  # 实际获得的 X2C 奖励
                })
            
            # 计算所有完成者的总奖励
            total_earned = sum(c.get('earned_reward', 0) for c in completers_list)
            
            # 获取基础奖励配置
            reward_config = get_reward_config()
            base_reward = reward_config.get('task_reward_x2c', 100)
            
            # 构建任务数据
            task_data = {
                'task_id': task['task_id'],
                'external_task_id': task['external_task_id'],
                'project_id': task['project_id'],
                'title': task['title'],
                'category': task['category'],
                'platform_requirements': task['platform_requirements'],
                'node_power_reward': task['node_power_reward'],
                'max_completions': task['max_completions'] or 100,  # 默认 100
                'completion_count': task['completion_count'],
                'total_view_count': task['total_view_count'] or 0,
                'total_like_count': task['total_like_count'] or 0,
                'latest_completed_at': task['latest_completed_at'].isoformat() if task['latest_completed_at'] else None,
                'earliest_completed_at': task['earliest_completed_at'].isoformat() if task['earliest_completed_at'] else None,
                'view_count_updated_at': task['view_count_updated_at'].isoformat() if task.get('view_count_updated_at') else None,
                'completers': completers_list,
                'base_reward_x2c': base_reward,  # 基础奖励
                'total_earned_reward': total_earned  # 所有完成者的总奖励
            }
            result_data.append(task_data)
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': result_data,
            'count': len(result_data)
        })
    
    except Exception as e:
        logger.error(f"获取完成日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/webhooks', methods=['GET'])
def get_webhook_logs():
    """
    获取 Webhook 回调日志
    从webhook_logs表读取真实的回调记录（如果表存在）
    """
    try:
        limit = int(request.args.get('limit', 100))
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查webhook_logs表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'webhook_logs'
            )
        """)
        table_exists = cur.fetchone()['exists']
        logger.info(f"🔍 [DEBUG] webhook_logs表存在: {table_exists}, hours={hours}, limit={limit}")
        
        # 如果表存在，从 webhook_logs 读取（按任务ID分组，只显示最新的一条回调记录，按回调时间降序排列）
        if table_exists:
            if hours > 0:
                cur.execute("""
                    WITH latest_webhooks AS (
                        SELECT DISTINCT ON (task_id)
                            id,
                            task_id,
                            task_title,
                            project_id,
                            callback_url,
                            callback_status,
                            payload,
                            created_at
                        FROM webhook_logs
                        WHERE created_at >= NOW() - INTERVAL '%s hours'
                        ORDER BY task_id, created_at DESC
                    ),
                    callback_counts AS (
                        SELECT task_id, COUNT(*) as callback_count
                        FROM webhook_logs
                        WHERE created_at >= NOW() - INTERVAL '%s hours'
                        GROUP BY task_id
                    ),
                    task_completion_times AS (
                        SELECT task_id, MAX(submitted_at) as latest_completed_at
                        FROM user_tasks
                        WHERE status = 'submitted'
                        GROUP BY task_id
                    )
                    SELECT 
                        lw.id,
                        lw.task_id,
                        lw.task_title as title,
                        lw.project_id,
                        lw.callback_url,
                        lw.callback_status,
                        lw.payload,
                        lw.created_at,
                        t.external_task_id,
                        t.callback_retry_count,
                        t.callback_last_attempt,
                        t.video_url,
                        COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count,
                        COALESCE(cc.callback_count, 1) as callback_count,
                        tct.latest_completed_at
                    FROM latest_webhooks lw
                    LEFT JOIN drama_tasks t ON lw.task_id = t.task_id
                    LEFT JOIN user_tasks ut ON lw.task_id = ut.task_id
                    LEFT JOIN callback_counts cc ON lw.task_id = cc.task_id
                    LEFT JOIN task_completion_times tct ON lw.task_id = tct.task_id
                    GROUP BY lw.id, lw.task_id, lw.task_title, lw.project_id, lw.callback_url, 
                             lw.callback_status, lw.payload, lw.created_at, t.external_task_id,
                             t.callback_retry_count, t.callback_last_attempt, t.video_url, cc.callback_count, tct.latest_completed_at
                    ORDER BY tct.latest_completed_at DESC NULLS LAST
                    LIMIT %s
                """, (hours, hours, limit))
            else:
                cur.execute("""
                    WITH latest_webhooks AS (
                        SELECT DISTINCT ON (task_id)
                            id,
                            task_id,
                            task_title,
                            project_id,
                            callback_url,
                            callback_status,
                            payload,
                            created_at
                        FROM webhook_logs
                        ORDER BY task_id, created_at DESC
                    ),
                    callback_counts AS (
                        SELECT task_id, COUNT(*) as callback_count
                        FROM webhook_logs
                        GROUP BY task_id
                    ),
                    task_completion_times AS (
                        SELECT task_id, MAX(submitted_at) as latest_completed_at
                        FROM user_tasks
                        WHERE status = 'submitted'
                        GROUP BY task_id
                    )
                    SELECT 
                        lw.id,
                        lw.task_id,
                        lw.task_title as title,
                        lw.project_id,
                        lw.callback_url,
                        lw.callback_status,
                        lw.payload,
                        lw.created_at,
                        t.external_task_id,
                        t.callback_retry_count,
                        t.callback_last_attempt,
                        t.video_url,
                        COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count,
                        COALESCE(cc.callback_count, 1) as callback_count,
                        tct.latest_completed_at
                    FROM latest_webhooks lw
                    LEFT JOIN drama_tasks t ON lw.task_id = t.task_id
                    LEFT JOIN user_tasks ut ON lw.task_id = ut.task_id
                    LEFT JOIN callback_counts cc ON lw.task_id = cc.task_id
                    LEFT JOIN task_completion_times tct ON lw.task_id = tct.task_id
                    GROUP BY lw.id, lw.task_id, lw.task_title, lw.project_id, lw.callback_url, 
                             lw.callback_status, lw.payload, lw.created_at, t.external_task_id,
                             t.callback_retry_count, t.callback_last_attempt, t.video_url, cc.callback_count, tct.latest_completed_at
                    ORDER BY tct.latest_completed_at DESC NULLS LAST
                    LIMIT %s
                """, (limit,))
            
            webhooks = cur.fetchall()
            
            # 调试日志：输出查询到的记录数
            logger.info(f"🔍 [DEBUG] 查询到的webhook记录数: {len(webhooks)}")
            
            # 查询总记录数
            cur.execute("SELECT COUNT(*) as total FROM webhook_logs")
            total_count = cur.fetchone()['total']
            logger.info(f"🔍 [DEBUG] webhook_logs表总记录数: {total_count}")
            
            # 转换日期格式
            for webhook in webhooks:
                if webhook['created_at']:
                    webhook['created_at'] = webhook['created_at'].isoformat()
                if webhook.get('callback_last_attempt'):
                    webhook['callback_last_attempt'] = webhook['callback_last_attempt'].isoformat()
                
                # 添加状态标签
                if webhook['callback_status'] == 'success':
                    webhook['status_label'] = '✅ 成功'
                    webhook['status_class'] = 'success'
                else:
                    webhook['status_label'] = '❌ 失败'
                    webhook['status_class'] = 'danger'
                
                # payload已经是JSONB格式
                webhook['callback_payload'] = webhook.get('payload', {})
                
                # 从 user_tasks 表获取播放量数据（而不是从 payload 中获取）
                task_id_for_view = webhook.get('task_id')
                if task_id_for_view:
                    cur_view = conn.cursor()
                    cur_view.execute("""
                        SELECT COALESCE(SUM(view_count), 0) as total_views
                        FROM user_tasks
                        WHERE task_id = %s AND status = 'submitted'
                    """, (task_id_for_view,))
                    view_result = cur_view.fetchone()
                    webhook['view_count'] = view_result['total_views'] if view_result else 0
                    cur_view.close()
                else:
                    webhook['view_count'] = 0
                
                # 查询用户分发链接
                task_id = webhook.get('task_id')
                if task_id:
                    cur2 = conn.cursor()
                    cur2.execute("""
                        SELECT 
                            user_id,
                            submission_link as video_url,
                            submitted_at
                        FROM user_tasks
                        WHERE task_id = %s AND status = 'submitted' AND submission_link IS NOT NULL
                        ORDER BY submitted_at ASC
                    """, (task_id,))
                    
                    user_submissions = cur2.fetchall()
                    webhook['user_submissions'] = [
                        {
                            'user_id': str(sub['user_id']),
                            'video_url': sub['video_url'],
                            'submitted_at': sub['submitted_at'].isoformat() if sub['submitted_at'] else None
                        }
                        for sub in user_submissions
                    ]
                    cur2.close()
                else:
                    webhook['user_submissions'] = []
            
            cur.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'data': webhooks,
                'count': len(webhooks),
                'source': 'webhook_logs'
            })
        
        # 如果表不存在，使用原来的逻辑（从 drama_tasks 读取）
        
        # 查询有回调配置的任务
        if hours > 0:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.duration,
                    t.platform_requirements,
                    t.callback_url,
                    t.callback_status,
                    t.callback_retry_count,
                    t.callback_last_attempt,
                    t.created_at,
                    t.video_url,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
                FROM drama_tasks t
                LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
                WHERE t.callback_url IS NOT NULL
                    AND t.created_at >= NOW() - INTERVAL '%s hours'
                GROUP BY t.task_id
                ORDER BY t.callback_last_attempt DESC NULLS LAST, t.created_at DESC
                LIMIT %s
            """, (hours, limit))
        else:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.duration,
                    t.platform_requirements,
                    t.callback_url,
                    t.callback_status,
                    t.callback_retry_count,
                    t.callback_last_attempt,
                    t.created_at,
                    t.video_url,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
                FROM drama_tasks t
                LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
                WHERE t.callback_url IS NOT NULL
                GROUP BY t.task_id
                ORDER BY t.callback_last_attempt DESC NULLS LAST, t.created_at DESC
                LIMIT %s
            """, (limit,))
        
        webhooks = cur.fetchall()
        
        # 转换日期格式
        for webhook in webhooks:
            if webhook['created_at']:
                webhook['created_at'] = webhook['created_at'].isoformat()
            if webhook['callback_last_attempt']:
                webhook['callback_last_attempt'] = webhook['callback_last_attempt'].isoformat()
            
            # 添加状态标签
            if webhook['callback_status'] == 'success':
                webhook['status_label'] = '✅ 成功'
                webhook['status_class'] = 'success'
            elif webhook['callback_status'] == 'failed':
                webhook['status_label'] = '❌ 失败'
                webhook['status_class'] = 'danger'
            elif webhook['callback_retry_count'] and webhook['callback_retry_count'] > 0:
                webhook['status_label'] = f"🔄 重试中 ({webhook['callback_retry_count']}/3)"
                webhook['status_class'] = 'warning'
            else:
                webhook['status_label'] = '⏳ 待回调'
                webhook['status_class'] = 'secondary'
            
            # 生成回调数据示例
            platform = webhook.get('platform_requirements', '').lower()
            stats_data = {
                'project_id': webhook.get('project_id'),
                'task_id': webhook.get('external_task_id') or webhook.get('task_id'),
                'duration': webhook.get('duration', 30),
                'account_count': 1
            }
            
            # 根据平台添加示例字段
            if 'youtube' in platform or 'yt' in platform:
                stats_data['yt_account_count'] = 1
                # 可以添加示例数据
                # stats_data['yt_view_count'] = 0
                # stats_data['yt_like_count'] = 0
            elif 'tiktok' in platform or 'tt' in platform:
                stats_data['tt_account_count'] = 1
                # stats_data['tt_view_count'] = 0
                # stats_data['tt_like_count'] = 0
            
            webhook['callback_payload'] = {
                'site_name': 'DramaRelayBot',
                'stats': [stats_data]
            }
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': webhooks,
            'count': len(webhooks)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/stats', methods=['GET'])
def get_stats():
    """
    获取统计数据
    """
    try:
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 任务统计 - 如果 hours 为 0 或负数，则查询所有数据
        if hours > 0:
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT t.task_id) as total_tasks,
                    COUNT(DISTINCT ut.user_id) as total_users,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_users,
                    COUNT(DISTINCT CASE WHEN t.callback_status = 'success' THEN t.task_id END) as successful_callbacks,
                    COUNT(DISTINCT CASE WHEN t.callback_status = 'failed' THEN t.task_id END) as failed_callbacks
                FROM drama_tasks t
                LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
                WHERE t.created_at >= NOW() - INTERVAL '%s hours'
            """, (hours,))
        else:
            # 查询所有数据（不限时间）
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT t.task_id) as total_tasks,
                    COUNT(DISTINCT ut.user_id) as total_users,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_users,
                    COUNT(DISTINCT CASE WHEN t.callback_status = 'success' THEN t.task_id END) as successful_callbacks,
                    COUNT(DISTINCT CASE WHEN t.callback_status = 'failed' THEN t.task_id END) as failed_callbacks
                FROM drama_tasks t
                LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
            """)
        
        stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config/api-key', methods=['GET'])
def get_api_key():
    """
    获取 API Key
    用于外部系统集成
    """
    try:
        api_key = os.getenv('API_KEY') or 'x2c_admin_secret_key_2024'
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API Key 未配置'
            }), 404
        
        return jsonify({
            'success': True,
            'api_key': api_key
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>/fix-status', methods=['POST'])
def fix_task_status(task_id):
    """
    修复任务状态：将 'approved' 改为 'active'
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询任务当前状态
        cur.execute("""
            SELECT task_id, title, status
            FROM drama_tasks
            WHERE task_id = %s
        """, (task_id,))
        
        task = cur.fetchone()
        
        if not task:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'任务 {task_id} 不存在'
            }), 404
        
        old_status = task['status']
        
        if old_status == 'active':
            cur.close()
            conn.close()
            return jsonify({
                'success': True,
                'message': f'任务 {task_id} 状态已经是 active，无需修复',
                'task_id': task_id,
                'title': task['title'],
                'old_status': old_status,
                'new_status': 'active'
            })
        
        # 更新任务状态为 'active'
        cur.execute("""
            UPDATE drama_tasks
            SET status = 'active'
            WHERE task_id = %s
            RETURNING task_id, title, status
        """, (task_id,))
        
        updated_task = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'任务 {task_id} 状态已修复',
            'task_id': updated_task['task_id'],
            'title': updated_task['title'],
            'old_status': old_status,
            'new_status': updated_task['status']
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/fix-all-approved', methods=['POST'])
def fix_all_approved_tasks():
    """
    批量修复所有 'approved' 状态的任务为 'active'
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询所有 approved 状态的任务
        cur.execute("""
            SELECT task_id, title, status
            FROM drama_tasks
            WHERE status = 'approved'
            ORDER BY created_at DESC
        """)
        
        tasks = cur.fetchall()
        
        if not tasks:
            cur.close()
            conn.close()
            return jsonify({
                'success': True,
                'message': '没有找到 approved 状态的任务',
                'count': 0,
                'tasks': []
            })
        
        # 批量更新为 active 状态
        cur.execute("""
            UPDATE drama_tasks
            SET status = 'active'
            WHERE status = 'approved'
            RETURNING task_id, title, status
        """)
        
        updated_tasks = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'已修复 {len(updated_tasks)} 个任务',
            'count': len(updated_tasks),
            'tasks': [{
                'task_id': task['task_id'],
                'title': task['title'],
                'new_status': task['status']
            } for task in updated_tasks]
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/broadcaster/start', methods=['POST'])
def start_broadcaster_api():
    """
    启动分发数据回传服务
    """
    try:
        from stats_broadcaster import start_broadcaster
        success = start_broadcaster()
        
        if success:
            return jsonify({
                'success': True,
                'message': '分发数据回传服务已启动，每3分钟自动回传一次'
            })
        else:
            return jsonify({
                'success': False,
                'message': '分发数据回传服务已在运行中'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/broadcaster/stop', methods=['POST'])
def stop_broadcaster_api():
    """
    停止分发数据回传服务
    """
    try:
        from stats_broadcaster import stop_broadcaster
        success = stop_broadcaster()
        
        if success:
            return jsonify({
                'success': True,
                'message': '分发数据回传服务已停止'
            })
        else:
            return jsonify({
                'success': False,
                'message': '分发数据回传服务未运行'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/broadcaster/status', methods=['GET'])
def get_broadcaster_status_api():
    """
    获取分发数据回传服务状态
    """
    try:
        from stats_broadcaster import get_broadcaster_status
        status = get_broadcaster_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/errors', methods=['GET'])
def get_error_logs():
    """
    获取回传错误日志
    """
    try:
        # 获取查询参数
        limit = int(request.args.get('limit', 50))
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 计算时间范围
        if hours > 0:
            time_filter = f"WHERE created_at >= NOW() - INTERVAL '{hours} hours'"
        else:
            time_filter = ""
        
        # 查询错误日志
        query = f"""
            SELECT 
                id,
                task_id,
                task_title,
                project_id,
                video_url,
                platform,
                error_type,
                error_message,
                callback_url,
                created_at
            FROM broadcaster_error_logs
            {time_filter}
            ORDER BY created_at DESC
            LIMIT %s
        """
        
        cur.execute(query, (limit,))
        logs = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'data': logs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/broadcaster/trigger', methods=['POST'])
def trigger_broadcaster_api():
    """
    手动触发一次分发数据回传
    """
    try:
        from stats_broadcaster import broadcast_all_tasks
        import asyncio
        import traceback
        
        # 运行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(broadcast_all_tasks())
        loop.close()
        
        # 检查内部结果是否成功
        if result and result.get('success') == False:
            # 内部失败，返回详细错误信息
            return jsonify({
                'success': False,
                'error': result.get('error', '内部错误'),
                'data': result
            })
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ 触发回传异常: {e}\n{error_trace}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500

@app.route('/api/admin/delete_tasks', methods=['POST'])
def delete_tasks():
    """
    删除指定的任务及相关数据
    需要API Key验证
    """
    try:
        # 验证API Key
        api_key = request.args.get('api_key') or request.headers.get('X-API-Key')
        if api_key != 'x2c_admin_secret_key_2024':
            return jsonify({
                'success': False,
                'error': 'Unauthorized: Invalid API key'
            }), 401
        
        # 获取要删除的任务ID
        data = request.get_json()
        if not data or 'task_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing task_ids in request body'
            }), 400
        
        task_ids = data.get('task_ids', [])
        if not task_ids or not isinstance(task_ids, list):
            return jsonify({
                'success': False,
                'error': 'task_ids must be a non-empty list'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询要删除的任务信息（用于日志）
        cur.execute("""
            SELECT task_id, title FROM drama_tasks WHERE task_id IN %s
        """, (tuple(task_ids),))
        tasks_to_delete = cur.fetchall()
        
        if not tasks_to_delete:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'No tasks found with the provided IDs'
            }), 404
        
        # 1. 删除推荐奖励记录（外键约束）
        cur.execute("""
            DELETE FROM referral_rewards WHERE task_id IN %s
        """, (tuple(task_ids),))
        referral_rewards_deleted = cur.rowcount
        
        # 2. 删除错误日志
        cur.execute("""
            DELETE FROM broadcaster_error_logs WHERE task_id IN %s
        """, (tuple(task_ids),))
        error_logs_deleted = cur.rowcount
        
        # 3. 删除每日统计
        cur.execute("""
            DELETE FROM task_daily_stats WHERE task_id IN %s
        """, (tuple(task_ids),))
        daily_stats_deleted = cur.rowcount
        
        # 4. 删除完成记录（注意：完成记录存储在 user_tasks 表中）
        # 不需要单独删除，因为 user_tasks 就是完成记录
        completions_deleted = 0  # 不存在单独的 task_completions 表
        
        # 5. 删除用户任务关联
        cur.execute("""
            DELETE FROM user_tasks WHERE task_id IN %s
        """, (tuple(task_ids),))
        user_tasks_deleted = cur.rowcount
        
        # 6. 删除任务本身
        cur.execute("""
            DELETE FROM drama_tasks WHERE task_id IN %s
        """, (tuple(task_ids),))
        tasks_deleted = cur.rowcount
        
        # 提交事务
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {tasks_deleted} tasks and related data',
            'deleted': {
                'tasks': tasks_deleted,
                'referral_rewards': referral_rewards_deleted,
                'error_logs': error_logs_deleted,
                'daily_stats': daily_stats_deleted,
                'completions': completions_deleted,
                'user_tasks': user_tasks_deleted
            },
            'deleted_tasks': [dict(task) for task in tasks_to_delete]
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/admin/update_callback_url', methods=['POST'])
def update_callback_url():
    """
    批量更新callback_url
    """
    try:
        # 验证API Key
        api_key = request.args.get('api_key')
        if api_key != 'x2c_admin_secret_key_2024':
            return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
        # 获取请求参数
        data = request.get_json()
        old_url_pattern = data.get('old_url_pattern', '%rxkcgquecleofqhyfchx.supabase.co%')
        new_url = data.get('new_url', 'https://eumfmgwxwjyagsvqloac.supabase.co/functions/v1/distribution-callback')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询需要更新的任务
        cur.execute("""
            SELECT task_id, title, callback_url
            FROM drama_tasks
            WHERE callback_url LIKE %s
        """, (old_url_pattern,))
        
        tasks_to_update = cur.fetchall()
        
        if not tasks_to_update:
            cur.close()
            conn.close()
            return jsonify({
                'success': True,
                'message': 'No tasks found with the old callback URL',
                'updated_count': 0
            })
        
        # 执行更新
        cur.execute("""
            UPDATE drama_tasks
            SET callback_url = %s
            WHERE callback_url LIKE %s
        """, (new_url, old_url_pattern))
        
        updated_count = cur.rowcount
        
        # 提交事务
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully updated {updated_count} tasks',
            'updated_count': updated_count,
            'old_url_pattern': old_url_pattern,
            'new_url': new_url,
            'updated_tasks': [dict(task) for task in tasks_to_update]
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/admin/migrate_categories', methods=['POST'])
def migrate_categories():
    """
    迁移旧的category值到X2C分类
    将不在X2C分类列表中的category设置为NULL
    """
    try:
        # X2C分类列表
        x2c_categories = [
            'latest',
            'billionaireRomance',
            'underdogRevenge',
            'werewolfVampire',
            'rebirthTimeTravel',
            'periodCostume',
            'marriageBetrayal',
            'fantasyMysticism',
            'suspenseCrime',
            'sciFiApocalypse',
            'urbanLife',
            'generalMixed',
            '霸总甘宠',
            '仙侠奇幻'
        ]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询当前category分布
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM drama_tasks 
            WHERE status = 'active' 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        old_distribution = cur.fetchall()
        
        # 更新旧的category为NULL
        cur.execute("""
            UPDATE drama_tasks 
            SET category = NULL 
            WHERE category IS NOT NULL 
            AND category NOT IN %s
        """, (tuple(x2c_categories),))
        
        affected_rows = cur.rowcount
        
        # 提交更改
        conn.commit()
        
        # 查询更新后的category分布
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM drama_tasks 
            WHERE status = 'active' 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        new_distribution = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'已将 {affected_rows} 个旧任务的category设置为NULL',
            'affected_rows': affected_rows,
            'old_distribution': [dict(row) for row in old_distribution],
            'new_distribution': [dict(row) for row in new_distribution]
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/tasks/search', methods=['GET'])
def search_tasks():
    """搜索任务"""
    try:
        title = request.args.get('title', '')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT *
            FROM drama_tasks
            WHERE title LIKE %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (f'%{title}%',))
        
        tasks = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # 转换datetime对象为字符串
        tasks_data = []
        for task in tasks:
            task_dict = dict(task)
            for key, value in task_dict.items():
                if isinstance(value, datetime):
                    task_dict[key] = value.isoformat()
            tasks_data.append(task_dict)
        
        return jsonify({
            'success': True,
            'count': len(tasks_data),
            'data': tasks_data
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/verification/queue-status', methods=['GET'])
def get_verification_queue_status():
    """
    获取TikTok验证队列状态
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询待验证的任务数量
        cur.execute("""
            SELECT COUNT(*) as pending_count
            FROM pending_verifications
            WHERE status = 'pending'
        """)
        pending_count = cur.fetchone()['pending_count']
        
        # 查询正在处理的任务数量
        cur.execute("""
            SELECT COUNT(*) as processing_count
            FROM pending_verifications
            WHERE status = 'processing'
        """)
        processing_count = cur.fetchone()['processing_count']
        
        # 查询最近完成的任务数量（24小时内）
        cur.execute("""
            SELECT COUNT(*) as completed_count
            FROM pending_verifications
            WHERE status = 'completed'
              AND completed_at >= NOW() - INTERVAL '24 hours'
        """)
        completed_count = cur.fetchone()['completed_count']
        
        # 查询最近失败的任务数量（24小时内）
        cur.execute("""
            SELECT COUNT(*) as failed_count
            FROM pending_verifications
            WHERE status = 'failed'
              AND updated_at >= NOW() - INTERVAL '24 hours'
        """)
        failed_count = cur.fetchone()['failed_count']
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'pending': pending_count,
                'processing': processing_count,
                'completed_24h': completed_count,
                'failed_24h': failed_count,
                'total_queue': pending_count + processing_count
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/clear-all', methods=['POST'])
def clear_all_logs():
    """
    清空所有日志数据（webhook_logs, broadcaster_error_logs, user_tasks中的submitted记录, drama_tasks）
    需要确认才能执行
    """
    try:
        # 获取确认参数
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'success': False,
                'error': '需要确认才能清空日志，请设置 confirm: true'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        deleted_counts = {}
        
        # 1. 清空 webhook_logs 表
        cur.execute("DELETE FROM webhook_logs")
        deleted_counts['webhook_logs'] = cur.rowcount
        
        # 2. 清空 broadcaster_error_logs 表
        cur.execute("DELETE FROM broadcaster_error_logs")
        deleted_counts['broadcaster_error_logs'] = cur.rowcount
        
        # 3. 清空 user_tasks 表（任务完成日志）
        cur.execute("DELETE FROM user_tasks")
        deleted_counts['user_tasks'] = cur.rowcount
        
        # 4. 清空 drama_tasks 表（任务接收日志）
        cur.execute("DELETE FROM drama_tasks")
        deleted_counts['drama_tasks'] = cur.rowcount
        
        # 5. 清空 task_daily_stats 表（如果存在）
        try:
            cur.execute("DELETE FROM task_daily_stats")
            deleted_counts['task_daily_stats'] = cur.rowcount
        except:
            deleted_counts['task_daily_stats'] = 0
        
        # 6. 清空 referral_rewards 表（如果存在）
        try:
            cur.execute("DELETE FROM referral_rewards")
            deleted_counts['referral_rewards'] = cur.rowcount
        except:
            deleted_counts['referral_rewards'] = 0
        
        # 提交事务
        conn.commit()
        
        cur.close()
        conn.close()
        
        total_deleted = sum(deleted_counts.values())
        
        return jsonify({
            'success': True,
            'message': f'已清空所有日志，共删除 {total_deleted} 条记录',
            'deleted': deleted_counts
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def get_withdrawal_requests():
    """
    获取提现申请列表
    """
    try:
        status = request.args.get('status', 'pending')  # pending, approved, rejected, completed, all
        limit = int(request.args.get('limit', 50))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if status == 'all':
            cur.execute("""
                SELECT 
                    w.withdrawal_id,
                    w.user_id,
                    w.sol_address,
                    w.amount,
                    w.status,
                    w.tx_hash,
                    w.error_message,
                    w.created_at,
                    w.processed_at,
                    u.username,
                    u.first_name,
                    u.total_node_power as current_balance
                FROM withdrawals w
                LEFT JOIN users u ON w.user_id = u.user_id
                ORDER BY w.created_at DESC
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT 
                    w.withdrawal_id,
                    w.user_id,
                    w.sol_address,
                    w.amount,
                    w.status,
                    w.tx_hash,
                    w.error_message,
                    w.created_at,
                    w.processed_at,
                    u.username,
                    u.first_name,
                    u.total_node_power as current_balance
                FROM withdrawals w
                LEFT JOIN users u ON w.user_id = u.user_id
                WHERE w.status = %s
                ORDER BY w.created_at DESC
                LIMIT %s
            """, (status, limit))
        
        withdrawals = cur.fetchall()
        
        # 获取各状态的统计
        cur.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total_amount
            FROM withdrawals
            GROUP BY status
        """)
        stats_rows = cur.fetchall()
        stats = {row['status']: {'count': row['count'], 'total_amount': float(row['total_amount'])} for row in stats_rows}
        
        cur.close()
        conn.close()
        
        # 转换为列表
        result = []
        for w in withdrawals:
            result.append({
                'withdrawal_id': w['withdrawal_id'],
                'user_id': w['user_id'],
                'username': w['username'] or '',
                'first_name': w['first_name'] or '',
                'sol_address': w['sol_address'],
                'amount': float(w['amount']),
                'status': w['status'],
                'tx_hash': w['tx_hash'] or '',
                'error_message': w['error_message'] or '',
                'created_at': w['created_at'].isoformat() if w['created_at'] else '',
                'processed_at': w['processed_at'].isoformat() if w['processed_at'] else '',
                'current_balance': float(w['current_balance']) if w['current_balance'] else 0
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'stats': stats
        })
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to get withdrawal requests: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def approve_withdrawal(withdrawal_id):
    """
    审批提现申请（执行转账）
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取提现请求信息
        cur.execute("""
            SELECT withdrawal_id, user_id, sol_address, amount, status
            FROM withdrawals
            WHERE withdrawal_id = %s
        """, (withdrawal_id,))
        
        withdrawal = cur.fetchone()
        
        if not withdrawal:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': '提现申请不存在'}), 404
        
        # 支持 pending 和 processing 状态的审批
        if withdrawal['status'] not in ('pending', 'processing'):
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': f'提现申请状态不正确，当前状态: {withdrawal["status"]}'}), 400
        
        # 直接更新状态为 processing
        cur.execute("""
            UPDATE withdrawals
            SET status = 'processing'
            WHERE withdrawal_id = %s
        """, (withdrawal_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        # 执行真实 Solana 转账
        from solana_transfer import execute_solana_transfer
        tx_hash = execute_solana_transfer(
            to_address=withdrawal['sol_address'],
            amount=str(withdrawal['amount']),
            withdrawal_id=withdrawal_id,
            asset_type=withdrawal.get('asset_type', 'x2c')
        )
        
        if not tx_hash:
            # 转账失败，更新状态为 failed
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE withdrawals
                SET status = 'failed',
                    error_message = 'Solana transfer failed',
                    processed_at = CURRENT_TIMESTAMP
                WHERE withdrawal_id = %s
            """, (withdrawal_id,))
            conn.commit()
            cur.close()
            conn.close()
            
            logger.error(f"❌ Solana transfer failed: withdrawal_id={withdrawal_id}")
            return jsonify({
                'success': False,
                'error': 'Solana transfer failed'
            }), 500
        
        # 更新提现记录为 completed
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE withdrawals
            SET status = 'completed',
                tx_hash = %s,
                processed_at = CURRENT_TIMESTAMP
            WHERE withdrawal_id = %s
        """, (tx_hash, withdrawal_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Withdrawal approved and processed: withdrawal_id={withdrawal_id}, tx_hash={tx_hash}")
        
        # 通知 X2C Web 更新提现状态
        try:
            x2c_web_url = os.environ.get('X2C_WEB_WEBHOOK_URL', 'https://x2c-web.manus.space/api/webhook/withdrawal-status')
            x2c_web_api_key = os.environ.get('X2C_WEB_API_KEY', '')
            if x2c_web_api_key:
                requests.post(
                    x2c_web_url,
                    json={
                        'withdrawalId': withdrawal_id,
                        'status': 'completed',
                        'txHash': tx_hash,
                        'processedAt': datetime.now().isoformat()
                    },
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {x2c_web_api_key}'
                    },
                    timeout=5
                )
                logger.info(f"✅ Notified X2C Web about withdrawal status update: withdrawal_id={withdrawal_id}")
        except Exception as webhook_error:
            logger.warning(f"⚠️ Failed to notify X2C Web: {webhook_error}")
        
        return jsonify({
            'success': True,
            'message': '提现已审批并转账成功',
            'tx_hash': tx_hash
        })
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to approve withdrawal: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def reject_withdrawal(withdrawal_id):
    """
    拒绝提现申请（退还余额）
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', '管理员拒绝')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取提现请求信息
        cur.execute("""
            SELECT withdrawal_id, user_id, sol_address, amount, status
            FROM withdrawals
            WHERE withdrawal_id = %s
        """, (withdrawal_id,))
        
        withdrawal = cur.fetchone()
        
        if not withdrawal:
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': '提现申请不存在'}), 404
        
        if withdrawal['status'] != 'pending':
            cur.close()
            conn.close()
            return jsonify({'success': False, 'error': f'提现申请状态不正确，当前状态: {withdrawal["status"]}'}), 400
        
        # 更新状态为拒绝
        cur.execute("""
            UPDATE withdrawals
            SET status = 'rejected',
                error_message = %s,
                processed_at = CURRENT_TIMESTAMP
            WHERE withdrawal_id = %s
        """, (reason, withdrawal_id))
        
        # 退还用户余额
        cur.execute("""
            UPDATE users
            SET total_node_power = total_node_power + %s
            WHERE user_id = %s
        """, (withdrawal['amount'], withdrawal['user_id']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"❌ Withdrawal rejected: withdrawal_id={withdrawal_id}, reason={reason}")
        
        # 通知 X2C Web 更新提现状态
        try:
            x2c_web_url = os.environ.get('X2C_WEB_WEBHOOK_URL', 'https://x2c-web.manus.space/api/webhook/withdrawal-status')
            x2c_web_api_key = os.environ.get('X2C_WEB_API_KEY', '')
            if x2c_web_api_key:
                requests.post(
                    x2c_web_url,
                    json={
                        'withdrawalId': withdrawal_id,
                        'status': 'rejected',
                        'errorMessage': reason,
                        'processedAt': datetime.now().isoformat()
                    },
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {x2c_web_api_key}'
                    },
                    timeout=5
                )
                logger.info(f"✅ Notified X2C Web about withdrawal rejection: withdrawal_id={withdrawal_id}")
        except Exception as webhook_error:
            logger.warning(f"⚠️ Failed to notify X2C Web: {webhook_error}")
        
        return jsonify({
            'success': True,
            'message': f'提现申请已拒绝，已退还 {withdrawal["amount"]} X2C 到用户账户'
        })
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to reject withdrawal: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ==================== 用户增长和任务统计 API ====================

@app.route('/api/stats/user-growth', methods=['GET'])
def get_user_growth_stats():
    """
    获取用户增长统计数据
    区分 TG Bot 用户和 Web 用户
    支持按天/周/月统计
    """
    try:
        days = int(request.args.get('days', 30))  # 默认查询最近 30 天
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. TG Bot 用户每日增长
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_users
            FROM users
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (days,))
        tg_daily = cur.fetchall()
        
        # 2. Web 用户每日增长
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_users
            FROM web_users
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (days,))
        web_daily = cur.fetchall()
        
        # 3. 用户总数统计
        cur.execute("SELECT COUNT(*) as total FROM users")
        tg_total = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM web_users")
        web_total = cur.fetchone()['total']
        
        # 4. 最近 7 天新增用户
        cur.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        tg_7d = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count FROM web_users 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        web_7d = cur.fetchone()['count']
        
        # 5. 最近 30 天新增用户
        cur.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """)
        tg_30d = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count FROM web_users 
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """)
        web_30d = cur.fetchone()['count']
        
        cur.close()
        conn.close()
        
        # 转换日期格式
        for item in tg_daily:
            item['date'] = item['date'].isoformat() if item['date'] else None
        for item in web_daily:
            item['date'] = item['date'].isoformat() if item['date'] else None
        
        return jsonify({
            'success': True,
            'data': {
                'tg_bot': {
                    'total': tg_total,
                    'last_7_days': tg_7d,
                    'last_30_days': tg_30d,
                    'daily': list(tg_daily)
                },
                'web': {
                    'total': web_total,
                    'last_7_days': web_7d,
                    'last_30_days': web_30d,
                    'daily': list(web_daily)
                },
                'combined': {
                    'total': tg_total + web_total,
                    'last_7_days': tg_7d + web_7d,
                    'last_30_days': tg_30d + web_30d
                }
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to get user growth stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/stats/task-stats', methods=['GET'])
def get_task_stats():
    """
    获取任务数据统计
    包括任务领取、完成、奖励发放等
    """
    try:
        days = int(request.args.get('days', 30))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. 任务每日领取统计
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as claimed_count
            FROM user_tasks
            WHERE created_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """, (days,))
        daily_claimed = cur.fetchall()
        
        # 2. 任务每日完成统计
        cur.execute("""
            SELECT 
                DATE(submitted_at) as date,
                COUNT(*) as completed_count
            FROM user_tasks
            WHERE submitted_at IS NOT NULL
            AND submitted_at >= NOW() - INTERVAL '%s days'
            GROUP BY DATE(submitted_at)
            ORDER BY date ASC
        """, (days,))
        daily_completed = cur.fetchall()
        
        # 3. 任务总体统计
        cur.execute("""
            SELECT 
                COUNT(*) as total_claimed,
                COUNT(CASE WHEN status IN ('submitted', 'approved', 'completed') THEN 1 END) as total_completed,
                COUNT(CASE WHEN status = 'rejected' THEN 1 END) as total_rejected,
                COUNT(CASE WHEN status IN ('claimed', 'pending') THEN 1 END) as total_pending,
                COALESCE(SUM(node_power_earned), 0) as total_rewards
            FROM user_tasks
        """)
        task_totals = cur.fetchone()
        
        # 4. 最近 7 天任务统计
        cur.execute("""
            SELECT 
                COUNT(*) as claimed,
                COUNT(CASE WHEN status IN ('submitted', 'approved', 'completed') THEN 1 END) as completed,
                COALESCE(SUM(node_power_earned), 0) as rewards
            FROM user_tasks
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        task_7d = cur.fetchone()
        
        # 5. 最近 30 天任务统计
        cur.execute("""
            SELECT 
                COUNT(*) as claimed,
                COUNT(CASE WHEN status IN ('submitted', 'approved', 'completed') THEN 1 END) as completed,
                COALESCE(SUM(node_power_earned), 0) as rewards
            FROM user_tasks
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """)
        task_30d = cur.fetchone()
        
        # 6. 按状态分布
        cur.execute("""
            SELECT 
                status,
                COUNT(*) as count
            FROM user_tasks
            GROUP BY status
            ORDER BY count DESC
        """)
        status_distribution = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # 转换日期格式
        for item in daily_claimed:
            item['date'] = item['date'].isoformat() if item['date'] else None
        for item in daily_completed:
            item['date'] = item['date'].isoformat() if item['date'] else None
        
        return jsonify({
            'success': True,
            'data': {
                'totals': {
                    'claimed': task_totals['total_claimed'],
                    'completed': task_totals['total_completed'],
                    'rejected': task_totals['total_rejected'],
                    'pending': task_totals['total_pending'],
                    'rewards_distributed': int(task_totals['total_rewards'])
                },
                'last_7_days': {
                    'claimed': task_7d['claimed'],
                    'completed': task_7d['completed'],
                    'rewards': int(task_7d['rewards'])
                },
                'last_30_days': {
                    'claimed': task_30d['claimed'],
                    'completed': task_30d['completed'],
                    'rewards': int(task_30d['rewards'])
                },
                'daily_claimed': list(daily_claimed),
                'daily_completed': list(daily_completed),
                'status_distribution': list(status_distribution)
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to get task stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/stats/overview', methods=['GET'])
def get_stats_overview():
    """
    获取综合统计概览
    包括用户、任务、奖励等核心指标
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. 用户统计
        cur.execute("SELECT COUNT(*) as total FROM users")
        tg_users = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM web_users")
        web_users = cur.fetchone()['total']
        
        # 2. 任务统计
        cur.execute("SELECT COUNT(*) as total FROM drama_tasks WHERE status = 'active'")
        active_tasks = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as total FROM user_tasks")
        total_claimed = cur.fetchone()['total']
        
        cur.execute("""
            SELECT COUNT(*) as total FROM user_tasks 
            WHERE status IN ('submitted', 'approved', 'completed')
        """)
        total_completed = cur.fetchone()['total']
        
        # 3. 奖励统计
        cur.execute("SELECT COALESCE(SUM(node_power_earned), 0) as total FROM user_tasks")
        total_rewards = int(cur.fetchone()['total'])
        
        # 4. 今日统计
        cur.execute("""
            SELECT COUNT(*) as count FROM users 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        tg_today = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count FROM web_users 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        web_today = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count FROM user_tasks 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        tasks_today = cur.fetchone()['count']
        
        cur.execute("""
            SELECT COUNT(*) as count FROM user_tasks 
            WHERE DATE(submitted_at) = CURRENT_DATE
            AND status IN ('submitted', 'approved', 'completed')
        """)
        completed_today = cur.fetchone()['count']
        
        # 5. 提现统计
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COALESCE(SUM(CASE WHEN status = 'completed' THEN amount END), 0) as total_amount
            FROM withdrawals
        """)
        withdrawal_stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'users': {
                    'tg_bot': tg_users,
                    'web': web_users,
                    'total': tg_users + web_users,
                    'tg_today': tg_today,
                    'web_today': web_today,
                    'today_total': tg_today + web_today
                },
                'tasks': {
                    'active': active_tasks,
                    'total_claimed': total_claimed,
                    'total_completed': total_completed,
                    'completion_rate': round(total_completed / total_claimed * 100, 1) if total_claimed > 0 else 0,
                    'claimed_today': tasks_today,
                    'completed_today': completed_today
                },
                'rewards': {
                    'total_distributed': total_rewards,
                    'total_usd': round(total_rewards * 0.02, 2)  # X2C 价格 $0.02
                },
                'withdrawals': {
                    'total': withdrawal_stats['total'],
                    'completed': withdrawal_stats['completed'],
                    'pending': withdrawal_stats['pending'],
                    'total_amount': int(withdrawal_stats['total_amount'])
                }
            }
        })
        
    except Exception as e:
        import traceback
        logger.error(f"❌ Failed to get stats overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ==================== Solana 转账 Callback 处理 ====================

@app.route('/api/solana/callback', methods=['POST'])
def solana_callback():
    """
    处理 Giggle API 的 Solana 转账 Callback 回调
    
    Giggle API 在转账完成后会调用此端点通知转账结果
    """
    try:
        # 获取回调数据
        callback_data = request.get_json() or {}
        
        logger.info(f"[Callback] Received callback: batch_id={callback_data.get('batch_id')}")
        
        # 处理回调
        from solana_callback import process_callback
        result = process_callback(callback_data)
        
        if result['success']:
            logger.info(f"[Callback] Callback processed successfully: {result['message']}")
            # 返回成功响应
            return jsonify({
                'code': 0,
                'data': None,
                'msg': ''
            }), 200
        else:
            logger.error(f"[Callback] Callback processing failed: {result['message']}")
            # 返回失败响应（但仍然返回 200，让 Giggle 知道我们收到了请求）
            return jsonify({
                'code': 0,
                'data': None,
                'msg': ''
            }), 200
        
    except Exception as e:
        logger.error(f"[Callback] Failed to handle callback: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 返回成功响应，避免 Giggle 重试
        return jsonify({
            'code': 0,
            'data': None,
            'msg': ''
        }), 200


if __name__ == '__main__':
    port = int(os.getenv('ADMIN_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)


# ==================== 奖励设置 API ====================

@app.route('/api/settings/reward', methods=['GET'])
def get_reward_settings():
    """
    获取任务完成奖励设置
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 确保 bot_settings 表存在
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # 获取奖励设置
        cur.execute("""
            SELECT key, value, description, updated_at 
            FROM bot_settings 
            WHERE key IN ('task_reward_x2c', 'newcomer_bonus_multiplier', 'newcomer_bonus_enabled')
        """)
        settings = cur.fetchall()
        
        # 转换为字典
        result = {
            'task_reward_x2c': 100,  # 默认值
            'newcomer_bonus_multiplier': 50,  # 默认50倍
            'newcomer_bonus_enabled': True  # 默认开启
        }
        
        for s in settings:
            key = s['key']
            value = s['value']
            if key == 'newcomer_bonus_enabled':
                result[key] = value.lower() == 'true'
            elif key in ['task_reward_x2c', 'newcomer_bonus_multiplier']:
                result[key] = int(value)
            else:
                result[key] = value
            result[f'{key}_updated_at'] = s['updated_at'].isoformat() if s['updated_at'] else None
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get reward settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings/reward', methods=['POST'])
def update_reward_settings():
    """
    更新任务完成奖励设置
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 确保 bot_settings 表存在
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        updated_keys = []
        
        # 更新任务奖励 X2C 数量
        if 'task_reward_x2c' in data:
            reward = int(data['task_reward_x2c'])
            if reward < 1 or reward > 1000:
                return jsonify({
                    'success': False,
                    'error': '任务奖励必须在 1-1000 X2C 之间'
                }), 400
            
            cur.execute("""
                INSERT INTO bot_settings (key, value, description, updated_at)
                VALUES ('task_reward_x2c', %s, '每个任务完成奖励的 X2C 数量', CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
            """, (str(reward), str(reward)))
            updated_keys.append('task_reward_x2c')
        
        # 更新新手奖励倍数
        if 'newcomer_bonus_multiplier' in data:
            multiplier = int(data['newcomer_bonus_multiplier'])
            if multiplier < 1 or multiplier > 100:
                return jsonify({
                    'success': False,
                    'error': '新手奖励倍数必须在 1-100 之间'
                }), 400
            
            cur.execute("""
                INSERT INTO bot_settings (key, value, description, updated_at)
                VALUES ('newcomer_bonus_multiplier', %s, '新手首单奖励倍数', CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
            """, (str(multiplier), str(multiplier)))
            updated_keys.append('newcomer_bonus_multiplier')
        
        # 更新新手奖励开关
        if 'newcomer_bonus_enabled' in data:
            enabled = str(data['newcomer_bonus_enabled']).lower() == 'true'
            
            cur.execute("""
                INSERT INTO bot_settings (key, value, description, updated_at)
                VALUES ('newcomer_bonus_enabled', %s, '是否开启新手首单奖励', CURRENT_TIMESTAMP)
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = CURRENT_TIMESTAMP
            """, (str(enabled), str(enabled)))
            updated_keys.append('newcomer_bonus_enabled')
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Reward settings updated: {updated_keys}")
        
        return jsonify({
            'success': True,
            'message': f'成功更新设置: {", ".join(updated_keys)}',
            'updated_keys': updated_keys
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'无效的数值: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"❌ Failed to update reward settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings/all', methods=['GET'])
def get_all_settings():
    """
    获取所有系统设置
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取 bot_settings 表的所有设置
        cur.execute("""
            SELECT key, value, description, updated_at 
            FROM bot_settings 
            ORDER BY key
        """)
        bot_settings = cur.fetchall()
        
        # 获取 system_config 表的所有设置
        cur.execute("""
            SELECT config_key as key, config_value as value, updated_at 
            FROM system_config 
            ORDER BY config_key
        """)
        system_config = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # 格式化日期
        for s in bot_settings:
            if s['updated_at']:
                s['updated_at'] = s['updated_at'].isoformat()
        
        for s in system_config:
            if s['updated_at']:
                s['updated_at'] = s['updated_at'].isoformat()
        
        return jsonify({
            'success': True,
            'data': {
                'bot_settings': list(bot_settings),
                'system_config': list(system_config)
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to get all settings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# ==================== 任务最大完成次数编辑 API ====================

@app.route('/api/tasks/<int:task_id>/max-completions', methods=['PUT'])
def update_task_max_completions(task_id):
    """
    更新任务的最大可完成次数
    """
    try:
        data = request.get_json()
        
        if not data or 'max_completions' not in data:
            return jsonify({
                'success': False,
                'error': '缺少 max_completions 参数'
            }), 400
        
        max_completions = int(data['max_completions'])
        
        # 验证范围
        if max_completions < 1 or max_completions > 100000:
            return jsonify({
                'success': False,
                'error': '最大完成次数必须在 1-100000 之间'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查任务是否存在
        cur.execute("SELECT task_id, title, max_completions FROM drama_tasks WHERE task_id = %s", (task_id,))
        task = cur.fetchone()
        
        if not task:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'任务 {task_id} 不存在'
            }), 404
        
        old_value = task['max_completions'] or 100
        
        # 更新 max_completions
        cur.execute("""
            UPDATE drama_tasks 
            SET max_completions = %s 
            WHERE task_id = %s
        """, (max_completions, task_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Task {task_id} max_completions updated: {old_value} -> {max_completions}")
        
        return jsonify({
            'success': True,
            'message': f'任务 {task_id} 的最大完成次数已更新',
            'data': {
                'task_id': task_id,
                'title': task['title'],
                'old_value': old_value,
                'new_value': max_completions
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'无效的数值: {str(e)}'
        }), 400
    except Exception as e:
        logger.error(f"❌ Failed to update task max_completions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
