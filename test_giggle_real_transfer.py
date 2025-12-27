"""
Giggle API 真实转账测试
针对 8yfhM9wDAF7UkguPrwqWj4qxLm1R2wWAtqwqma8Q53Ci 地址转账 10 个 X2C
"""

import requests
import json
import time
import hashlib
from datetime import datetime

# Giggle API 配置
GIGGLE_API_URL = "https://api-gv1.giggle.fun"
GIGGLE_APP_ID = "1WyXH9uE2UKCt5DqaV"
GIGGLE_APP_SECRET = "C8laAnozXqbG9l0PaHRmKBcSuzuS8fcL"
GIGGLE_API_KEY = "DXrocNWEBkWS38Rp5Br1fcOZ0aHg3Unmu"

# Solana 配置
DEFAULT_FROM_ADDRESS = "6aaqtgfdDY9Xh1upeucyMMJuyk5VMpw5FNZvSCD3js1w"
ASSET_SYMBOL = "x2c"
CHAIN = "sol"

# 测试参数
TEST_TO_ADDRESS = "8yfhM9wDAF7UkguPrwqWj4qxLm1R2wWAtqwqma8Q53Ci"
TEST_AMOUNT = "10"


def generate_signature(params: dict, app_secret: str = GIGGLE_API_KEY) -> str:
    """
    生成 Giggle API 签名
    """
    try:
        # 过滤空值参数并按 ASCII 码排序
        filtered_params = {k: v for k, v in params.items() if v is not None and v != "" and k != "sign"}
        
        # 参数排序（ASCII 码）
        sorted_items = sorted(filtered_params.items())
        
        # 拼接参数字符串
        param_parts = []
        for k, v in sorted_items:
            if isinstance(v, (dict, list)):
                # 使用 separators 确保紧凑格式（无空格）
                v_str = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
            else:
                v_str = str(v)
            param_parts.append(f"{k}={v_str}")
        
        param_str = ",".join(param_parts)
        
        # 追加密钥
        sign_str = f"{param_str},key={app_secret}"
        
        # MD5 并转大写
        signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
        
        print(f"[Signature] Generated: {signature}")
        return signature
        
    except Exception as e:
        print(f"[Signature] Failed: {e}")
        raise


