"""
Solana 转账模块 - 基于 Giggle API 实现真实转账
"""

import hashlib
import json
import time
import logging
import requests
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Giggle API 配置
GIGGLE_API_URL = "https://api-gv1.giggle.fun"
GIGGLE_APP_ID = "1WyXH9uE2UKCt5DqaV"
GIGGLE_APP_SECRET = "C8laAnozXqbG9l0PaHRmKBcSuzuS8fcL"
GIGGLE_API_KEY = "DXrocNWEBkWS38Rp5Br1fcOZ0aHg3Unmu"

# Solana 配置
DEFAULT_FROM_ADDRESS = "6aaqtgfdDY9Xh1upeucyMMJuyk5VMpw5FNZvSCD3js1w"
ASSET_SYMBOL = "x2c"
CHAIN = "sol"

# 状态常量
BATCH_STATUS_PENDING = "PENDING"
BATCH_STATUS_PROCESSING = "PROCESSING"
BATCH_STATUS_SUCCESS = "SUCCESS"
BATCH_STATUS_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
BATCH_STATUS_FAILED = "FAILED"

TRANSFER_STATUS_PENDING = "PENDING"
TRANSFER_STATUS_PROCESSING = "PROCESSING"
TRANSFER_STATUS_SUCCESS = "SUCCESS"
TRANSFER_STATUS_FAILED = "FAILED"
TRANSFER_STATUS_CANCELLED = "CANCELLED"

SUCCESS_STATUSES = {TRANSFER_STATUS_SUCCESS}
FAILURE_STATUSES = {TRANSFER_STATUS_FAILED, TRANSFER_STATUS_CANCELLED}
PENDING_STATUSES = {TRANSFER_STATUS_PENDING, TRANSFER_STATUS_PROCESSING}


def generate_signature(params: Dict[str, Any], app_secret: str = GIGGLE_API_KEY) -> str:
    """
    生成 Giggle API 签名
    
    签名步骤：
    1. 参数按 ASCII 码排序
    2. 拼接为 key1=value1,key2=value2,... 格式
    3. 追加 ,key=<app_secret>
    4. 计算 MD5 并转大写
    
    Args:
        params: 请求参数字典
        app_secret: API 密钥
        
    Returns:
        MD5 签名（大写）
    """
    try:
        # 1. 不过滤任何字段（包括空值），只排除 sign 字段
        # 重要：所有字段都必须包含在签名字符串中，包括空字符串值
        filtered_params = {k: v for k, v in params.items() if k != "sign"}
        
        # 2. 参数排序（ASCII 码）
        sorted_items = sorted(filtered_params.items())
        
        # 3. 拼接参数字符串
        # 对于复杂类型（list），需要对内部对象的字段也进行排序
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
        sign_str = f"{param_str},key={app_secret}"
        
        # 5. MD5 并转大写
        signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
        
        logger.debug(f"[Signature] Generated: {signature}")
        logger.debug(f"[Signature] String to sign: {sign_str}")
        return signature
        
    except Exception as e:
        logger.error(f"[Signature] Failed to generate signature: {e}")
        raise


