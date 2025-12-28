#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：将旧任务的 category 从 name_key 更新为正确的分类名称

X2C API 返回的分类数据结构：
- name: 显示名称（如 "霸总甜宠"、"Spiritual Awakening Drama"）
- name_key: 代码（如 "ceoRomance"、"billionaireRomance"）

旧代码错误地将 name_key 存入数据库，现在需要将其更新为 name
"""

import pymysql
import os
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# name_key 到 name 的映射表（来自 X2C API）
CATEGORY_MAPPING = {
    # 英文分类
    'billionaireRomance': 'Spiritual Awakening Drama',
    'Thriller': 'Supernatural Thriller',
    'werewolfVampire': 'Female Revenge Arc',
    'rebirthTimeTravel': 'Billionaire Romance',
    'periodCostume': 'Fantasy',
    'marriageBetrayal': 'AI Drama Lab',
    # 中文分类
    'fantasyMysticism': '玄幻异能',
    'suspenseCrime': '悬疑惊悚',
    'sciFiApocalypse': '科幻末世',
    'urbanLife': '都市复仇',
    'generalMixed': '热门综合',
    'ceoRomance': '霸总甜宠',
    'immortalFantasy': '仙侠古装',
}


def get_db_connection():
    """获取数据库连接"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    result = urlparse(DATABASE_URL)
    
    return pymysql.connect(
        host=result.hostname,
        port=result.port or 4000,
        user=result.username,
        password=result.password,
        database=result.path[1:],
        ssl={'ssl': {}},
        cursorclass=pymysql.cursors.DictCursor
    )


def migrate_categories():
    """迁移 category 字段"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 查询当前 category 分布
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM drama_tasks 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        old_distribution = cur.fetchall()
        logger.info("📊 当前 category 分布:")
        for row in old_distribution:
            logger.info(f"  {row['category']}: {row['count']}")
        
        # 执行迁移
        total_updated = 0
        for old_key, new_name in CATEGORY_MAPPING.items():
            cur.execute("""
                UPDATE drama_tasks 
                SET category = %s 
                WHERE category = %s
            """, (new_name, old_key))
            
            affected = cur.rowcount
            if affected > 0:
                logger.info(f"✅ 更新 {old_key} → {new_name}: {affected} 条记录")
                total_updated += affected
        
        # 提交更改
        conn.commit()
        
        # 查询更新后的 category 分布
        cur.execute("""
            SELECT category, COUNT(*) as count 
            FROM drama_tasks 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        new_distribution = cur.fetchall()
        logger.info("\n📊 更新后的 category 分布:")
        for row in new_distribution:
            logger.info(f"  {row['category']}: {row['count']}")
        
        logger.info(f"\n✅ 迁移完成！共更新 {total_updated} 条记录")
        
        return {
            'success': True,
            'total_updated': total_updated,
            'old_distribution': old_distribution,
            'new_distribution': new_distribution
        }
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        conn.rollback()
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    print("=" * 50)
    print("开始迁移 category 字段...")
    print("=" * 50)
    
    result = migrate_categories()
    
    if result['success']:
        print(f"\n✅ 迁移成功！共更新 {result['total_updated']} 条记录")
    else:
        print(f"\n❌ 迁移失败: {result['error']}")
