"""临时脚本：添加到admin_api.py末尾的代码"""

@app.route('/api/tasks/<int:task_id>/detail', methods=['GET'])
def get_task_detail(task_id):
    """获取任务的完整详情"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM drama_tasks WHERE task_id = %s", (task_id,))
        task = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not task:
            return jsonify({
                'success': False,
                'error': f'任务不存在: task_id={task_id}'
            }), 404
        
        # 转换datetime对象为字符串
        task_data = dict(task)
        for key, value in task_data.items():
            if isinstance(value, datetime):
                task_data[key] = value.isoformat()
        
        return jsonify({
            'success': True,
            'data': task_data
        })
    
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
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
        logger.error(f"搜索任务失败: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
