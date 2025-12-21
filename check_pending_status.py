#!/usr/bin/env python3
"""
检查任务的 pending 验证状态
"""

def get_task_pending_status(conn, user_id: int, task_id: int) -> dict:
    """
    检查任务是否有 pending 状态的验证
    
    Returns:
        dict: {'is_pending': bool, 'status': str or None}
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT status FROM pending_verifications 
            WHERE user_id = %s AND task_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, task_id))
        result = cur.fetchone()
        
        if result:
            return {
                'is_pending': result['status'] == 'pending',
                'status': result['status']
            }
        return {'is_pending': False, 'status': None}
    finally:
        cur.close()


def get_user_pending_tasks(conn, user_id: int) -> list:
    """
    获取用户所有 pending 状态的任务 ID 列表
    
    Returns:
        list: [task_id, ...]
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT DISTINCT task_id FROM pending_verifications 
            WHERE user_id = %s AND status = 'pending'
        """, (user_id,))
        results = cur.fetchall()
        return [r['task_id'] for r in results]
    finally:
        cur.close()


def get_user_failed_tasks(conn, user_id: int) -> dict:
    """
    获取用户所有 failed 状态的任务
    
    Returns:
        dict: {task_id: error_message, ...}
    """
    cur = conn.cursor()
    try:
        # 获取每个任务最新的失败记录
        cur.execute("""
            SELECT pv.task_id, pv.error_message 
            FROM pending_verifications pv
            INNER JOIN (
                SELECT task_id, MAX(created_at) as max_created
                FROM pending_verifications
                WHERE user_id = %s
                GROUP BY task_id
            ) latest ON pv.task_id = latest.task_id AND pv.created_at = latest.max_created
            WHERE pv.user_id = %s AND pv.status = 'failed'
        """, (user_id, user_id))
        results = cur.fetchall()
        return {r['task_id']: r.get('error_message', '验证失败') for r in results}
    finally:
        cur.close()
