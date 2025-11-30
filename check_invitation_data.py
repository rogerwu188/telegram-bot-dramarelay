"""
检查邀请系统数据的脚本
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

def check_invitation_data():
    """检查邀请系统数据"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        inviter_id = 5156570084
        invitee_id = 8550836392
        
        logger.info("=" * 60)
        logger.info("邀请系统数据检查")
        logger.info("=" * 60)
        
        # 1. 检查邀请关系
        logger.info("\n【1. 邀请关系】")
        cur.execute("""
            SELECT * FROM user_invitations 
            WHERE inviter_id = %s AND invitee_id = %s
        """, (inviter_id, invitee_id))
        invitation = cur.fetchone()
        
        if invitation:
            logger.info(f"✅ 邀请关系已记录:")
            logger.info(f"   - 邀请人ID: {invitation['inviter_id']}")
            logger.info(f"   - 被邀请人ID: {invitation['invitee_id']}")
            logger.info(f"   - 首次任务完成: {invitation['first_task_completed']}")
            logger.info(f"   - 首次任务完成时间: {invitation['first_task_completed_at']}")
            logger.info(f"   - 累计推荐奖励: {invitation['total_referral_rewards']}")
            logger.info(f"   - 创建时间: {invitation['created_at']}")
        else:
            logger.warning("❌ 未找到邀请关系记录")
        
        # 2. 检查被邀请人的任务完成情况
        logger.info("\n【2. 被邀请人任务完成情况】")
        cur.execute("""
            SELECT ut.*, dt.title, dt.node_power_reward
            FROM user_tasks ut
            JOIN drama_tasks dt ON ut.task_id = dt.task_id
            WHERE ut.user_id = %s
            ORDER BY ut.submitted_at DESC
        """, (invitee_id,))
        tasks = cur.fetchall()
        
        if tasks:
            logger.info(f"✅ 被邀请人完成了 {len(tasks)} 个任务:")
            for i, task in enumerate(tasks, 1):
                logger.info(f"\n   任务 {i}:")
                logger.info(f"   - 任务ID: {task['task_id']}")
                logger.info(f"   - 任务标题: {task['title']}")
                logger.info(f"   - 状态: {task['status']}")
                logger.info(f"   - 平台: {task['platform']}")
                logger.info(f"   - 提交时间: {task['submitted_at']}")
                logger.info(f"   - 验证时间: {task['verified_at']}")
                logger.info(f"   - 获得奖励: {task['node_power_earned']} X2C")
        else:
            logger.warning("❌ 被邀请人没有完成任何任务")
        
        # 3. 检查推荐奖励记录
        logger.info("\n【3. 推荐奖励记录】")
        cur.execute("""
            SELECT * FROM referral_rewards 
            WHERE inviter_id = %s AND invitee_id = %s
            ORDER BY created_at DESC
        """, (inviter_id, invitee_id))
        rewards = cur.fetchall()
        
        if rewards:
            logger.info(f"✅ 找到 {len(rewards)} 条推荐奖励记录:")
            for i, reward in enumerate(rewards, 1):
                logger.info(f"\n   奖励 {i}:")
                logger.info(f"   - 任务ID: {reward['task_id']}")
                logger.info(f"   - 原始奖励: {reward['original_reward']} X2C")
                logger.info(f"   - 推荐奖励: {reward['referral_reward']} X2C")
                logger.info(f"   - 创建时间: {reward['created_at']}")
        else:
            logger.warning("❌ 没有找到推荐奖励记录")
        
        # 4. 检查邀请人的算力
        logger.info("\n【4. 邀请人算力】")
        cur.execute("""
            SELECT user_id, username, total_node_power, completed_tasks
            FROM users
            WHERE user_id = %s
        """, (inviter_id,))
        inviter = cur.fetchone()
        
        if inviter:
            logger.info(f"✅ 邀请人信息:")
            logger.info(f"   - 用户ID: {inviter['user_id']}")
            logger.info(f"   - 用户名: {inviter['username']}")
            logger.info(f"   - 总算力: {inviter['total_node_power']} X2C")
            logger.info(f"   - 完成任务数: {inviter['completed_tasks']}")
        
        # 5. 检查被邀请人的算力
        logger.info("\n【5. 被邀请人算力】")
        cur.execute("""
            SELECT user_id, username, total_node_power, completed_tasks, invited_by
            FROM users
            WHERE user_id = %s
        """, (invitee_id,))
        invitee = cur.fetchone()
        
        if invitee:
            logger.info(f"✅ 被邀请人信息:")
            logger.info(f"   - 用户ID: {invitee['user_id']}")
            logger.info(f"   - 用户名: {invitee['username']}")
            logger.info(f"   - 总算力: {invitee['total_node_power']} X2C")
            logger.info(f"   - 完成任务数: {invitee['completed_tasks']}")
            logger.info(f"   - 被谁邀请: {invitee['invited_by']}")
        
        # 6. 分析问题
        logger.info("\n【6. 问题分析】")
        if invitation and tasks:
            if invitation['first_task_completed']:
                logger.info("✅ 首次任务已标记为完成")
            else:
                logger.warning("⚠️ 首次任务未标记为完成")
            
            if rewards:
                logger.info(f"✅ 已发放 {len(rewards)} 次推荐奖励")
            else:
                logger.error("❌ 问题：被邀请人完成了任务，但没有推荐奖励记录！")
                logger.error("   可能原因：")
                logger.error("   1. process_referral_reward() 函数执行失败")
                logger.error("   2. 任务是在邀请关系建立之前完成的")
                logger.error("   3. user_invitations 表查询失败")
                
                # 检查任务完成时间 vs 邀请时间
                if tasks[0]['submitted_at'] and invitation['created_at']:
                    if tasks[0]['submitted_at'] < invitation['created_at']:
                        logger.error(f"   ❌ 确认：任务完成时间 ({tasks[0]['submitted_at']}) 早于邀请时间 ({invitation['created_at']})")
                    else:
                        logger.error(f"   ✅ 任务完成时间 ({tasks[0]['submitted_at']}) 晚于邀请时间 ({invitation['created_at']})")
        
        logger.info("\n" + "=" * 60)
        
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 检查失败: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    check_invitation_data()
