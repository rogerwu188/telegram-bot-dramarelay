"""
Solana 转账 Callback 处理模块 - 处理 Giggle API 的回调通知
"""

import hashlib
import json
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Giggle API 配置
GIGGLE_APP_SECRET = "C8laAnozXqbG9l0PaHRmKBcSuzuS8fcL"


def verify_callback_signature(callback_data: Dict[str, Any], provided_sign: str) -> bool:
    """
    验证 Callback 请求的签名
    
    签名步骤：
    1. 提取 batch_id, status, summary, transfers
    2. 按 ASCII 码排序
    3. 拼接为 key1=value1,key2=value2,... 格式
    4. 追加 ,key=<app_secret>
    5. 计算 MD5 并转大写
    
    Args:
        callback_data: 回调数据字典（不包含 sign 字段）
        provided_sign: 提供的签名
        
    Returns:
        签名是否有效
    """
    try:
        # 1. 提取需要签名的字段
        sign_params = {
            "batch_id": callback_data.get("batch_id"),
            "status": callback_data.get("status"),
            "summary": callback_data.get("summary"),
            "transfers": callback_data.get("transfers")
        }
        
        # 2. 参数排序（ASCII 码）
        sorted_items = sorted(sign_params.items())
        
        # 3. 拼接参数字符串
        param_parts = []
        for k, v in sorted_items:
            if isinstance(v, list):
                # 对列表中的每个对象进行字段排序
                sorted_list = []
                for item in v:
                    if isinstance(item, dict):
                        # 对字典的键进行排序
                        sorted_item = {key: item[key] for key in sorted(item.keys())}
                        sorted_list.append(sorted_item)
                    else:
                        sorted_list.append(item)
                # 使用 separators 确保紧凑格式（无空格）
                v_str = json.dumps(sorted_list, separators=(',', ':'), ensure_ascii=False)
            elif isinstance(v, dict):
                # 对字典的键进行排序
                sorted_dict = {key: v[key] for key in sorted(v.keys())}
                v_str = json.dumps(sorted_dict, separators=(',', ':'), ensure_ascii=False)
            else:
                v_str = str(v)
            param_parts.append(f"{k}={v_str}")
        
        param_str = ",".join(param_parts)
        
        # 4. 追加密钥
        sign_str = f"{param_str},key={GIGGLE_APP_SECRET}"
        
        # 5. 计算 MD5
        calculated_sign = hashlib.md5(sign_str.encode()).hexdigest().upper()
        
        logger.debug(f"[Callback] Sign string: {sign_str}")
        logger.debug(f"[Callback] Calculated sign: {calculated_sign}")
        logger.debug(f"[Callback] Provided sign: {provided_sign}")
        
        # 6. 比较签名
        is_valid = calculated_sign == provided_sign
        if is_valid:
            logger.info(f"[Callback] Signature verified successfully")
        else:
            logger.error(f"[Callback] Signature verification failed")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"[Callback] Failed to verify signature: {e}")
        return False


