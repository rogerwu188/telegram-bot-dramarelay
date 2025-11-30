"""
Webhook 回调通知模块
用于在任务完成后向外部系统发送回调通知
"""

import asyncio
import hmac
import hashlib
import time
import logging
from datetime import datetime
from typing import Dict, Optional
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from urllib.parse import urlparse

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 数据库连接配置
DATABASE_URL = os.getenv('DATABASE_URL')

def get_db_connection():
    """获取数据库连接"""
    result = urlparse(DATABASE_URL)
    return psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        cursor_factory=RealDictCursor
    )

def generate_signature(payload: str, secret: str) -> str:
    """生成 HMAC-SHA256 签名"""
    return 'sha256=' + hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

async def send_webhook(
    callback_url: str,
    payload: Dict,
    secret: Optional[str] = None,
    timeout: int = 30
) -> tuple[bool, Optional[str]]:
    """
    发送 Webhook 回调
    
    Args:
        callback_url: 回调 URL
        payload: 回调数据
        secret: 回调密钥 (可选)
        timeout: 超时时间 (秒)
    
    Returns:
        (success, error_message)
    """
    import json
    
    # 准备请求头
    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Event': payload.get('event', 'task.completed'),
        'X-Webhook-Timestamp': str(int(time.time())),
        'User-Agent': 'X2C-Bot-Webhook/1.0'
    }
    
    # 添加密钥和签名
    if secret:
        headers['X-Webhook-Secret'] = secret
        payload_str = json.dumps(payload, ensure_ascii=False)
        headers['X-Webhook-Signature'] = generate_signature(payload_str, secret)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                callback_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                status = response.status
                response_text = await response.text()
                
                # 2xx 状态码表示成功
                if 200 <= status < 300:
                    logger.info(f"✅ Webhook 发送成功: {callback_url} (status={status})")
                    return True, None
                else:
                    error_msg = f"HTTP {status}: {response_text[:200]}"
                    logger.warning(f"⚠️ Webhook 返回非成功状态: {error_msg}")
                    return False, error_msg
    
    except asyncio.TimeoutError:
        error_msg = f"Timeout after {timeout}s"
        logger.error(f"❌ Webhook 超时: {callback_url}")
        return False, error_msg
    
    except aiohttp.ClientError as e:
        error_msg = f"Client error: {str(e)}"
        logger.error(f"❌ Webhook 客户端错误: {error_msg}")
        return False, error_msg
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"❌ Webhook 发送异常: {error_msg}", exc_info=True)
        return False, error_msg

