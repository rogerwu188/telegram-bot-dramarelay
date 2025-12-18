#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将数据库中的旧category值更新为X2C的新分类代码
"""

import pymysql
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # 解析数据库URL
    # mysql://user:password@host:port/database
    import re
    match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if not match:
        raise ValueError(f"Invalid DATABASE_URL format: {database_url}")
    
    user, password, host, port, database = match.groups()
    
    return pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )


def migrate_categories():
    """
    迁移category字段
    
    策略：
    1. 将所有旧的category值设置为NULL
    2. 让新任务使用X2C的分类代码
    3. 旧任务会显示在"latest"分类中
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 查询当前category分布
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM drama_tasks 
            WHERE status = 'active' 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        old_categories = cur.fetchall()
        logger.info("📊 当前category分布:")
        for row in old_categories:
            logger.info(f"  {row['category']}: {row['count']}")
        
        # 获取所有旧的category值（不在X2C分类列表中的）
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
            '霸总甜宠',
            '仙侠奇幻'
        ]
        
        # 将不在X2C分类中的category设置为NULL
        cur.execute("""
            UPDATE drama_tasks 
            SET category = NULL 
            WHERE category IS NOT NULL 
            AND category NOT IN (%s)
        """ % ','.join(['%s'] * len(x2c_categories)), x2c_categories)
        
        affected_rows = cur.rowcount
        logger.info(f"✅ 已将 {affected_rows} 个旧任务的category设置为NULL")
        
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
        
        new_categories = cur.fetchall()
        logger.info("📊 更新后的category分布:")
        for row in new_categories:
            logger.info(f"  {row['category']}: {row['count']}")
        
        logger.info("✅ Category迁移完成！")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    migrate_categories()