def process_callback(callback_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理 Giggle API 的 Callback 回调
    
    Args:
        callback_data: 回调数据，包含以下字段：
            - batch_id: 批次 ID
            - status: 批次状态 (SUCCESS/FAILED/CANCELLED)
            - summary: 统计信息 {total, success, failed, pending}
            - transfers: 转账列表，每项包含：
                - request_id: 请求 ID
                - status: 转账状态 (SUCCESS/FAILED)
                - tx_hash: 交易哈希
                - to_address: 收款地址
                - amount: 金额
            - sign: 签名
            
    Returns:
        处理结果 {success, message, transfers_processed}
    """
    try:
        batch_id = callback_data.get("batch_id")
        status = callback_data.get("status")
        transfers = callback_data.get("transfers", [])
        
        logger.info(f"[Callback] Processing callback: batch_id={batch_id}, status={status}, transfer_count={len(transfers)}")
        
        # 1. 验证签名
        provided_sign = callback_data.get("sign")
        if not provided_sign:
            logger.error(f"[Callback] Missing signature in callback")
            return {
                "success": False,
                "message": "Missing signature",
                "transfers_processed": 0
            }
        
        # 创建签名验证用的数据（不包含 sign 字段）
        sign_verify_data = {
            "batch_id": batch_id,
            "status": status,
            "summary": callback_data.get("summary"),
            "transfers": transfers
        }
        
        if not verify_callback_signature(sign_verify_data, provided_sign):
            logger.error(f"[Callback] Signature verification failed: batch_id={batch_id}")
            return {
                "success": False,
                "message": "Signature verification failed",
                "transfers_processed": 0
            }
        
        # 2. 处理每笔转账
        transfers_processed = 0
        
        for transfer in transfers:
            request_id = transfer.get("request_id")
            transfer_status = transfer.get("status")
            tx_hash = transfer.get("tx_hash", "")
            to_address = transfer.get("to_address")
            amount = transfer.get("amount")
            
            logger.info(f"[Callback] Processing transfer: request_id={request_id}, status={transfer_status}, tx_hash={tx_hash}")
            
            # 根据 request_id 查找对应的提现申请
            # request_id 格式: "withdrawal_{withdrawal_id}"
            if request_id.startswith("withdrawal_"):
                try:
                    withdrawal_id = int(request_id.split("_")[1])
                    
                    # 根据转账状态更新提现记录
                    if transfer_status == "SUCCESS":
                        # 转账成功
                        update_withdrawal_status(
                            withdrawal_id=withdrawal_id,
                            status="completed",
                            tx_hash=tx_hash,
                            batch_id=batch_id
                        )
                        logger.info(f"[Callback] Transfer success: withdrawal_id={withdrawal_id}, tx_hash={tx_hash}")
                    else:
                        # 转账失败
                        update_withdrawal_status(
                            withdrawal_id=withdrawal_id,
                            status="failed",
                            error_message=f"Transfer failed: {transfer_status}",
                            batch_id=batch_id
                        )
                        logger.error(f"[Callback] Transfer failed: withdrawal_id={withdrawal_id}, status={transfer_status}")
                    
                    transfers_processed += 1
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"[Callback] Failed to parse withdrawal_id from request_id: {request_id}, error: {e}")
            else:
                logger.warning(f"[Callback] Unexpected request_id format: {request_id}")
        
        logger.info(f"[Callback] Callback processed: batch_id={batch_id}, transfers_processed={transfers_processed}")
        
        return {
            "success": True,
            "message": "Callback processed successfully",
            "transfers_processed": transfers_processed
        }
        
    except Exception as e:
        logger.error(f"[Callback] Failed to process callback: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": str(e),
            "transfers_processed": 0
        }


def update_withdrawal_status(
    withdrawal_id: int,
    status: str,
    tx_hash: Optional[str] = None,
    error_message: Optional[str] = None,
    batch_id: Optional[str] = None
) -> bool:
    """
    更新提现申请状态
    
    Args:
        withdrawal_id: 提现申请 ID
        status: 新状态 (completed/failed)
        tx_hash: 交易哈希
        error_message: 错误信息
        batch_id: 批次 ID
        
    Returns:
        是否更新成功
    """
    try:
        from admin_api import get_db_connection
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if status == "completed":
            cur.execute("""
                UPDATE withdrawals
                SET status = 'completed',
                    tx_hash = %s,
                    batch_id = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE withdrawal_id = %s
            """, (tx_hash, batch_id, withdrawal_id))
        elif status == "failed":
            cur.execute("""
                UPDATE withdrawals
                SET status = 'failed',
                    error_message = %s,
                    batch_id = %s,
                    processed_at = CURRENT_TIMESTAMP
                WHERE withdrawal_id = %s
            """, (error_message, batch_id, withdrawal_id))
        else:
            logger.warning(f"[Callback] Unknown status: {status}")
            cur.close()
            conn.close()
            return False
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"[Callback] Updated withdrawal status: withdrawal_id={withdrawal_id}, status={status}")
        
        # 通知 X2C Web 更新提现状态
        try:
            import os
            x2c_web_url = os.environ.get('X2C_WEB_WEBHOOK_URL', 'https://x2c-web.manus.space/api/webhook/withdrawal-status')
            x2c_web_api_key = os.environ.get('X2C_WEB_API_KEY', '')
            if x2c_web_api_key:
                webhook_data = {
                    'withdrawalId': withdrawal_id,
                    'status': status,
                    'processedAt': datetime.now().isoformat()
                }
                if tx_hash:
                    webhook_data['txHash'] = tx_hash
                if error_message:
                    webhook_data['errorMessage'] = error_message
                
                requests.post(
                    x2c_web_url,
                    json=webhook_data,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {x2c_web_api_key}'
                    },
                    timeout=5
                )
                logger.info(f"[Callback] Notified X2C Web about withdrawal status: withdrawal_id={withdrawal_id}, status={status}")
        except Exception as webhook_error:
            logger.warning(f"[Callback] Failed to notify X2C Web: {webhook_error}")
        
        return True
        
    except Exception as e:
        logger.error(f"[Callback] Failed to update withdrawal status: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
