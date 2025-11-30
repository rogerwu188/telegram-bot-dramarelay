"""
数据库迁移脚本：添加邀请系统相关表和字段
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def migrate():
    """执行数据库迁移"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        logger.info("🔄 开始数据库迁移...")
        
        # 1. 检查并添加 users 表的新字段
        logger.info("📝 检查 users 表字段...")
        
        # 添加 invited_by 字段
        try:
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS invited_by BIGINT
            """)
            logger.info("✅ 添加 invited_by 字段")
        except Exception as e:
            logger.warning(f"⚠️ invited_by 字段可能已存在: {e}")
        
        # 添加 invitation_reward_received 字段
        try:
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS invitation_reward_received BOOLEAN DEFAULT FALSE
            """)
            logger.info("✅ 添加 invitation_reward_received 字段")
        except Exception as e:
            logger.warning(f"⚠️ invitation_reward_received 字段可能已存在: {e}")
        
        # 添加 invitation_reward_received_at 字段
        try:
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS invitation_reward_received_at TIMESTAMP
            """)
            logger.info("✅ 添加 invitation_reward_received_at 字段")
        except Exception as e:
            logger.warning(f"⚠️ invitation_reward_received_at 字段可能已存在: {e}")
        
        # 2. 创建 user_invitations 表
        logger.info("📝 创建 user_invitations 表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_invitations (
                id SERIAL PRIMARY KEY,
                inviter_id BIGINT NOT NULL,
                invitee_id BIGINT NOT NULL UNIQUE,
                first_task_completed BOOLEAN DEFAULT FALSE,
                first_task_completed_at TIMESTAMP,
                total_referral_rewards DECIMAL(18, 2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inviter_id) REFERENCES users(user_id),
                FOREIGN KEY (invitee_id) REFERENCES users(user_id)
            )
        """)
        logger.info("✅ user_invitations 表已创建")
        
        # 3. 创建 referral_rewards 表
        logger.info("📝 创建 referral_rewards 表...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS referral_rewards (
                id SERIAL PRIMARY KEY,
                inviter_id BIGINT NOT NULL,
                invitee_id BIGINT NOT NULL,
                task_id INTEGER NOT NULL,
                original_reward DECIMAL(18, 2) NOT NULL,
                referral_reward DECIMAL(18, 2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inviter_id) REFERENCES users(user_id),
                FOREIGN KEY (invitee_id) REFERENCES users(user_id),
                FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id)
            )
        """)
        logger.info("✅ referral_rewards 表已创建")
        
        # 4. 从 users 表的 invited_by 字段同步数据到 user_invitations 表
        logger.info("📝 同步邀请关系数据...")
        cur.execute("""
            INSERT INTO user_invitations (inviter_id, invitee_id, created_at)
            SELECT invited_by, user_id, created_at
            FROM users
            WHERE invited_by IS NOT NULL
            ON CONFLICT (invitee_id) DO NOTHING
        """)
        synced_count = cur.rowcount
        logger.info(f"✅ 已同步 {synced_count} 条邀请关系")
        
        # 提交事务
        conn.commit()
        logger.info("✅ 数据库迁移完成！")
        
        # 5. 验证迁移结果
        logger.info("📊 验证迁移结果...")
        
        cur.execute("SELECT COUNT(*) as count FROM user_invitations")
        invitation_count = cur.fetchone()['count']
        logger.info(f"📊 user_invitations 表记录数: {invitation_count}")
        
        cur.execute("SELECT COUNT(*) as count FROM referral_rewards")
        reward_count = cur.fetchone()['count']
        logger.info(f"📊 referral_rewards 表记录数: {reward_count}")
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}", exc_info=True)
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("邀请系统数据库迁移脚本")
    logger.info("=" * 50)
    
    success = migrate()
    
    if success:
        logger.info("✅ 迁移成功！邀请系统已启用。")
    else:
        logger.error("❌ 迁移失败！请检查错误日志。")
