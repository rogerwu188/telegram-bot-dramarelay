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
        raw_data = request.get_json()
        
        # 记录接收到的原始数据
        logger.info(f"📥 接收到任务数据: {raw_data}")
        
        # 详细记录 category 字段
        logger.info(f"🎯 [DEBUG] raw_data 中的 category: {raw_data.get('category')}")
        logger.info(f"🎯 [DEBUG] raw_data 中的 project_style: {raw_data.get('project_style')}")
        logger.info(f"🎯 [DEBUG] raw_data 的所有字段: {list(raw_data.keys())}")
        
        # 处理 X2C 的 datasets 数组结构
        # X2C 传递的格式: {"datasets": [{...task_data...}], "source": "x2c-distribution-episode", ...}
        if 'datasets' in raw_data and isinstance(raw_data['datasets'], list) and len(raw_data['datasets']) > 0:
            # 从 datasets 数组中提取任务数据
            data = raw_data['datasets'][0]
            # 保留顶层的 callback_url（如果 datasets 内没有）
            if not data.get('callback_url') and raw_data.get('callback_url'):
                data['callback_url'] = raw_data.get('callback_url')
            logger.info(f"📦 解析 X2C datasets 结构: source={raw_data.get('source')}, 任务数={len(raw_data['datasets'])}")
        else:
            # 直接使用原始数据（兼容旧格式）
            data = raw_data
        
        # 详细记录解析后的 data 中的 category
        logger.info(f"🎯 [DEBUG] 解析后 data 中的 category: {data.get('category')}")
        logger.info(f"🎯 [DEBUG] 解析后 data 中的 project_style: {data.get('project_style')}")
        
        # 验证必填字段
        if not data.get('title'):
            return jsonify({
                'success': False,
                'error': 'Title is required'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 处理剧集分类
        from x2c_category_sync import get_category_code
        
        # 支持 video_url 和 video_file_id 两种参数名
        video_url = data.get('video_file_id') or data.get('video_url')
        
        # 从 X2C 的 project_style 或 category 获取分类
        project_style = data.get('project_style') or data.get('category')
        
        # 将 project_style 映射为 Bot 的分类代码
        if project_style:
            category = get_category_code(project_style)
            if category:
                logger.info(f"✅ 使用 X2C 分类: {data.get('title')} | {project_style} → {category}")
            else:
                # 未找到映射，使用原值
                category = project_style
                logger.warning(f"⚠️ 未找到分类映射，使用原值: {project_style}")
        else:
            # 没有 project_style，使用默认分类
            category = 'latest'
            logger.info(f"🆕 未提供分类，使用默认: {data.get('title')} → {category}")
        
        # 处理任务状态：将 'approved' 映射为 'active'
        # X2C 平台可能传入 'approved' 状态，但 Bot 只识别 'active' 状态
        raw_status = data.get('status', 'active')
        if raw_status in ['approved', 'active', None]:
            task_status = 'active'
        else:
            task_status = raw_status
        
        if raw_status == 'approved':
            logger.info(f"⚠️ 状态映射: {data.get('title')} - 'approved' → 'active'")
        
        cur.execute("""
            INSERT INTO drama_tasks (
                project_id, external_task_id, title, description, video_file_id, thumbnail_url,
                duration, node_power_reward, platform_requirements, status,
                video_url, task_template, keywords_template, video_title,
                callback_url, callback_secret, title_en, description_en, category, hashtags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            task_status,
            data.get('video_url'),
            data.get('task_template'),
            data.get('keywords_template') or data.get('keywords'),  # 兼容X2C的keywords字段
            data.get('video_title'),
            data.get('callback_url'),
            data.get('callback_secret'),
            data.get('title_en'),
            data.get('description_en'),
            category,
            data.get('hashtags')  # X2C平台提供的hashtags
        ))
        
        new_task = cur.fetchone()
        
        # 保存原始接收数据到日志表
        try:
            import json
            cur.execute("""
                INSERT INTO task_receive_logs (task_id, project_id, title, raw_data, parsed_category, final_category)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                new_task['task_id'],
                data.get('project_id'),
                data.get('title'),
                json.dumps(raw_data, ensure_ascii=False),
                project_style,  # X2C发送的原始分类值
                category  # 最终存储的分类值
            ))
            logger.info(f"📝 已保存任务接收日志: task_id={new_task['task_id']}, parsed_category={project_style}, final_category={category}")
        except Exception as log_error:
            logger.warning(f"⚠️ 保存任务接收日志失败: {log_error}")
        
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

@app.route('/api/logs/errors')
def admin_errors():
    """错误日志 API"""
    return admin_api.get_error_logs()

@app.route('/api/config/api-key')
def admin_api_key():
    """获取 API Key"""
    return admin_api.get_api_key()

@app.route('/api/tasks/<int:task_id>/fix-status', methods=['POST'])
def fix_task_status(task_id):
    """修复任务状态"""
    return admin_api.fix_task_status(task_id)

@app.route('/api/tasks/fix-all-approved', methods=['POST'])
def fix_all_approved():
    """批量修复 approved 状态的任务"""
    return admin_api.fix_all_approved_tasks()

# 分发数据回传相关路由
@app.route('/api/broadcaster/start', methods=['POST'])
def start_broadcaster():
    """启动分发数据回传服务"""
    return admin_api.start_broadcaster_api()

@app.route('/api/broadcaster/stop', methods=['POST'])
def stop_broadcaster():
    """停止分发数据回传服务"""
    return admin_api.stop_broadcaster_api()

@app.route('/api/broadcaster/status', methods=['GET'])
def get_broadcaster_status():
    """获取分发数据回传服务状态"""
    return admin_api.get_broadcaster_status_api()

@app.route('/api/broadcaster/trigger', methods=['POST'])
def trigger_broadcaster():
    """手动触发一次分发数据回传"""
    return admin_api.trigger_broadcaster_api()

@app.route('/api/admin/delete_tasks', methods=['POST'])
def delete_tasks_route():
    """删除指定的任务及相关数据"""
    return admin_api.delete_tasks()

@app.route('/api/admin/update_callback_url', methods=['POST'])
def update_callback_url_route():
    """批量更新callback_url"""
    return admin_api.update_callback_url()

@app.route('/api/admin/delete_null_tasks', methods=['POST'])
def delete_null_tasks_route():
    """删除category为NULL的旧任务"""
    return admin_api.delete_null_category_tasks()

@app.route('/api/admin/migrate_categories', methods=['POST'])
def migrate_categories_route():
    """迁移旧的category值到X2C分类"""
    return admin_api.migrate_categories()

@app.route('/api/admin/create_webhook_logs_table', methods=['POST'])
def create_webhook_logs_table():
    """创建webhook_logs表（一次性操作）"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查表是否已存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'webhook_logs'
            )
        """)
        
        exists = cur.fetchone()['exists']
        
        if exists:
            cur.close()
            conn.close()
            return jsonify({
                'success': True,
                'message': 'webhook_logs表已存在',
                'already_exists': True
            })
        
        # 创建表
        cur.execute("""
            CREATE TABLE webhook_logs (
                id SERIAL PRIMARY KEY,
                task_id INTEGER,
                task_title VARCHAR(500),
                project_id VARCHAR(100),
                callback_url TEXT,
                callback_status VARCHAR(50) DEFAULT 'success',
                payload JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        cur.execute("""
            CREATE INDEX idx_webhook_logs_task_id ON webhook_logs(task_id);
        """)
        cur.execute("""
            CREATE INDEX idx_webhook_logs_created_at ON webhook_logs(created_at);
        """)
        cur.execute("""
            CREATE INDEX idx_webhook_logs_callback_status ON webhook_logs(callback_status);
        """)
        cur.execute("""
            CREATE INDEX idx_webhook_logs_project_id ON webhook_logs(project_id);
        """)
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ webhook_logs表创建成功")
        
        return jsonify({
            'success': True,
            'message': 'webhook_logs表创建成功！',
            'already_exists': False
        })
        
    except Exception as e:
        logger.error(f"❌ 创建webhook_logs表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 全局 Callback URL 配置 API
# ============================================================

@app.route('/api/config/callback-url', methods=['GET'])
def get_callback_url():
    """获取全局 Callback URL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查system_config表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'system_config'
            )
        """)
        exists = cur.fetchone()['exists']
        
        if not exists:
            # 创建system_config表
            cur.execute("""
                CREATE TABLE system_config (
                    id SERIAL PRIMARY KEY,
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("✅ system_config表创建成功")
        
        # 获取callback_url配置
        cur.execute("""
            SELECT config_value FROM system_config WHERE config_key = 'x2c_callback_url'
        """)
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        callback_url = result['config_value'] if result else ''
        
        return jsonify({
            'success': True,
            'callback_url': callback_url
        })
        
    except Exception as e:
        logger.error(f"❌ 获取Callback URL失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config/callback-url', methods=['POST'])
def set_callback_url():
    """设置全局 Callback URL"""
    try:
        data = request.get_json()
        callback_url = data.get('callback_url', '').strip()
        
        if not callback_url:
            return jsonify({
                'success': False,
                'error': 'Callback URL 不能为空'
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查system_config表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'system_config'
            )
        """)
        exists = cur.fetchone()['exists']
        
        if not exists:
            # 创建system_config表
            cur.execute("""
                CREATE TABLE system_config (
                    id SERIAL PRIMARY KEY,
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("✅ system_config表创建成功")
        
        # 使用UPSERT更新或插入配置
        cur.execute("""
            INSERT INTO system_config (config_key, config_value, updated_at)
            VALUES ('x2c_callback_url', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (config_key) 
            DO UPDATE SET config_value = %s, updated_at = CURRENT_TIMESTAMP
        """, (callback_url, callback_url))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Callback URL 已更新: {callback_url}")
        
        return jsonify({
            'success': True,
            'message': 'Callback URL 保存成功',
            'callback_url': callback_url
        })
        
    except Exception as e:
        logger.error(f"❌ 保存Callback URL失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 播放量抓取服务 API
# ============================================================

# 导入播放量抓取服务
try:
    from view_counter_service import (
        fetch_all_view_counts,
        start_view_count_timer,
        stop_view_count_timer,
        is_timer_running,
        ensure_view_count_columns,
        ensure_view_count_error_log_table
    )
    VIEW_COUNTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 播放量抓取服务不可用: {e}")
    VIEW_COUNTER_AVAILABLE = False

@app.route('/api/view-counter/start', methods=['POST'])
def start_view_counter():
    """启动播放量抓取定时器"""
    if not VIEW_COUNTER_AVAILABLE:
        return jsonify({'success': False, 'error': '播放量抓取服务不可用'}), 500
    
    try:
        # 确保表结构正确
        ensure_view_count_columns()
        ensure_view_count_error_log_table()
        
        if is_timer_running():
            return jsonify({'success': False, 'error': '定时器已在运行中'})
        
        start_view_count_timer(interval_minutes=10)
        return jsonify({'success': True, 'message': '播放量抓取定时器已启动，间隔: 10分钟'})
    except Exception as e:
        logger.error(f"❌ 启动播放量定时器失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/view-counter/stop', methods=['POST'])
def stop_view_counter():
    """停止播放量抓取定时器"""
    if not VIEW_COUNTER_AVAILABLE:
        return jsonify({'success': False, 'error': '播放量抓取服务不可用'}), 500
    
    try:
        stop_view_count_timer()
        return jsonify({'success': True, 'message': '播放量抓取定时器已停止'})
    except Exception as e:
        logger.error(f"❌ 停止播放量定时器失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/view-counter/status', methods=['GET'])
def get_view_counter_status():
    """获取播放量抓取定时器状态"""
    if not VIEW_COUNTER_AVAILABLE:
        return jsonify({'success': False, 'error': '播放量抓取服务不可用'}), 500
    
    return jsonify({
        'success': True,
        'running': is_timer_running(),
        'interval_minutes': 10
    })

@app.route('/api/view-counter/trigger', methods=['POST'])
def trigger_view_counter():
    """手动触发一次播放量抓取"""
    if not VIEW_COUNTER_AVAILABLE:
        return jsonify({'success': False, 'error': '播放量抓取服务不可用'}), 500
    
    try:
        # 确保表结构正确
        ensure_view_count_columns()
        ensure_view_count_error_log_table()
        
        result = fetch_all_view_counts()
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ 手动抓取播放量失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

## ============================================================
# X2C Pool 任务接收接口 - 按照标准协议直接接收任务
# ============================================================

@app.route('/api/x2c/tasks', methods=['POST'])
@require_api_key
def x2c_task_receive():
    """
    X2C Pool 任务接收接口
    
    按照 X2C Pool 任务分发接口标准 v1.1 实现
    接收扁平的 JSON 对象，不使用 datasets 数组嵌套
    
    必填字段:
    - title: 任务标题
    - task_id: X2C 平台的剧集ID (Episode ID)
    - video_url: 视频文件链接
    - category: 剧集类型
    - callback_url: 回调URL
    """
    import json
    
    try:
        # 获取原始请求数据
        raw_body = request.get_data(as_text=True)
        data = request.get_json()
        
        # 记录完整的原始数据
        logger.info(f"📥 [X2C] 接收到任务数据")
        logger.info(f"📥 [X2C] 字段列表: {list(data.keys()) if data else 'None'}")
        logger.info(f"📥 [X2C] 字段数量: {len(data.keys()) if data else 0}")
        logger.info(f"📥 [X2C] category: {data.get('category')}")
        logger.info(f"📥 [X2C] callback_url: {data.get('callback_url')}")
        logger.info(f"📥 [X2C] 完整数据: {data}")
        
        # 验证必填字段
        required_fields = ['title', 'task_id', 'video_url', 'category', 'callback_url']
        missing_fields = [f for f in required_fields if not data.get(f)]
        
        if missing_fields:
            logger.warning(f"⚠️ [X2C] 缺少必填字段: {missing_fields}")
            return jsonify({
                'success': False,
                'error': f'缺少必填字段: {missing_fields}',
                'received_fields': list(data.keys()) if data else []
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 处理剧集分类
        from x2c_category_sync import get_category_code
        
        raw_category = data.get('category')
        category = get_category_code(raw_category)
        
        if category:
            logger.info(f"✅ [X2C] 分类映射成功: {raw_category} → {category}")
        else:
            # 未找到映射，使用默认分类
            category = 'latest'
            logger.warning(f"⚠️ [X2C] 未找到分类映射，使用默认: {raw_category} → {category}")
        
        # 处理任务状态：将 'approved' 映射为 'active'
        raw_status = data.get('status', 'active')
        task_status = 'active' if raw_status in ['approved', 'active', None] else raw_status
        
        # 插入任务到数据库
        cur.execute("""
            INSERT INTO drama_tasks (
                project_id, external_task_id, title, description, video_file_id, thumbnail_url,
                duration, node_power_reward, platform_requirements, status,
                video_url, keywords_template, video_title,
                callback_url, category, hashtags
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING task_id, project_id, external_task_id, title, category, created_at
        """, (
            data.get('project_id'),
            data.get('task_id'),  # X2C平台提供的task_id（剧集ID），存储到external_task_id
            data.get('title'),
            data.get('description'),
            data.get('video_url'),  # 使用video_url作为video_file_id
            data.get('thumbnail_url'),
            data.get('duration', 15),
            data.get('node_power_reward', 10),
            data.get('platform_requirements', 'TikTok,YouTube,Instagram'),
            task_status,
            data.get('video_url'),
            data.get('keywords'),
            data.get('video_title') or data.get('title'),  # 如果没有video_title，使用title
            data.get('callback_url'),
            category,
            data.get('hashtags')
        ))
        
        new_task = cur.fetchone()
        
        # 保存原始接收数据到日志表
        try:
            cur.execute("""
                INSERT INTO task_receive_logs (task_id, project_id, title, raw_data, parsed_category, final_category)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                new_task['task_id'],
                data.get('project_id'),
                data.get('title'),
                raw_body,  # 保存原始请求体
                raw_category,  # X2C发送的原始分类值
                category  # 最终存储的分类值
            ))
            logger.info(f"📝 [X2C] 已保存任务接收日志: task_id={new_task['task_id']}")
        except Exception as log_error:
            logger.warning(f"⚠️ [X2C] 保存任务接收日志失败: {log_error}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        task_dict = dict(new_task)
        if task_dict.get('created_at'):
            task_dict['created_at'] = task_dict['created_at'].isoformat()
        
        logger.info(f"✅ [X2C] 任务创建成功: internal_id={task_dict['task_id']}, external_id={task_dict.get('external_task_id')}, category={task_dict.get('category')} - {task_dict['title']}")
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': '任务创建成功',
            'data': {
                'internal_task_id': task_dict['task_id'],
                'project_id': task_dict.get('project_id'),
                'task_id': task_dict.get('external_task_id'),  # 返回X2C提供的task_id
                'title': task_dict.get('title'),
                'category': task_dict.get('category'),
                'received_fields': list(data.keys())
            }
        }), 201
    
    except Exception as e:
        logger.error(f"❌ [X2C] 创建任务失败: {e}")
        import traceback
        logger.error(f"❌ [X2C] 错误详情: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 专用测试接口 - 用于排查字段丢失问题
# ============================================================

@app.route('/api/test/echo', methods=['POST', 'GET'])
def test_echo():
    """测试接口 - 记录完整的原始请求数据"""
    import json
    
    try:
        # 获取请求信息
        method = request.method
        headers = dict(request.headers)
        raw_body = request.get_data(as_text=True)
        
        # 尝试解析JSON
        parsed_json = None
        field_names = []
        field_count = 0
        category_value = None
        
        try:
            parsed_json = request.get_json(force=True)
            if parsed_json:
                field_names = list(parsed_json.keys())
                field_count = len(field_names)
                category_value = parsed_json.get('category')
        except:
            pass
        
        # 获取客户端IP
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # 保存到数据库
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO api_test_logs (endpoint, method, headers, raw_body, parsed_json, field_count, field_names, category_value, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            '/api/test/echo',
            method,
            json.dumps(headers, ensure_ascii=False),
            raw_body,
            json.dumps(parsed_json, ensure_ascii=False) if parsed_json else None,
            field_count,
            field_names,
            category_value,
            ip_address
        ))
        
        log_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"🧪 测试接口收到请求: log_id={log_id}, field_count={field_count}, category={category_value}")
        logger.info(f"🧪 字段列表: {field_names}")
        logger.info(f"🧪 原始数据: {raw_body[:500] if raw_body else 'empty'}")
        
        return jsonify({
            'success': True,
            'log_id': log_id,
            'received': {
                'method': method,
                'field_count': field_count,
                'field_names': field_names,
                'category_value': category_value,
                'raw_body_length': len(raw_body) if raw_body else 0
            },
            'message': '数据已记录，请查询 api_test_logs 表获取完整数据'
        })
        
    except Exception as e:
        logger.error(f"❌ 测试接口错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/test/logs', methods=['GET'])
def get_test_logs():
    """获取测试日志"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        limit = request.args.get('limit', 10, type=int)
        
        cur.execute("""
            SELECT id, endpoint, method, field_count, field_names, category_value, ip_address, created_at,
                   raw_body, parsed_json
            FROM api_test_logs
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        
        logs = cur.fetchall()
        cur.close()
        conn.close()
        
        logs_list = []
        for log in logs:
            log_dict = dict(log)
            if log_dict.get('created_at'):
                log_dict['created_at'] = log_dict['created_at'].isoformat()
            logs_list.append(log_dict)
        
        return jsonify({
            'success': True,
            'data': logs_list,
            'count': len(logs_list)
        })
        
    except Exception as e:
        logger.error(f"❌ 获取测试日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# 清空日志 API
# ============================================================
@app.route('/api/logs/clear-all', methods=['POST'])
def clear_all_logs():
    """
    清空所有日志数据（webhook_logs, broadcaster_error_logs, user_tasks, drama_tasks）
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
        
        logger.info(f"🗑️ 清空所有日志完成，共删除 {total_deleted} 条记录")
        
        return jsonify({
            'success': True,
            'message': f'已清空所有日志，共删除 {total_deleted} 条记录',
            'deleted': deleted_counts
        })
    
    except Exception as e:
        import traceback
        logger.error(f"❌ 清空日志失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

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
