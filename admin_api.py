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
        
        # 如果表存在，从 webhook_logs 读取
        if table_exists:
            if hours > 0:
                cur.execute("""
                    SELECT 
                        wl.id,
                        wl.task_id,
                        wl.task_title as title,
                        wl.project_id,
                        wl.callback_url,
                        wl.callback_status,
                        wl.payload,
                        wl.created_at,
                        t.external_task_id,
                        t.callback_retry_count,
                        t.callback_last_attempt,
                        t.video_url,
                        COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
                    FROM webhook_logs wl
                    LEFT JOIN drama_tasks t ON wl.task_id = t.task_id
                    LEFT JOIN user_tasks ut ON wl.task_id = ut.task_id
                    WHERE wl.created_at >= NOW() - INTERVAL '%s hours'
                    GROUP BY wl.id, wl.task_id, wl.task_title, wl.project_id, wl.callback_url, 
                             wl.callback_status, wl.payload, wl.created_at, t.external_task_id,
                             t.callback_retry_count, t.callback_last_attempt, t.video_url
                    ORDER BY wl.created_at DESC
                    LIMIT %s
                """, (hours, limit))
            else:
                cur.execute("""
                    SELECT 
                        wl.id,
                        wl.task_id,
                        wl.task_title as title,
                        wl.project_id,
                        wl.callback_url,
                        wl.callback_status,
                        wl.payload,
                        wl.created_at,
                        t.external_task_id,
                        t.callback_retry_count,
                        t.callback_last_attempt,
                        t.video_url,
                        COUNT(DISTINCT CASE WHEN ut.status = 'submitted' THEN ut.user_id END) as completed_count
                    FROM webhook_logs wl
                    LEFT JOIN drama_tasks t ON wl.task_id = t.task_id
                    LEFT JOIN user_tasks ut ON wl.task_id = ut.task_id
                    GROUP BY wl.id, wl.task_id, wl.task_title, wl.project_id, wl.callback_url, 
                             wl.callback_status, wl.payload, wl.created_at, t.external_task_id,
                             t.callback_retry_count, t.callback_last_attempt, t.video_url
                    ORDER BY wl.created_at DESC
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
                
                # 从 payload 中提取 view_count
                payload = webhook.get('payload', {})
                stats = payload.get('stats', [])
                if stats and len(stats) > 0:
                    # 获取第一个 stats 的 view_count（每个 webhook 只包含一个任务）
                    webhook['view_count'] = stats[0].get('view_count', 0)
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
        
        # 运行异步任务
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(broadcast_all_tasks())
        loop.close()
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
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

if __name__ == '__main__':
    port = int(os.getenv('ADMIN_PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
