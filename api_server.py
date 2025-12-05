#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2C Drama Relay Bot - HTTP API Server
提供管理后台访问的 RESTful API 接口
"""

import os
import logging
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# 配置
# ============================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 环境变量
# 优先使用环境变量，如果是 MySQL URL 则使用 Railway PostgreSQL
DATABASE_URL_RAW = os.getenv('DATABASE_URL', '')
if DATABASE_URL_RAW.startswith('mysql://'):
    # 如果是 MySQL URL，使用 Railway PostgreSQL
    DATABASE_URL = 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'
else:
    DATABASE_URL = DATABASE_URL_RAW or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@tramway.proxy.rlwy.net:57058/railway'
API_KEY = os.getenv('API_KEY') or 'x2c_admin_secret_key_2024'
# Railway 提供 PORT 环境变量，优先使用它
PORT = int(os.getenv('PORT') or os.getenv('API_PORT', '5000'))

logger.info("✅ API Server configuration loaded")
logger.info(f"✅ Database URL: {DATABASE_URL[:30]}...")
logger.info(f"✅ API Port: {PORT}")

# ============================================================
# 数据库连接
# ============================================================

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ============================================================
# 认证装饰器
# ============================================================

def require_api_key(f):
    """API Key 认证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 从 Header 或 Query 参数获取 API Key
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key or api_key != API_KEY:
            return jsonify({
                'success': False,
                'error': 'Invalid or missing API key'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================================
# API 路由
# ============================================================

@app.route('/', methods=['GET'])
def index():
    """API 首页"""
    return jsonify({
        'name': 'X2C Drama Relay Bot API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'tasks': {
                'list': 'GET /api/tasks',
                'get': 'GET /api/tasks/<task_id>',
                'create': 'POST /api/tasks',
                'update': 'PUT /api/tasks/<task_id>',
                'delete': 'DELETE /api/tasks/<task_id>',
            },
            'stats': {
                'overview': 'GET /api/stats/overview',
                'tasks': 'GET /api/stats/tasks',
            },
            'users': {
                'list': 'GET /api/users',
                'get': 'GET /api/users/<user_id>',
            },
            'submissions': {
                'list': 'GET /api/submissions',
                'by_task': 'GET /api/submissions/task/<task_id>',
            }
        },
        'authentication': 'X-API-Key header or api_key query parameter'
    })

# ============================================================
# 任务管理 API
# ============================================================

