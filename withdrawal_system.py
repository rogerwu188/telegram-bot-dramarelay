"""
提现系统模块
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import re
import asyncio

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def validate_sol_address(address: str) -> bool:
    """验证 SOL 地址格式"""
    # SOL 地址通常是 32-44 个字符的 base58 编码
    # 简化验证: 长度在 32-44 之间,只包含 base58 字符
    if not address or len(address) < 32 or len(address) > 44:
        return False
    
    # Base58 字符集 (不包含 0, O, I, l)
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
    return bool(re.match(base58_pattern, address))

def create_withdrawal_request(user_id: int, sol_address: str, amount: float) -> int:
    """创建提现请求"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 检查用户余额
        cur.execute("SELECT total_node_power FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user or user['total_node_power'] < amount:
            cur.close()
            conn.close()
            return None
        
        # 创建提现请求
        cur.execute("""
            INSERT INTO withdrawals (user_id, sol_address, amount, status)
            VALUES (%s, %s, %s, 'pending')
            RETURNING withdrawal_id
        """, (user_id, sol_address, amount))
        
        withdrawal_id = cur.fetchone()['withdrawal_id']
        
        # 扣除用户余额
        cur.execute("""
            UPDATE users
            SET total_node_power = total_node_power - %s
            WHERE user_id = %s
        """, (amount, user_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"✅ Withdrawal request created: withdrawal_id={withdrawal_id}, user_id={user_id}, amount={amount}")
        return withdrawal_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create withdrawal request: {e}", exc_info=True)
        return None

async def process_withdrawal(withdrawal_id: int) -> dict:
    """
    处理提现请求 (异步)
    
    返回格式:
    {
        'success': True/False,
        'tx_hash': '交易哈希' (成功时),
        'error': '错误信息' (失败时)
    }
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 获取提现请求信息
        cur.execute("""
            SELECT withdrawal_id, user_id, sol_address, amount
            FROM withdrawals
            WHERE withdrawal_id = %s AND status = 'pending'
        """, (withdrawal_id,))
        
        withdrawal = cur.fetchone()
        
        if not withdrawal:
            cur.close()
            conn.close()
            return {'success': False, 'error': 'Withdrawal request not found or already processed'}
        
        # 更新状态为处理中
        cur.execute("""
            UPDATE withdrawals
            SET status = 'processing'
            WHERE withdrawal_id = %s
        """, (withdrawal_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        # 模拟转账延迟
        await asyncio.sleep(3)
        
        # 调用转账函数 (虚拟实现,后续替换为真实 API)
        result = await transfer_sol_to_address(
            withdrawal['sol_address'],
            withdrawal['amount']
        )
        
        # 更新提现记录
        conn = get_db_connection()
        cur = conn.cursor()
        
        if result['success']:
            cur.execute("""
                UPDATE withdrawals
                SET status = 'completed',
                    tx_hash = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE withdrawal_id = %s
            """, (result['tx_hash'], withdrawal_id))
            
            logger.info(f"✅ Withdrawal completed: withdrawal_id={withdrawal_id}, tx_hash={result['tx_hash']}")
        else:
            cur.execute("""
                UPDATE withdrawals
                SET status = 'failed',
                    error_message = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE withdrawal_id = %s
            """, (result['error'], withdrawal_id))
            
            # 退还余额
            cur.execute("""
                UPDATE users
                SET total_node_power = total_node_power + %s
                WHERE user_id = %s
            """, (withdrawal['amount'], withdrawal['user_id']))
            
            logger.error(f"❌ Withdrawal failed: withdrawal_id={withdrawal_id}, error={result['error']}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to process withdrawal: {e}", exc_info=True)
        
        # 更新为失败状态并退还余额
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE withdrawals
                SET status = 'failed',
                    error_message = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE withdrawal_id = %s
            """, (str(e), withdrawal_id))
            
            # 获取金额和用户ID以退还余额
            cur.execute("""
                SELECT user_id, amount FROM withdrawals WHERE withdrawal_id = %s
            """, (withdrawal_id,))
            wd = cur.fetchone()
            
            if wd:
                cur.execute("""
                    UPDATE users
                    SET total_node_power = total_node_power + %s
                    WHERE user_id = %s
                """, (wd['amount'], wd['user_id']))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as rollback_error:
            logger.error(f"❌ Failed to rollback withdrawal: {rollback_error}")
        
        return {'success': False, 'error': str(e)}

async def transfer_sol_to_address(sol_address: str, amount: float) -> dict:
    """
    转账到 SOL 地址 (虚拟实现)
    
    后续替换为真实的 SOL 转账 API 调用
    
    返回格式:
    {
        'success': True/False,
        'tx_hash': '交易哈希' (成功时),
        'error': '错误信息' (失败时)
    }
    """
    try:
        # TODO: 替换为真实的 SOL 转账 API
        # 示例:
        # response = await external_api.transfer_sol(
        #     to_address=sol_address,
        #     amount=amount
        # )
        # return {
        #     'success': True,
        #     'tx_hash': response['transaction_hash']
        # }
        
        # 虚拟实现: 模拟成功
        logger.info(f"🔄 [MOCK] Transferring {amount} X2C to {sol_address}")
        
        # 模拟生成交易哈希
        import hashlib
        import time
        mock_tx_hash = hashlib.sha256(f"{sol_address}{amount}{time.time()}".encode()).hexdigest()
        
        logger.info(f"✅ [MOCK] Transfer successful: tx_hash={mock_tx_hash}")
        
        return {
            'success': True,
            'tx_hash': mock_tx_hash
        }
        
    except Exception as e:
        logger.error(f"❌ Transfer failed: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }

def get_user_balance(user_id: int) -> float:
    """获取用户余额"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT total_node_power FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return float(user['total_node_power']) if user else 0.0
        
    except Exception as e:
        logger.error(f"❌ Failed to get user balance: {e}", exc_info=True)
        return 0.0
