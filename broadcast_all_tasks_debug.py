"""
替换stats_broadcaster.py中的broadcast_all_tasks函数（第269-380行）
添加详细的调试日志
"""

async def broadcast_all_tasks():
    """
    回传所有活跃任务的统计数据
    
    Returns:
        dict: 回传结果统计
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 调试日志：开始查询
        logger.info("🔍 [DEBUG] 开始查询已完成的任务...")
        
        # 先查询user_tasks表中所有submitted的记录
        cur.execute("""
            SELECT COUNT(*) as total, 
                   MIN(submitted_at) as earliest,
                   MAX(submitted_at) as latest
            FROM user_tasks 
            WHERE status = 'submitted'
        """)
        stats = cur.fetchone()
        logger.info(f"🔍 [DEBUG] user_tasks表中 submitted 状态的任务数: {stats['total']}, 最早: {stats['earliest']}, 最晚: {stats['latest']}")
        
        # 查询drama_tasks表中有callback_url的任务数
        cur.execute("""
            SELECT COUNT(*) as total
            FROM drama_tasks
            WHERE callback_url IS NOT NULL AND callback_url != ''
        """)
        callback_count = cur.fetchone()['total']
        logger.info(f"🔍 [DEBUG] drama_tasks表中有callback_url的任务数: {callback_count}")
        
        # 查询最近7天内用户已完成的任务
        cur.execute("""
            SELECT DISTINCT
                t.task_id,
                t.external_task_id,
                t.project_id,
                t.title,
                ut.submission_link as video_url,
                t.callback_url,
                t.callback_secret,
                t.duration,
                ut.user_id,
                ut.submitted_at
            FROM user_tasks ut
            JOIN drama_tasks t ON ut.task_id = t.task_id
            WHERE ut.status = 'submitted'
              AND t.callback_url IS NOT NULL
              AND t.callback_url != ''
              AND ut.submitted_at >= NOW() - INTERVAL '7 days'
            ORDER BY ut.submitted_at DESC
        """)
        
        tasks = cur.fetchall()
        logger.info(f"🔍 [DEBUG] 查询到 {len(tasks)} 个符合条件的任务")
        
        if tasks:
            for task in tasks:
                callback_preview = task['callback_url'][:50] if task['callback_url'] else 'NULL'
                logger.info(f"🔍 [DEBUG] 任务: task_id={task['task_id']}, title={task['title']}, callback_url={callback_preview}...")
        
        cur.close()
        conn.close()
        
        if not tasks:
            logger.warning("⚠️ 没有需要回传的任务（查询结果为空）")
            return {
                'success': True,
                'total': 0,
                'success_count': 0,
                'failed_count': 0
            }
        
        logger.info(f"📊 开始回传 {len(tasks)} 个任务的数据")
        
        # 逐个回传
        success_count = 0
        failed_count = 0
        total_views = 0  # 统计总播放量
        
        for task in tasks:
            # ... 后续代码保持不变