@app.route('/api/tasks', methods=['GET'])
@require_api_key
def get_tasks():
    """获取所有任务列表"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取查询参数
        status = request.args.get('status')  # active, inactive, all
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 构建查询
        query = "SELECT * FROM drama_tasks"
        params = []
        
        if status and status != 'all':
            query += " WHERE status = %s"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cur.execute(query, params)
        tasks = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # 转换为 JSON 可序列化的格式
        tasks_list = []
        for task in tasks:
            task_dict = dict(task)
            if task_dict.get('created_at'):
                task_dict['created_at'] = task_dict['created_at'].isoformat()
            tasks_list.append(task_dict)
        
        return jsonify({
            'success': True,
            'data': tasks_list,
            'count': len(tasks_list)
        })
    
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@require_api_key
def get_task(task_id):
    """获取单个任务详情"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM drama_tasks WHERE task_id = %s", (task_id,))
        task = cur.fetchone()
        
        if not task:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # 获取该任务的提交统计（只统计已验证的提交）
        cur.execute("""
            SELECT 
                COUNT(*) as total_submissions,
                COUNT(CASE WHEN status = 'verified' THEN 1 END) as verified_submissions,
                COUNT(DISTINCT user_id) as unique_users
            FROM user_tasks
            WHERE task_id = %s
        """, (task_id,))
        stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        task_dict = dict(task)
        if task_dict.get('created_at'):
            task_dict['created_at'] = task_dict['created_at'].isoformat()
        
        task_dict['stats'] = {
            'total_submissions': stats['total_submissions'],
            'successful_distributions': stats['verified_submissions'],
            'unique_users': stats['unique_users']
        }
        
        return jsonify({
            'success': True,
            'data': task_dict
        })
    
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks', methods=['POST'])
@require_api_key
def create_task():
    """创建新任务"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        if not data.get('title'):
            return jsonify({
                'success': False,
                'error': 'Title is required'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 处理剧集分类
        from category_classifier import classify_drama_by_ai, DRAMA_CATEGORIES
        
        # 支持 video_url 和 video_file_id 两种参数名
        video_url = data.get('video_file_id') or data.get('video_url')
        
        category = data.get('category')
        
        # 验证传入的分类是否有效
        if category and category in DRAMA_CATEGORIES and category != 'latest':
            # 有值且在分类模版库内，使用传入的分类
            logger.info(f"✅ 使用传入的分类: {data.get('title')} → {category}")
        else:
            # 无值或不在模版库内，使用 AI 自动分类
            category = classify_drama_by_ai(data.get('title'), data.get('description', ''))
            logger.info(f"🤖 AI 自动分类: {data.get('title')} → {category}")
        
        cur.execute("""
            INSERT INTO drama_tasks (
                project_id, external_task_id, title, description, video_file_id, thumbnail_url,
                duration, node_power_reward, platform_requirements, status,
                video_url, task_template, keywords_template, video_title,
                callback_url, callback_secret, title_en, description_en, category
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING task_id, project_id, external_task_id, title, category, created_at
        """, (
            data.get('project_id'),
            data.get('task_id'),  # X2C平台提供的task_id，存储到external_task_id
            data.get('title'),
            data.get('description'),
            video_url,
            data.get('thumbnail_url'),
            data.get('duration', 15),
            data.get('node_power_reward', 10),
            data.get('platform_requirements', 'TikTok,YouTube,Instagram'),
            data.get('status', 'active'),
            data.get('video_url'),
            data.get('task_template'),
            data.get('keywords_template'),
            data.get('video_title'),
            data.get('callback_url'),
            data.get('callback_secret'),
            data.get('title_en'),
            data.get('description_en'),
            category
        ))
        
        new_task = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        task_dict = dict(new_task)
        if task_dict.get('created_at'):
            task_dict['created_at'] = task_dict['created_at'].isoformat()
        
        logger.info(f"✅ Created new task: internal_id={task_dict['task_id']}, external_id={task_dict.get('external_task_id')} - {task_dict['title']}")
        
        # 按照最小改动原则，只返回project_id和task_id（X2C的ID）
        return jsonify({
            'success': True,
            'project_id': task_dict.get('project_id'),
            'task_id': task_dict.get('external_task_id')  # 返回X2C提供的task_id
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT', 'PATCH'])
@require_api_key
def update_task(task_id):
    """更新任务"""
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查任务是否存在
        cur.execute("SELECT task_id FROM drama_tasks WHERE task_id = %s", (task_id,))
        if not cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # 构建更新语句
        update_fields = []
        params = []
        
        if 'title' in data:
            update_fields.append("title = %s")
            params.append(data['title'])
        if 'description' in data:
            update_fields.append("description = %s")
            params.append(data['description'])
        if 'video_file_id' in data:
            update_fields.append("video_file_id = %s")
            params.append(data['video_file_id'])
        if 'thumbnail_url' in data:
            update_fields.append("thumbnail_url = %s")
            params.append(data['thumbnail_url'])
        if 'duration' in data:
            update_fields.append("duration = %s")
            params.append(data['duration'])
        if 'node_power_reward' in data:
            update_fields.append("node_power_reward = %s")
            params.append(data['node_power_reward'])
        if 'platform_requirements' in data:
            update_fields.append("platform_requirements = %s")
            params.append(data['platform_requirements'])
        if 'status' in data:
            update_fields.append("status = %s")
            params.append(data['status'])
        
        if not update_fields:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'No fields to update'
            }), 400
        
        params.append(task_id)
        query = f"UPDATE drama_tasks SET {', '.join(update_fields)} WHERE task_id = %s RETURNING *"
        
        cur.execute(query, params)
        updated_task = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        task_dict = dict(updated_task)
        if task_dict.get('created_at'):
            task_dict['created_at'] = task_dict['created_at'].isoformat()
        
        logger.info(f"✅ Updated task: {task_id}")
        
        return jsonify({
            'success': True,
            'data': task_dict
        })
    
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@require_api_key
def delete_task(task_id):
    """删除任务"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查任务是否存在
        cur.execute("SELECT task_id, title FROM drama_tasks WHERE task_id = %s", (task_id,))
        task = cur.fetchone()
        
        if not task:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        # 删除任务
        cur.execute("DELETE FROM drama_tasks WHERE task_id = %s", (task_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Deleted task: {task_id} - {task['title']}")
        
        return jsonify({
            'success': True,
            'message': f'Task {task_id} deleted successfully'
        })
    
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 统计数据 API
# ============================================================

@app.route('/api/stats/overview', methods=['GET'])
@require_api_key
def get_stats_overview():
    """获取总体统计数据"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 任务统计
        cur.execute("SELECT COUNT(*) as total FROM drama_tasks")
        total_tasks = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as active FROM drama_tasks WHERE status = 'active'")
        active_tasks = cur.fetchone()['active']
        
        # 用户统计
        cur.execute("SELECT COUNT(*) as total FROM users")
        total_users = cur.fetchone()['total']
        
        # 提交统计
        cur.execute("SELECT COUNT(*) as total FROM user_tasks")
        total_submissions = cur.fetchone()['total']
        
        cur.execute("SELECT COUNT(*) as verified FROM user_tasks WHERE status = 'verified'")
        verified_submissions = cur.fetchone()['verified']
        
        # 节点算力统计
        cur.execute("SELECT SUM(total_node_power) as total FROM users")
        total_node_power = cur.fetchone()['total'] or 0
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'tasks': {
                    'total': total_tasks,
                    'active': active_tasks,
                    'inactive': total_tasks - active_tasks
                },
                'users': {
                    'total': total_users
                },
                'submissions': {
                    'total': total_submissions,
                    'verified': verified_submissions,
                    'pending': total_submissions - verified_submissions
                },
                'node_power': {
                    'total': total_node_power
                }
            }
        })
    
    except Exception as e:
        logger.error(f"Error getting stats overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/stats/tasks', methods=['GET'])
@require_api_key
def get_tasks_stats():
    """获取任务详细统计"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                dt.task_id,
                dt.title,
                dt.status,
                dt.node_power_reward,
                dt.created_at,
                COUNT(ut.id) as submission_count,
                COUNT(DISTINCT ut.user_id) as unique_users,
                SUM(CASE WHEN ut.status = 'verified' THEN 1 ELSE 0 END) as verified_count
            FROM drama_tasks dt
            LEFT JOIN user_tasks ut ON dt.task_id = ut.task_id
            GROUP BY dt.task_id, dt.title, dt.status, dt.node_power_reward, dt.created_at
            ORDER BY dt.created_at DESC
        """)
        
        tasks_stats = cur.fetchall()
        cur.close()
        conn.close()
        
        stats_list = []
        for task in tasks_stats:
            task_dict = dict(task)
            if task_dict.get('created_at'):
                task_dict['created_at'] = task_dict['created_at'].isoformat()
            stats_list.append(task_dict)
        
        return jsonify({
            'success': True,
            'data': stats_list
        })
    
    except Exception as e:
        logger.error(f"Error getting tasks stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 用户管理 API
# ============================================================

@app.route('/api/users', methods=['GET'])
@require_api_key
def get_users():
    """获取用户列表"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = "SELECT * FROM users ORDER BY total_node_power DESC"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cur.execute(query)
        users = cur.fetchall()
        
        cur.close()
        conn.close()
        
        users_list = []
        for user in users:
            user_dict = dict(user)
            if user_dict.get('created_at'):
                user_dict['created_at'] = user_dict['created_at'].isoformat()
            if user_dict.get('updated_at'):
                user_dict['updated_at'] = user_dict['updated_at'].isoformat()
            users_list.append(user_dict)
        
        return jsonify({
            'success': True,
            'data': users_list,
            'count': len(users_list)
        })
    
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
@require_api_key
def get_user(user_id):
    """获取单个用户详情"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
        
        # 获取用户的提交记录
        cur.execute("""
            SELECT ut.*, dt.title as task_title
            FROM user_tasks ut
            JOIN drama_tasks dt ON ut.task_id = dt.task_id
            WHERE ut.user_id = %s
            ORDER BY ut.created_at DESC
        """, (user_id,))
        submissions = cur.fetchall()
        
        cur.close()
        conn.close()
        
        user_dict = dict(user)
        if user_dict.get('created_at'):
            user_dict['created_at'] = user_dict['created_at'].isoformat()
        if user_dict.get('updated_at'):
            user_dict['updated_at'] = user_dict['updated_at'].isoformat()
        
        submissions_list = []
        for sub in submissions:
            sub_dict = dict(sub)
            if sub_dict.get('created_at'):
                sub_dict['created_at'] = sub_dict['created_at'].isoformat()
            if sub_dict.get('submitted_at'):
                sub_dict['submitted_at'] = sub_dict['submitted_at'].isoformat()
            if sub_dict.get('verified_at'):
                sub_dict['verified_at'] = sub_dict['verified_at'].isoformat()
            submissions_list.append(sub_dict)
        
        user_dict['submissions'] = submissions_list
        
        return jsonify({
            'success': True,
            'data': user_dict
        })
    
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 提交记录 API
# ============================================================

@app.route('/api/submissions', methods=['GET'])
@require_api_key
def get_submissions():
    """获取所有提交记录"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        status = request.args.get('status')  # pending, verified, rejected
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = """
            SELECT ut.*, dt.title as task_title, u.username, u.first_name
            FROM user_tasks ut
            JOIN drama_tasks dt ON ut.task_id = dt.task_id
            JOIN users u ON ut.user_id = u.user_id
        """
        params = []
        
        if status:
            query += " WHERE ut.status = %s"
            params.append(status)
        
        query += " ORDER BY ut.created_at DESC"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cur.execute(query, params)
        submissions = cur.fetchall()
        
        cur.close()
        conn.close()
        
        submissions_list = []
        for sub in submissions:
            sub_dict = dict(sub)
            if sub_dict.get('created_at'):
                sub_dict['created_at'] = sub_dict['created_at'].isoformat()
            if sub_dict.get('submitted_at'):
                sub_dict['submitted_at'] = sub_dict['submitted_at'].isoformat()
            if sub_dict.get('verified_at'):
                sub_dict['verified_at'] = sub_dict['verified_at'].isoformat()
            submissions_list.append(sub_dict)
        
        return jsonify({
            'success': True,
            'data': submissions_list,
            'count': len(submissions_list)
        })
    
    except Exception as e:
        logger.error(f"Error getting submissions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submissions/task/<int:task_id>', methods=['GET'])
@require_api_key
def get_task_submissions(task_id):
    """获取特定任务的提交记录"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT ut.*, u.username, u.first_name
            FROM user_tasks ut
            JOIN users u ON ut.user_id = u.user_id
            WHERE ut.task_id = %s
            ORDER BY ut.created_at DESC
        """, (task_id,))
        
        submissions = cur.fetchall()
        cur.close()
        conn.close()
        
        submissions_list = []
        for sub in submissions:
            sub_dict = dict(sub)
            if sub_dict.get('created_at'):
                sub_dict['created_at'] = sub_dict['created_at'].isoformat()
            if sub_dict.get('submitted_at'):
                sub_dict['submitted_at'] = sub_dict['submitted_at'].isoformat()
            if sub_dict.get('verified_at'):
                sub_dict['verified_at'] = sub_dict['verified_at'].isoformat()
            submissions_list.append(sub_dict)
        
        return jsonify({
            'success': True,
            'data': submissions_list,
            'count': len(submissions_list)
        })
    
    except Exception as e:
        logger.error(f"Error getting submissions for task {task_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 健康检查
# ============================================================

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    try:
        # 测试数据库连接
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# ============================================================
# 管理页面集成
# ============================================================

from flask import send_from_directory
import admin_api

@app.route('/admin')
def admin_page():
    """管理页面"""
    return send_from_directory('templates', 'admin.html')

@app.route('/api/logs/stats')
def admin_stats():
    """统计数据 API"""
    return admin_api.get_stats()

@app.route('/api/logs/webhooks')
def admin_webhooks():
    """Webhook 日志 API"""
    return admin_api.get_webhook_logs()

@app.route('/api/logs/completions')
def admin_completions():
    """完成日志 API"""
    return admin_api.get_completion_logs()

@app.route('/api/logs/tasks')
def admin_tasks():
    """任务日志 API"""
    return admin_api.get_task_logs()

# ============================================================
# 启动服务器
# ============================================================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Starting X2C Drama Relay Bot API Server")
    logger.info("=" * 60)
    logger.info(f"📡 API Server will run on http://0.0.0.0:{PORT}")
    logger.info(f"🔑 API Key: {API_KEY[:10]}...")
    logger.info("=" * 60)
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
