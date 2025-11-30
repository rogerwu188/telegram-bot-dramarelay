"""
反刷量检查模块
"""
import psycopg2
from datetime import datetime, timedelta
import logging
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 配置参数
DAILY_SUBMIT_LIMIT = 10  # 每日提交上限
SUBMIT_INTERVAL_MINUTES = 3  # 提交间隔(分钟)
NEW_USER_COOLDOWN_MINUTES = 5  # 新用户冷却期(分钟)
LINK_VERIFY_TIMEOUT = 10  # 链接验证超时(秒)


def check_new_user_cooldown(conn, user_id: int) -> tuple[bool, str]:
    """
    检查新用户冷却期
    
    Returns:
        (is_allowed, error_message)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT created_at FROM users WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            return False, "用户不存在"
        
        created_at = result['created_at']
        cooldown_end = created_at + timedelta(minutes=NEW_USER_COOLDOWN_MINUTES)
        now = datetime.now()
        
        if now < cooldown_end:
            return False, "新注册用户需要等待5分钟,请稍后重试"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"检查新用户冷却期失败: {e}")
        return False, "系统错误,请稍后重试"


def check_submit_interval(conn, user_id: int) -> tuple[bool, str]:
    """
    检查提交间隔
    
    Returns:
        (is_allowed, error_message)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT last_submission_time FROM users WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result or not result['last_submission_time']:
            # 首次提交
            return True, ""
        
        last_submit_time = result['last_submission_time']
        next_allowed_time = last_submit_time + timedelta(minutes=SUBMIT_INTERVAL_MINUTES)
        now = datetime.now()
        
        if now < next_allowed_time:
            remaining_seconds = int((next_allowed_time - now).total_seconds())
            remaining_minutes = remaining_seconds // 60
            remaining_secs = remaining_seconds % 60
            
            return False, f"⏱️ 提交太频繁!\n\n请等待 {remaining_minutes} 分 {remaining_secs} 秒后再试。\n\n这是为了防止刷量行为,感谢理解!"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"检查提交间隔失败: {e}")
        return False, "系统错误,请稍后重试"


def check_daily_limit(conn, user_id: int) -> tuple[bool, str]:
    """
    检查每日提交上限
    
    Returns:
        (is_allowed, error_message)
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM user_tasks
            WHERE user_id = %s
            AND DATE(created_at) = CURRENT_DATE
            AND status = 'completed'
        """, (user_id,))
        
        result = cursor.fetchone()
        today_count = result['count'] if result else 0
        
        if today_count >= DAILY_SUBMIT_LIMIT:
            return False, f"🚫 今日提交次数已达上限!\n\n每天最多提交 {DAILY_SUBMIT_LIMIT} 次任务。\n明天再来吧!"
        
        return True, ""
        
    except Exception as e:
        logger.error(f"检查每日上限失败: {e}")
        return False, "系统错误,请稍后重试"


def verify_link_exists(link: str) -> tuple[bool, str]:
    """
    验证链接是否真实存在
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # 解析 URL
        parsed = urlparse(link)
        if not parsed.scheme or not parsed.netloc:
            return False, "链接格式无效"
        
        # 发送 HEAD 请求(更快,不下载内容)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.head(
            link,
            headers=headers,
            timeout=LINK_VERIFY_TIMEOUT,
            allow_redirects=True
        )
        
        # 检查状态码
        if response.status_code == 200:
            return True, ""
        elif response.status_code == 404:
            return False, "链接不存在或已被删除"
        elif response.status_code == 403:
            return False, "链接访问被拒绝,可能是私密视频"
        else:
            # 对于其他状态码,尝试 GET 请求
            response = requests.get(
                link,
                headers=headers,
                timeout=LINK_VERIFY_TIMEOUT,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                return True, ""
            else:
                return False, f"链接无法访问(状态码: {response.status_code})"
        
    except requests.Timeout:
        logger.warning(f"链接验证超时: {link}")
        # 超时不算失败,可能是网络问题
        return True, ""
    except requests.RequestException as e:
        logger.error(f"链接验证失败: {link}, 错误: {e}")
        # 网络错误不算失败,给用户通过
        return True, ""
    except Exception as e:
        logger.error(f"链接验证异常: {e}")
        return True, ""


def update_last_submit_time(conn, user_id: int):
    """
    更新用户最后提交时间
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users
            SET last_submission_time = NOW()
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"更新最后提交时间失败: {e}")
        conn.rollback()


def check_all_limits(conn, user_id: int, link: str) -> tuple[bool, str]:
    """
    执行所有反刷量检查
    
    Returns:
        (is_allowed, error_message)
    """
    # 1. 检查新用户冷却期
    allowed, error = check_new_user_cooldown(conn, user_id)
    if not allowed:
        return False, error
    
    # 2. 检查提交间隔
    allowed, error = check_submit_interval(conn, user_id)
    if not allowed:
        return False, error
    
    # 3. 检查每日上限
    allowed, error = check_daily_limit(conn, user_id)
    if not allowed:
        return False, error
    
    # 4. 验证链接真实性
    allowed, error = verify_link_exists(link)
    if not allowed:
        return False, f"❌ 链接验证失败!\n\n{error}\n\n请确保:\n• 链接真实有效\n• 视频是公开的\n• 视频未被删除"
    
    return True, ""


def get_user_submit_stats(conn, user_id: int) -> dict:
    """
    获取用户提交统计
    """
    try:
        cursor = conn.cursor()
        
        # 今日提交次数
        cursor.execute("""
            SELECT COUNT(*) FROM user_tasks
            WHERE user_id = %s
            AND DATE(created_at) = CURRENT_DATE
            AND status = 'completed'
        """, (user_id,))
        result = cursor.fetchone()
        today_count = result['count'] if result else 0
        
        # 最后提交时间
        cursor.execute("""
            SELECT last_submission_time FROM users WHERE user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        last_submit = result['last_submission_time'] if result and result.get('last_submission_time') else None
        
        # 计算下次可提交时间
        next_allowed = None
        if last_submit:
            next_allowed = last_submit + timedelta(minutes=SUBMIT_INTERVAL_MINUTES)
        
        return {
            'today_count': today_count,
            'daily_limit': DAILY_SUBMIT_LIMIT,
            'remaining_today': DAILY_SUBMIT_LIMIT - today_count,
            'last_submit': last_submit,
            'next_allowed': next_allowed
        }
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        return {}
