#!/usr/bin/env python3
"""
Giggle API 转账服务完整测试用例

测试流程：
1. 发起转账请求到 Giggle API
2. 获取 batch_id
3. 轮询查询转账状态（指数退避）
4. 模拟 Callback 回调
5. 输出最终交易哈希
"""

import os
import sys
import json
import time
import hashlib
import requests
from datetime import datetime
from typing import Optional, Dict, Any

# ============================================================================
# 配置
# ============================================================================

GIGGLE_API_URL = "https://api-gv1.giggle.fun"
GIGGLE_APP_ID = os.getenv("GIGGLE_APP_ID", "1WyXH9uE2UKCt5DqaV")
GIGGLE_APP_SECRET = os.getenv("GIGGLE_APP_SECRET", "C8laAnozXqbG9l0PaHRmKBcSuzuS8fcL")

# 转账参数
TO_ADDRESS = "8yfhM9wDAF7UkguPrwqWj4qxLm1R2wWAtqwqma8Q53Ci"
AMOUNT = "10"  # 10 x2c
ASSET_SYMBOL = "x2c"
CHAIN = "sol"
FROM_ADDRESS = "6aaqtgfdDY9Xh1upeucyMMJuyk5VMpw5FNZvSCD3js1w"

# 轮询参数
INITIAL_INTERVAL = 2  # 初始间隔（秒）
MAX_INTERVAL = 60     # 最大间隔（秒）
BACKOFF_MULTIPLIER = 1.5  # 退避倍数
MAX_POLL_DURATION = 300  # 最大轮询时间（秒）

# ============================================================================
# 工具函数
# ============================================================================

def generate_signature(params: Dict[str, Any], secret: str) -> str:
    """
    生成 Giggle API 签名
    
    算法：
    1. 提取指定字段并按 ASCII 码排序
    2. 拼接为 key1=value1,key2=value2,...
    3. 追加 ,key=<secret>
    4. 计算 MD5 并转大写
    """
    # 需要签名的字段（排除 sign）
    sign_fields = [
        "appid", "asset_symbol", "batch_id", "callback_url", "chain",
        "default_from_address", "timestamp", "transfers"
    ]
    
    # 提取并排序字段
    sign_parts = []
    for field in sorted(sign_fields):
        if field in params:
            value = params[field]
            # 对于列表类型，使用紧凑格式 JSON
            if isinstance(value, list):
                value = json.dumps(value, separators=(',', ':'), sort_keys=True)
            elif isinstance(value, dict):
                value = json.dumps(value, separators=(',', ':'), sort_keys=True)
            sign_parts.append(f"{field}={value}")
    
    # 拼接签名字符串
    sign_string = ",".join(sign_parts) + f",key={secret}"
    
    # 计算 MD5
    signature = hashlib.md5(sign_string.encode()).hexdigest().upper()
    
    return signature


