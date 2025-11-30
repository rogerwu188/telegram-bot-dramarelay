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
        cur.execute("""
            SELECT 
                t.task_id,
                t.external_task_id,
                t.project_id,
                t.title,
                t.platform_requirements,
                t.node_power_reward,
                t.status as task_status,
                t.created_at,
                COUNT(DISTINCT ut.user_id) as assigned_users,
                COUNT(DISTINCT CASE WHEN ut.status = 'completed' THEN ut.user_id END) as completed_users,
                MAX(ut.completed_at) as last_completed_at
            FROM drama_tasks t
            LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
            WHERE t.created_at >= NOW() - INTERVAL '%s hours'
            GROUP BY t.task_id
            ORDER BY t.created_at DESC
            LIMIT %s
        """, (hours, limit))
        
        tasks = cur.fetchall()
        
        # 转换日期格式
        for task in tasks:
            if task['created_at']:
                task['created_at'] = task['created_at'].isoformat()
            if task['last_completed_at']:
                task['last_completed_at'] = task['last_completed_at'].isoformat()
        
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
        cur.execute("""
            SELECT 
                ut.user_id,
                u.username,
                u.first_name,
                u.last_name,
                t.task_id,
                t.external_task_id,
                t.project_id,
                t.title,
                t.platform_requirements,
                t.node_power_reward,
                ut.status,
                ut.assigned_at,
                ut.completed_at,
                ut.submission_link,
                EXTRACT(EPOCH FROM (ut.completed_at - ut.assigned_at)) as duration_seconds
            FROM user_tasks ut
            JOIN drama_tasks t ON ut.task_id = t.task_id
            LEFT JOIN users u ON ut.user_id = u.user_id
            WHERE ut.status = 'completed'
                AND ut.completed_at >= NOW() - INTERVAL '%s hours'
            ORDER BY ut.completed_at DESC
            LIMIT %s
        """, (hours, limit))
        
        completions = cur.fetchall()
        
        # 转换日期格式
        for completion in completions:
            if completion['assigned_at']:
                completion['assigned_at'] = completion['assigned_at'].isoformat()
            if completion['completed_at']:
                completion['completed_at'] = completion['completed_at'].isoformat()
            
            # 格式化用户名
            name_parts = []
            if completion.get('first_name'):
                name_parts.append(completion['first_name'])
            if completion.get('last_name'):
                name_parts.append(completion['last_name'])
            completion['display_name'] = ' '.join(name_parts) or completion.get('username') or f"User_{completion['user_id']}"
        
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
        cur.execute("""
            SELECT 
                t.task_id,
                t.external_task_id,
                t.project_id,
                t.title,
                t.callback_url,
                t.callback_status,
                t.callback_retry_count,
                t.callback_last_attempt,
                t.created_at,
                COUNT(DISTINCT CASE WHEN ut.status = 'completed' THEN ut.user_id END) as completed_count
            FROM drama_tasks t
            LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
            WHERE t.callback_url IS NOT NULL
                AND t.created_at >= NOW() - INTERVAL '%s hours'
            GROUP BY t.task_id
            ORDER BY t.callback_last_attempt DESC NULLS LAST, t.created_at DESC
            LIMIT %s
        """, (hours, limit))
        
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
        
        # 任务统计
        cur.execute("""
            SELECT 
                COUNT(DISTINCT t.task_id) as total_tasks,
                COUNT(DISTINCT ut.user_id) as total_users,
                COUNT(DISTINCT CASE WHEN ut.status = 'completed' THEN ut.user_id END) as completed_users,
                COUNT(DISTINCT CASE WHEN t.callback_status = 'success' THEN t.task_id END) as successful_callbacks,
                COUNT(DISTINCT CASE WHEN t.callback_status = 'failed' THEN t.task_id END) as failed_callbacks
            FROM drama_tasks t
            LEFT JOIN user_tasks ut ON t.task_id = ut.task_id
            WHERE t.created_at >= NOW() - INTERVAL '%s hours'
        """, (hours,))
        
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
