# -*- coding: utf-8 -*-
"""
管理页面 API
提供日志查询接口
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse
from datetime import datetime, timedelta

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
        if hours > 0:
            cur.execute("""
                SELECT 
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.description,
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
                    COUNT(DISTINCT ut.user_id) as assigned_users,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_users,
                    MAX(ut.submitted_at) as last_completed_at
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
                    COUNT(DISTINCT ut.user_id) as assigned_users,
                    COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_users,
                    MAX(ut.submitted_at) as last_completed_at
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
    包括：用户信息、完成时间、验证结果
    """
    try:
        limit = int(request.args.get('limit', 50))
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询最近完成的任务
        if hours > 0:
            cur.execute("""
                SELECT 
                    ut.user_id,
                    u.username,
                    u.first_name,
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.category,
                    t.platform_requirements,
                    t.node_power_reward,
                    ut.status,
                    ut.created_at as assigned_at,
                    ut.submitted_at as completed_at,
                    ut.submission_link,
                    EXTRACT(EPOCH FROM (ut.submitted_at - ut.created_at)) as duration_seconds
                FROM user_tasks ut
                JOIN drama_tasks t ON ut.task_id = t.task_id
                LEFT JOIN users u ON ut.user_id = u.user_id
                WHERE ut.status = 'submitted'
                    AND ut.submitted_at >= NOW() - INTERVAL '%s hours'
                ORDER BY ut.submitted_at DESC
                LIMIT %s
            """, (hours, limit))
        else:
            cur.execute("""
                SELECT 
                    ut.user_id,
                    u.username,
                    u.first_name,
                    t.task_id,
                    t.external_task_id,
                    t.project_id,
                    t.title,
                    t.category,
                    t.platform_requirements,
                    t.node_power_reward,
                    ut.status,
                    ut.created_at as assigned_at,
                    ut.submitted_at as completed_at,
                    ut.submission_link,
                    EXTRACT(EPOCH FROM (ut.submitted_at - ut.created_at)) as duration_seconds
                FROM user_tasks ut
                JOIN drama_tasks t ON ut.task_id = t.task_id
                LEFT JOIN users u ON ut.user_id = u.user_id
                WHERE ut.status = 'submitted'
                ORDER BY ut.submitted_at DESC
                LIMIT %s
            """, (limit,))
        
        completions = cur.fetchall()
        
        # 转换日期格式
        for completion in completions:
            if completion['assigned_at']:
                completion['assigned_at'] = completion['assigned_at'].isoformat()
            if completion['completed_at']:
                completion['completed_at'] = completion['completed_at'].isoformat()
            
            # 格式化用户名
            completion['display_name'] = completion.get('first_name') or completion.get('username') or f"User_{completion['user_id']}"
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': completions,
            'count': len(completions)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/logs/webhooks', methods=['GET'])
def get_webhook_logs():
    """
    获取 Webhook 回调日志
    包括：回调状态、重试次数、最后尝试时间
    """
    try:
        limit = int(request.args.get('limit', 50))
        hours = int(request.args.get('hours', 24))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
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

if __name__ == '__main__':
    port = int(os.getenv('ADMIN_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