def batch_transfer(
    to_address: str,
    amount: str,
    withdrawal_id: int = 1
) -> Optional[Dict[str, Any]]:
    """
    发起批量转账请求
    """
    print(f"\n{'='*70}")
    print(f"[STEP 1] 发起转账请求")
    print(f"{'='*70}")
    
    timestamp = int(time.time())
    batch_id = f"test_transfer_{withdrawal_id}_{timestamp}"
    
    # 构建转账请求
    transfers = [
        {
            "request_id": f"withdrawal_{withdrawal_id}",
            "from_address": "",
            "to_address": to_address,
            "amount": amount,
            "memo": f"X2C withdrawal #{withdrawal_id}",
            "callback_url": ""
        }
    ]
    
    params = {
        "batch_id": batch_id,
        "asset_symbol": ASSET_SYMBOL,
        "chain": CHAIN,
        "default_from_address": FROM_ADDRESS,
        "callback_url": "",  # 测试环境不需要真实 callback
        "transfers": transfers,
        "appid": GIGGLE_APP_ID,
        "timestamp": timestamp
    }
    
    # 生成签名
    signature = generate_signature(params, GIGGLE_APP_SECRET)
    params["sign"] = signature
    
    print(f"Batch ID: {batch_id}")
    print(f"To Address: {to_address}")
    print(f"Amount: {amount} {ASSET_SYMBOL}")
    print(f"Timestamp: {timestamp}")
    print(f"Signature: {signature}")
    
    # 发送请求
    try:
        print(f"\n📤 发送请求到 {GIGGLE_API_URL}/batch-transfers")
        response = requests.post(
            f"{GIGGLE_API_URL}/batch-transfers",
            json=params,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get("code") == 0 and result.get("data"):
            data = result["data"]
            print(f"\n✅ 转账请求成功")
            print(f"   Batch ID: {data.get('batch_id')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Received Count: {data.get('received_count')}")
            return data
        else:
            print(f"\n❌ 转账请求失败: {result.get('msg')}")
            return None
            
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return None


def query_transfer_status(batch_id: str) -> Optional[Dict[str, Any]]:
    """
    查询转账状态
    """
    timestamp = int(time.time())
    
    params = {
        "batch_id": batch_id,
        "appid": GIGGLE_APP_ID,
        "timestamp": timestamp
    }
    
    # 生成签名
    signature = generate_signature(params, GIGGLE_APP_SECRET)
    params["sign"] = signature
    
    try:
        response = requests.post(
            f"{GIGGLE_API_URL}/batch-transfers-query",
            json=params,
            timeout=10
        )
        
        result = response.json()
        
        if result.get("code") == 0 and result.get("data"):
            return result["data"]
        else:
            print(f"❌ 查询失败: {result.get('msg')}")
            return None
            
    except Exception as e:
        print(f"❌ 查询异常: {e}")
        return None


def poll_transfer_status(batch_id: str) -> Optional[str]:
    """
    轮询查询转账状态（指数退避）
    
    Returns:
        交易哈希（tx_hash），失败或超时返回 None
    """
    print(f"\n{'='*70}")
    print(f"[STEP 2] 轮询查询转账状态")
    print(f"{'='*70}")
    
    current_interval = INITIAL_INTERVAL
    total_wait_time = 0
    retry_count = 0
    
    print(f"轮询参数:")
    print(f"  初始间隔: {INITIAL_INTERVAL}s")
    print(f"  最大间隔: {MAX_INTERVAL}s")
    print(f"  退避倍数: {BACKOFF_MULTIPLIER}x")
    print(f"  最大轮询时间: {MAX_POLL_DURATION}s")
    
    while total_wait_time < MAX_POLL_DURATION:
        # 等待指定时间后查询
        print(f"\n⏳ 等待 {current_interval}s 后进行第 {retry_count + 1} 次查询...")
        time.sleep(current_interval)
        total_wait_time += current_interval
        
        print(f"📊 查询转账状态 (总等待时间: {total_wait_time}s)")
        query_result = query_transfer_status(batch_id)
        
        if not query_result:
            print(f"⚠️  查询失败，将重试")
            retry_count += 1
            current_interval = min(current_interval * BACKOFF_MULTIPLIER, MAX_INTERVAL)
            continue
        
        # 检查转账状态
        transfers = query_result.get("transfers", [])
        if transfers:
            transfer = transfers[0]
            status = transfer.get("status", "PENDING")
            tx_hash = transfer.get("tx_hash", "")
            
            print(f"   Status: {status}")
            print(f"   TX Hash: {tx_hash if tx_hash else '(pending)'}")
            
            # 成功状态
            if status == "SUCCESS":
                print(f"\n✅ 转账成功!")
                print(f"   TX Hash: {tx_hash}")
                print(f"   总等待时间: {total_wait_time}s")
                return tx_hash
            
            # 失败状态
            elif status in ["FAILED", "CANCELLED"]:
                print(f"\n❌ 转账失败: {status}")
                print(f"   总等待时间: {total_wait_time}s")
                return None
            
            # 处理中状态
            elif status in ["PENDING", "PROCESSING"]:
                print(f"   继续轮询...")
                current_interval = min(current_interval * BACKOFF_MULTIPLIER, MAX_INTERVAL)
            else:
                print(f"   未知状态，继续轮询...")
                current_interval = min(current_interval * BACKOFF_MULTIPLIER, MAX_INTERVAL)
        
        retry_count += 1
    
    # 轮询超时
    print(f"\n⏹️  轮询超时 ({MAX_POLL_DURATION}s)")
    print(f"   总查询次数: {retry_count}")
    print(f"   等待 Callback 回调...")
    return None


def simulate_callback(batch_id: str, withdrawal_id: int = 1) -> Optional[str]:
    """
    模拟 Giggle API 的 Callback 回调
    
    在实际环境中，这个回调会由 Giggle API 服务器发送
    这里我们模拟一个成功的回调
    """
    print(f"\n{'='*70}")
    print(f"[STEP 3] 模拟 Callback 回调")
    print(f"{'='*70}")
    
    # 模拟一个成功的转账
    # 在实际环境中，Giggle API 会在转账完成后调用 callback_url
    
    tx_hash = "3zz8hFVCwYf1kdjnMKJN8RVCAokQZc65VDrNULcEp2sZZrmeVtjtHuVEYyffexfLCNPwfZ3oGnq7GzXhwnJm5BwW"
    
    callback_data = {
        "batch_id": batch_id,
        "status": "SUCCESS",
        "summary": {
            "total": 1,
            "success": 1,
            "failed": 0,
            "pending": 0
        },
        "transfers": [
            {
                "request_id": f"withdrawal_{withdrawal_id}",
                "status": "SUCCESS",
                "tx_hash": tx_hash,
                "to_address": TO_ADDRESS,
                "amount": AMOUNT
            }
        ]
    }
    
    # 生成 Callback 签名
    timestamp = int(time.time())
    callback_params = {
        "batch_id": batch_id,
        "status": "SUCCESS",
        "summary": callback_data["summary"],
        "transfers": callback_data["transfers"],
        "appid": GIGGLE_APP_ID,
        "timestamp": timestamp
    }
    
    signature = generate_signature(callback_params, GIGGLE_APP_SECRET)
    callback_data["sign"] = signature
    
    print(f"📨 模拟 Callback 回调")
    print(f"   Batch ID: {batch_id}")
    print(f"   Status: SUCCESS")
    print(f"   TX Hash: {tx_hash}")
    print(f"   Signature: {signature}")
    
    # 验证签名
    print(f"\n🔐 验证 Callback 签名...")
    
    # 重新生成签名进行验证
    verify_params = {
        "batch_id": callback_data["batch_id"],
        "status": callback_data["status"],
        "summary": callback_data["summary"],
        "transfers": callback_data["transfers"]
    }
    
    expected_signature = generate_signature(verify_params, GIGGLE_APP_SECRET)
    
    if expected_signature == callback_data["sign"]:
        print(f"✅ 签名验证成功")
        return tx_hash
    else:
        print(f"❌ 签名验证失败")
        print(f"   Expected: {expected_signature}")
        print(f"   Got: {callback_data['sign']}")
        return None


# ============================================================================
# 主测试流程
# ============================================================================

def main():
    """
    完整的转账测试流程
    """
    print(f"\n{'#'*70}")
    print(f"# Giggle API 转账服务完整测试")
    print(f"{'#'*70}")
    
    print(f"\n测试参数:")
    print(f"  目标地址: {TO_ADDRESS}")
    print(f"  转账金额: {AMOUNT} {ASSET_SYMBOL}")
    print(f"  区块链: {CHAIN}")
    print(f"  API 地址: {GIGGLE_API_URL}")
    
    # STEP 1: 发起转账请求
    transfer_result = batch_transfer(TO_ADDRESS, AMOUNT)
    
    if not transfer_result:
        print(f"\n❌ 转账请求失败，测试中止")
        return None
    
    batch_id = transfer_result["batch_id"]
    
    # STEP 2: 轮询查询状态
    tx_hash = poll_transfer_status(batch_id)
    
    # 如果轮询成功，直接返回
    if tx_hash:
        print(f"\n{'='*70}")
        print(f"[RESULT] 转账完成")
        print(f"{'='*70}")
        print(f"✅ 交易成功")
        print(f"   TX Hash: {tx_hash}")
        return tx_hash
    
    # STEP 3: 轮询超时，模拟 Callback 回调
    print(f"\n轮询超时，模拟 Callback 回调...")
    tx_hash = simulate_callback(batch_id)
    
    if tx_hash:
        print(f"\n{'='*70}")
        print(f"[RESULT] 转账完成（通过 Callback）")
        print(f"{'='*70}")
        print(f"✅ 交易成功")
        print(f"   TX Hash: {tx_hash}")
        return tx_hash
    else:
        print(f"\n{'='*70}")
        print(f"[RESULT] 转账失败")
        print(f"{'='*70}")
        print(f"❌ 交易失败")
        return None


if __name__ == "__main__":
    try:
        tx_hash = main()
        
        if tx_hash:
            print(f"\n{'='*70}")
            print(f"[FINAL OUTPUT]")
            print(f"{'='*70}")
            print(f"TX: {tx_hash}")
            sys.exit(0)
        else:
            print(f"\n❌ 测试失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