def batch_transfer(to_address: str, amount: str) -> dict:
    """
    发起批量转账请求
    """
    try:
        # 生成批次 ID 和请求 ID
        batch_id = f"test_transfer_{int(time.time() * 1000)}"
        request_id = f"req_{int(time.time())}"
        
        # 构建转账数据
        transfers = [
            {
                "request_id": request_id,
                "from_address": "",
                "to_address": to_address,
                "amount": amount,
                "memo": f"Test transfer {amount} X2C",
                "callback_url": ""
            }
        ]
        
        # 构建请求参数
        timestamp = int(time.time())
        params = {
            "batch_id": batch_id,
            "asset_symbol": ASSET_SYMBOL,
            "chain": CHAIN,
            "default_from_address": DEFAULT_FROM_ADDRESS,
            "callback_url": "",
            "transfers": transfers,
            "appid": GIGGLE_APP_ID,
            "timestamp": timestamp
        }
        
        # 生成签名
        signature = generate_signature(params)
        params["sign"] = signature
        
        print(f"\n[Transfer] Initiating transfer...")
        print(f"  - Batch ID: {batch_id}")
        print(f"  - Request ID: {request_id}")
        print(f"  - To Address: {to_address}")
        print(f"  - Amount: {amount} X2C")
        
        # 发起转账请求
        response = requests.post(
            f"{GIGGLE_API_URL}/batch-transfers",
            json=params,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        result = response.json()
        
        print(f"\n[Transfer Response]")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 检查响应状态
        if result.get("code") != 0:
            print(f"❌ API error: code={result.get('code')}, msg={result.get('msg')}")
            return None
        
        # 解析响应
        data = result.get("data", {})
        transfer_data = data.get("transfers", [{}])[0]
        
        print(f"\n✅ Transfer initiated successfully!")
        print(f"  - Status: {transfer_data.get('status')}")
        print(f"  - TX Hash: {transfer_data.get('tx_hash', 'N/A')}")
        
        return {
            "batch_id": batch_id,
            "request_id": request_id,
            "status": transfer_data.get("status", "PENDING"),
            "tx_hash": transfer_data.get("tx_hash", ""),
            "to_address": to_address,
            "amount": amount
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to execute transfer: {e}")
        return None


def query_transfer_status(batch_id: str) -> dict:
    """
    查询转账状态
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
            print(f"❌ Query API error: code={result.get('code')}, msg={result.get('msg')}")
            return None
        
        # 解析响应
        data = result.get("data", {})
        
        return {
            "batch_id": batch_id,
            "batch_status": data.get("status", "PROCESSING"),
            "transfers": data.get("transfers", [])
        }
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Query request failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to query transfer status: {e}")
        return None


def wait_for_transfer_completion(batch_id: str, max_retries: int = 24, retry_interval: int = 5) -> str:
    """
    等待转账完成
    
    Args:
        batch_id: 批次 ID
        max_retries: 最大重试次数（24 * 5s = 120s）
        retry_interval: 重试间隔（秒）
        
    Returns:
        交易哈希或 None
    """
    print(f"\n[Query] Waiting for transfer completion (max {max_retries * retry_interval}s)...")
    
    for attempt in range(max_retries):
        time.sleep(retry_interval)
        
        print(f"\n[Query] Attempt {attempt + 1}/{max_retries}")
        query_result = query_transfer_status(batch_id)
        
        if not query_result:
            print(f"⚠️  Query failed, retrying...")
            continue
        
        batch_status = query_result.get("batch_status", "PROCESSING")
        transfers = query_result.get("transfers", [])
        
        print(f"  - Batch Status: {batch_status}")
        
        if transfers:
            transfer = transfers[0]
            status = transfer.get("status", "PENDING")
            tx_hash = transfer.get("tx_hash", "")
            
            print(f"  - Transfer Status: {status}")
            print(f"  - TX Hash: {tx_hash if tx_hash else 'N/A'}")
            
            # 成功状态
            if status == "SUCCESS":
                print(f"\n✅ Transfer completed successfully!")
                print(f"  - TX Hash: {tx_hash}")
                return tx_hash
            
            # 失败/取消状态
            elif status in ("FAILED", "CANCELLED"):
                print(f"\n❌ Transfer {status.lower()}")
                return None
            
            # 处理中状态
            elif status in ("PENDING", "PROCESSING"):
                print(f"  - Waiting for completion...")
                continue
        
        # 批次成功
        if batch_status == "SUCCESS":
            if transfers:
                tx_hash = transfers[0].get("tx_hash", "")
                if tx_hash:
                    print(f"\n✅ Transfer completed successfully!")
                    print(f"  - TX Hash: {tx_hash}")
                    return tx_hash
    
    print(f"\n⚠️  Transfer timeout after {max_retries * retry_interval}s")
    return None


def main():
    """
    主测试函数
    """
    print("=" * 60)
    print("Giggle API Real Transfer Test")
    print("=" * 60)
    print(f"Time: {datetime.now().isoformat()}")
    print(f"Target Address: {TEST_TO_ADDRESS}")
    print(f"Amount: {TEST_AMOUNT} X2C")
    print("=" * 60)
    
    # 1. 发起转账
    transfer_result = batch_transfer(TEST_TO_ADDRESS, TEST_AMOUNT)
    
    if not transfer_result:
        print("\n❌ Failed to initiate transfer")
        return
    
    batch_id = transfer_result["batch_id"]
    
    # 2. 等待转账完成
    tx_hash = wait_for_transfer_completion(batch_id)
    
    # 3. 打印最终结果
    print("\n" + "=" * 60)
    print("Test Result")
    print("=" * 60)
    
    if tx_hash:
        print(f"✅ Transfer Successful")
        print(f"  - Batch ID: {batch_id}")
        print(f"  - TX Hash: {tx_hash}")
        print(f"  - To Address: {TEST_TO_ADDRESS}")
        print(f"  - Amount: {TEST_AMOUNT} X2C")
        print(f"  - Time: {datetime.now().isoformat()}")
    else:
        print(f"❌ Transfer Failed or Timeout")
        print(f"  - Batch ID: {batch_id}")
        print(f"  - To Address: {TEST_TO_ADDRESS}")
        print(f"  - Amount: {TEST_AMOUNT} X2C")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
