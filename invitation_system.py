"""
邀请系统数据库操作函数
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def record_invitation(inviter_id: int, invitee_id: int) -> bool:
    """记录邀请关系"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查是否已经有邀请关系
        cur.execute("SELECT invited_by FROM users WHERE user_id = %s", (invitee_id,))
        result = cur.fetchone()
        
        if result and result['invited_by']:
            logger.info(f"⚠️ User {invitee_id} already invited by {result['invited_by']}")
            cur.close()
            conn.close()
            return False
        
        # 更新用户的 invited_by 字段
        cur.execute("""
            UPDATE users 
            SET invited_by = %s 
            WHERE user_id = %s
        """, (inviter_id, invitee_id))
        
        # 插入邀请记录
        cur.execute("""
            INSERT INTO user_invitations (inviter_id, invitee_id)
            VALUES (%s, %s)
            ON CONFLICT (invitee_id) DO NOTHING
        """, (inviter_id, invitee_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Invitation recorded: {inviter_id} invited {invitee_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to record invitation: {e}", exc_info=True)
        return False

def get_invitation_stats(user_id: int) -> dict:
    """获取用户的邀请统计"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 总邀请人数
        cur.execute("""
            SELECT COUNT(*) as count
            FROM user_invitations
            WHERE inviter_id = %s
        """, (user_id,))
        total = cur.fetchone()
        
        # 有效邀请人数（完成首次任务的）
        cur.execute("""
            SELECT COUNT(*) as count
            FROM user_invitations
            WHERE inviter_id = %s AND first_task_completed = TRUE
        """, (user_id,))
        active = cur.fetchone()
        
        # 累计推荐奖励
        cur.execute("""
            SELECT COALESCE(SUM(total_referral_rewards), 0) as total
            FROM user_invitations
            WHERE inviter_id = %s
        """, (user_id,))
        rewards = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            'invited_count': total['count'] if total else 0,
            'active_count': active['count'] if active else 0,
            'total_rewards': float(rewards['total']) if rewards else 0.0
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get invitation stats: {e}", exc_info=True)
        return {
            'invited_count': 0,
            'active_count': 0,
            'total_rewards': 0.0
        }

def process_referral_reward(invitee_id: int, task_id: int, original_reward: float) -> bool:
    """处理推荐奖励（被邀请人完成任务时调用）"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取邀请关系
        cur.execute("""
            SELECT inviter_id, first_task_completed
            FROM user_invitations
            WHERE invitee_id = %s
        """, (invitee_id,))
        invitation = cur.fetchone()
        
        if not invitation:
            logger.info(f"ℹ️ User {invitee_id} was not invited by anyone")
            cur.close()
            conn.close()
            return False
        
        inviter_id = invitation['inviter_id']
        is_first_task = not invitation['first_task_completed']
        
        # 计算推荐奖励（10%）
        referral_reward = original_reward * 0.1
        
        # 给邀请人增加奖励
        cur.execute("""
            UPDATE users
            SET total_node_power = total_node_power + %s
            WHERE user_id = %s
        """, (referral_reward, inviter_id))
        
        # 记录推荐奖励
        cur.execute("""
            INSERT INTO referral_rewards (inviter_id, invitee_id, task_id, original_reward, referral_reward)
            VALUES (%s, %s, %s, %s, %s)
        """, (inviter_id, invitee_id, task_id, original_reward, referral_reward))
        
        # 更新邀请记录的累计奖励
        cur.execute("""
            UPDATE user_invitations
            SET total_referral_rewards = total_referral_rewards + %s
            WHERE invitee_id = %s
        """, (referral_reward, invitee_id))
        
        # 如果是首次任务，标记并给被邀请人新人奖励
        if is_first_task:
            # 标记首次任务完成
            cur.execute("""
                UPDATE user_invitations
                SET first_task_completed = TRUE,
                    first_task_completed_at = CURRENT_TIMESTAMP
                WHERE invitee_id = %s
            """, (invitee_id,))
            
            # 给被邀请人新人奖励 +5 X2C
            cur.execute("""
                UPDATE users
                SET total_node_power = total_node_power + 5
                WHERE user_id = %s
            """, (invitee_id,))
            
            # 标记新人奖励已领取
            cur.execute("""
                UPDATE users
                SET invitation_reward_received = TRUE,
                    invitation_reward_received_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (invitee_id,))
            
            logger.info(f"🎁 First task bonus: invitee {invitee_id} got +5 X2C, inviter {inviter_id} got +{referral_reward} X2C")
        else:
            logger.info(f"💰 Referral reward: inviter {inviter_id} got +{referral_reward} X2C from invitee {invitee_id}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to process referral reward: {e}", exc_info=True)
        return False

def get_inviter_id(invitee_id: int) -> int:
    """获取邀请人ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT invited_by FROM users WHERE user_id = %s", (invitee_id,))
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return result['invited_by'] if result and result['invited_by'] else None
        
    except Exception as e:
        logger.error(f"❌ Failed to get inviter ID: {e}", exc_info=True)
        return None


def get_active_invitees(inviter_id: int, page: int = 1, per_page: int = 10) -> dict:
    """获取有效被邀请人列表（分页）
    
    Args:
        inviter_id: 邀请人ID
        page: 页码（从1开始）
        per_page: 每页数量
    
    Returns:
        dict: {
            'invitees': [{'username': str, 'first_name': str, 'user_id': int}, ...],
            'total': int,
            'page': int,
            'total_pages': int
        }
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取总数
        cur.execute("""
            SELECT COUNT(*) as count
            FROM user_invitations ui
            WHERE ui.inviter_id = %s AND ui.first_task_completed = TRUE
        """, (inviter_id,))
        total_result = cur.fetchone()
        total = total_result['count'] if total_result else 0
        
        # 计算总页数
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        
        # 获取当前页的被邀请人列表
        offset = (page - 1) * per_page
        cur.execute("""
            SELECT u.user_id, u.username, u.first_name
            FROM user_invitations ui
            JOIN users u ON ui.invitee_id = u.user_id
            WHERE ui.inviter_id = %s AND ui.first_task_completed = TRUE
            ORDER BY ui.first_task_completed_at DESC
            LIMIT %s OFFSET %s
        """, (inviter_id, per_page, offset))
        
        invitees = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            'invitees': [dict(inv) for inv in invitees] if invitees else [],
            'total': total,
            'page': page,
            'total_pages': total_pages
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get active invitees: {e}", exc_info=True)
        return {
            'invitees': [],
            'total': 0,
            'page': 1,
            'total_pages': 1
        }