def batch_transfer(
    to_address: str,
    amount: str,
    withdrawal_id: int,
    asset_type: str = "x2c"
) -> Optional[Dict[str, Any]]:
    """
    执行批量转账（单笔）
    
    Args:
        to_address: 收款地址
        amount: 转账金额
        withdrawal_id: 提现申请 ID
        asset_type: 资产类型 (x2c 或 usdc)
        
    Returns:
        {
            'batch_id': 批次 ID,
            'request_id': 请求 ID,
            'status': 状态 (PENDING/SUCCESS/FAILED),
            'tx_hash': 交易哈希,
            'to_address': 收款地址,
            'amount': 金额
        }
        
        失败返回 None
    """
    try:
        # 生成批次 ID 和请求 ID
        batch_id = f"withdrawal_{withdrawal_id}_{int(time.time() * 1000)}"
        request_id = f"req_{withdrawal_id}"
        
        # 构建 Callback URL
        # 优先使用环境变量中的 URL，否则使用默认值
        import os
        callback_url = os.environ.get(
            'GIGGLE_CALLBACK_URL',
            'http://localhost:5001/api/solana/callback'
        )
        
        # 构建转账数据
        transfers = [
            {
                "request_id": f"withdrawal_{withdrawal_id}",  # 用于 Callback 中识别提现申请
                "from_address": "",  # 使用默认地址
                "to_address": to_address,
                "amount": amount,
                "memo": f"X2C withdrawal #{withdrawal_id}",
                "callback_url": ""  # 单笔转账不需要 callback_url
            }
        ]
        
        # 构建请求参数
        timestamp = int(time.time())
        params = {
            "batch_id": batch_id,
            "asset_symbol": ASSET_SYMBOL,
            "chain": CHAIN,
            "default_from_address": DEFAULT_FROM_ADDRESS,
            "callback_url": callback_url,  # 批次级别的 Callback URL
            "transfers": transfers,
            "appid": GIGGLE_APP_ID,
            "timestamp": timestamp
        }
        
        # 生成签名
        signature = generate_signature(params)
        params["sign"] = signature
        
        # 发起转账请求
        logger.info(f"[Transfer] Initiating transfer: withdrawal_id={withdrawal_id}, to={to_address}, amount={amount}, callback_url={callback_url}")
        
        response = requests.post(
            f"{GIGGLE_API_URL}/batch-transfers",
            json=params,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 检查响应状态
        if result.get("code") != 0:
            logger.error(f"[Transfer] API error: code={result.get('code')}, msg={result.get('msg')}")
            return None
        
        # 解析响应
        data = result.get("data", {})
        transfer_data = data.get("transfers", [{}])[0]
        
        logger.info(f"[Transfer] Success: batch_id={batch_id}, request_id={request_id}, status={transfer_data.get('status')}")
        
        return {
            "batch_id": batch_id,
            "request_id": f"withdrawal_{withdrawal_id}",  # 返回标准化的 request_id
            "status": transfer_data.get("status", "PENDING"),
            "tx_hash": transfer_data.get("tx_hash", ""),
            "to_address": to_address,
            "amount": amount,
            "asset_type": asset_type,
            "callback_url": callback_url
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"[Transfer] Request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"[Transfer] Failed to execute transfer: {e}")
        return None


def query_transfer_status(batch_id: str) -> Optional[Dict[str, Any]]:
    """
    查询转账状态
    
    Args:
        batch_id: 批次 ID
        
    Returns:
        {
            'batch_id': 批次 ID,
            'status': 批次状态 (PROCESSING/SUCCESS/FAILED),
            'transfers': [
                {
                    'request_id': 请求 ID,
                    'status': 转账状态 (PENDING/SUCCESS/FAILED),
                    'tx_hash': 交易哈希,
                    'to_address': 收款地址,
                    'amount': 金额
                }
            ]
        }
        
        失败返回 None
    """
    try:
        timestamp = int(time.time())
        params = {
            "batch_id": batch_id,
            "appid": GIGGLE_APP_ID,
            "timestamp": timestamp
        }
        
        # 生成签名
        signature = generate_signature(params)
        params["sign"] = signature
        
        logger.info(f"[Query] Querying transfer status: batch_id={batch_id}")
        
        response = requests.post(
            f"{GIGGLE_API_URL}/batch-transfers-query",
            json=params,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 检查响应状态
        if result.get("code") != 0:
            logger.error(f"[Query] API error: code={result.get('code')}, msg={result.get('msg')}")
            return None
        
        # 解析响应
        data = result.get("data", {})
        
        logger.info(f"[Query] Status: batch_id={batch_id}, status={data.get('status')}")
        
        return {
            "batch_id": batch_id,
            "status": data.get("status", "PROCESSING"),
            "transfers": data.get("transfers", [])
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"[Query] Request failed: {e}")
        return None
    except Exception as e:
        logger.error(f"[Query] Failed to query transfer status: {e}")
        return None


def execute_solana_transfer(
    to_address: str,
    amount: str,
    withdrawal_id: int,
    asset_type: str = "x2c"
) -> Optional[str]:
    """
    执行 Solana 转账（主函数）
    
    支持的状态：
    - 批次状态: PENDING, PROCESSING, SUCCESS, PARTIAL_SUCCESS, FAILED
    - 单个转账状态: PENDING, PROCESSING, SUCCESS, FAILED, CANCELLED
    
    Args:
        to_address: 收款地址
        amount: 转账金额
        withdrawal_id: 提现申请 ID
        asset_type: 资产类型
        
    Returns:
        交易哈希（tx_hash），失败返回 None
    """
    try:
        # 1. 发起转账
        transfer_result = batch_transfer(to_address, amount, withdrawal_id, asset_type)
        
        if not transfer_result:
            logger.error(f"[Execute] Failed to initiate transfer: withdrawal_id={withdrawal_id}")
            return None
        
        batch_id = transfer_result["batch_id"]
        
        # 2. 轮询查询状态（最多等待 60 秒）
        max_retries = 12
        retry_count = 0
        
        while retry_count < max_retries:
            time.sleep(5)  # 每 5 秒查询一次
            
            query_result = query_transfer_status(batch_id)
            
            if not query_result:
                logger.warning(f"[Execute] Query failed, retrying: batch_id={batch_id}")
                retry_count += 1
                continue
            
            # 检查转账状态
            transfers = query_result.get("transfers", [])
            if transfers:
                transfer = transfers[0]
                status = transfer.get("status", "PENDING")
                tx_hash = transfer.get("tx_hash", "")
                
                # 成功状态
                if status in SUCCESS_STATUSES:
                    logger.info(f"[Execute] Transfer success: batch_id={batch_id}, tx_hash={tx_hash}")
                    return tx_hash
                
                # 失败/取消状态
                elif status in FAILURE_STATUSES:
                    logger.error(f"[Execute] Transfer {status.lower()}: batch_id={batch_id}")
                    return None
                
                # 处理中状态
                elif status in PENDING_STATUSES:
                    logger.debug(f"[Execute] Transfer {status.lower()}: batch_id={batch_id}, retrying...")
                    # 继续轮询
                else:
                    logger.warning(f"[Execute] Unknown transfer status: {status}")
            
            retry_count += 1
        
        logger.warning(f"[Execute] Transfer timeout: batch_id={batch_id}")
        return None
        
    except Exception as e:
        logger.error(f"[Execute] Failed to execute transfer: {e}")
        return None