async def send_task_completed_webhook(
    task_id: int,
    user_id: int,
    platform: str,
    submission_link: str,
    node_power_earned: int,
    verification_details: Optional[Dict] = None
) -> bool:
    """
    发送任务完成回调
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        platform: 平台
        submission_link: 提交链接
        node_power_earned: 获得的算力
        verification_details: 验证详情
    
    Returns:
        是否发送成功
    """
    try:
        # 从数据库获取任务和用户信息
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取任务信息
        cur.execute("""
            SELECT task_id, project_id, external_task_id, title, duration, callback_url, callback_secret, callback_retry_count
            FROM drama_tasks
            WHERE task_id = %s
        """, (task_id,))
        task = cur.fetchone()
        
        if not task:
            logger.error(f"❌ 任务不存在: task_id={task_id}")
            cur.close()
            conn.close()
            return False
        
        # 如果没有配置回调 URL,直接返回成功
        if not task['callback_url']:
            logger.info(f"ℹ️ 任务 {task_id} 未配置回调 URL,跳过回调")
            cur.close()
            conn.close()
            return True
        
        # 获取用户信息
        cur.execute("""
            SELECT user_id, username, first_name
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        user = cur.fetchone()
        
        # 获取提交信息
        cur.execute("""
            SELECT submitted_at, verified_at
            FROM user_tasks
            WHERE user_id = %s AND task_id = %s
        """, (user_id, task_id))
        submission = cur.fetchone()
        
        cur.close()
        conn.close()
        
        # 构建回调数据（按照最小改动原则）
        # 根据平台生成对应的统计字段
        stats_data = {
            'project_id': task.get('project_id'),
            'task_id': task.get('external_task_id'),  # 使用X2C的task_id
            'duration': task.get('duration', 30),
            'account_count': 1  # 单个用户完成
        }
        
        # 从 verification_details 中获取数据（如果有）
        if verification_details:
            view_count = verification_details.get('views') or verification_details.get('view_count', 0)
            like_count = verification_details.get('likes') or verification_details.get('like_count', 0)
            
            # 根据平台填充对应的字段
            platform_lower = platform.lower()
            if 'youtube' in platform_lower or 'yt' in platform_lower:
                if view_count > 0:
                    stats_data['yt_view_count'] = view_count
                if like_count > 0:
                    stats_data['yt_like_count'] = like_count
                stats_data['yt_account_count'] = 1
            elif 'tiktok' in platform_lower or 'tt' in platform_lower:
                if view_count > 0:
                    stats_data['tt_view_count'] = view_count
                if like_count > 0:
                    stats_data['tt_like_count'] = like_count
                stats_data['tt_account_count'] = 1
            # 其他平台可以类似扩展
        
        payload = {
            'site_name': 'DramaRelayBot',
            'stats': [stats_data]
        }
        
        # 发送回调
        logger.info(f"📤 准备发送 Webhook: task_id={task_id}, url={task['callback_url']}")
        success, error = await send_webhook(
            callback_url=task['callback_url'],
            payload=payload,
            secret=task['callback_secret']
        )
        
        # 更新回调状态
        conn = get_db_connection()
        cur = conn.cursor()
        
        retry_count = task['callback_retry_count'] or 0
        
        if success:
            # 回调成功
            cur.execute("""
                UPDATE drama_tasks
                SET callback_status = 'success',
                    callback_last_attempt = CURRENT_TIMESTAMP
                WHERE task_id = %s
            """, (task_id,))
            logger.info(f"✅ Webhook 回调成功: task_id={task_id}")
        else:
            # 回调失败,更新重试次数
            new_retry_count = retry_count + 1
            if new_retry_count >= 3:
                # 达到最大重试次数,标记为失败
                cur.execute("""
                    UPDATE drama_tasks
                    SET callback_status = 'failed',
                        callback_retry_count = %s,
                        callback_last_attempt = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (new_retry_count, task_id))
                logger.error(f"❌ Webhook 回调失败 (已达最大重试次数): task_id={task_id}, error={error}")
            else:
                # 更新重试次数,等待下次重试
                cur.execute("""
                    UPDATE drama_tasks
                    SET callback_retry_count = %s,
                        callback_last_attempt = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (new_retry_count, task_id))
                logger.warning(f"⚠️ Webhook 回调失败 (将重试): task_id={task_id}, retry={new_retry_count}/3, error={error}")
                
                # 计算下次重试延迟 (指数退避: 5, 25, 125 秒)
                delay = 5 ** new_retry_count
                logger.info(f"🔄 将在 {delay} 秒后重试 Webhook")
                
                # 异步调度重试
                asyncio.create_task(retry_webhook_after_delay(
                    task_id, user_id, platform, submission_link, 
                    node_power_earned, verification_details, delay
                ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return success
    
    except Exception as e:
        logger.error(f"❌ 发送 Webhook 异常: {e}", exc_info=True)
        return False

async def retry_webhook_after_delay(
    task_id: int,
    user_id: int,
    platform: str,
    submission_link: str,
    node_power_earned: int,
    verification_details: Optional[Dict],
    delay: int
):
    """延迟后重试 Webhook"""
    await asyncio.sleep(delay)
    logger.info(f"🔄 开始重试 Webhook: task_id={task_id}")
    await send_task_completed_webhook(
        task_id, user_id, platform, submission_link,
        node_power_earned, verification_details
    )

# 测试函数
async def test_webhook():
    """测试 Webhook 功能"""
    test_payload = {
        'event': 'task.completed',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'data': {
            'task_id': 999,
            'task_title': '测试任务',
            'user_id': 123456,
            'username': 'test_user',
            'platform': 'TikTok',
            'submission_link': 'https://www.tiktok.com/@test/video/123456',
            'submitted_at': datetime.utcnow().isoformat() + 'Z',
            'verified_at': datetime.utcnow().isoformat() + 'Z',
            'node_power_earned': 10,
            'verification_status': 'verified',
            'verification_details': {
                'matched': True,
                'match_rate': 100,
                'matched_keywords': ['测试关键词']
            }
        }
    }
    
    # 使用 webhook.site 测试
    test_url = 'https://webhook.site/your-unique-id'
    success, error = await send_webhook(test_url, test_payload, secret='test_secret')
    
    if success:
        print("✅ Webhook 测试成功!")
    else:
        print(f"❌ Webhook 测试失败: {error}")

if __name__ == '__main__':
    # 运行测试
    asyncio.run(test_webhook())
