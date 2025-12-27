"""
Giggle API 真实转账测试（修复后的签名）
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


def sort_dict_keys(obj):
    """递归排序字典的所有键"""
    if isinstance(obj, dict):
        return {k: sort_dict_keys(obj[k]) for k in sorted(obj.keys())}
    elif isinstance(obj, list):
        return [sort_dict_keys(item) for item in obj]
    else:
        return obj


def generate_signature(params: dict, app_secret: str = GIGGLE_API_KEY) -> str:
    """生成 Giggle API 签名（修复版本）"""
    try:
        # 过滤空值参数
        filtered_params = {k: v for k, v in params.items() if v is not None and v != "" and k != "sign"}
        
        # 递归排序所有键
        sorted_params = sort_dict_keys(filtered_params)
        
        # 按 ASCII 码排序顶级键
        sorted_items = sorted(sorted_params.items())
        
        # 拼接参数字符串
        param_parts = []
        for k, v in sorted_items:
            if isinstance(v, (dict, list)):
                v_str = json.dumps(v, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
            else:
                v_str = str(v)
            param_parts.append(f"{k}={v_str}")
        
        param_str = ",".join(param_parts)
        sign_str = f"{param_str},key={app_secret}"
        signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
        
        print(f"[Signature] Generated: {signature}")
        return signature
        
    except Exception as e:
        print(f"[Signature] Failed: {e}")
        raise


def batch_transfer(to_address: str, amount: str) -> dict:
    """发起批量转账请求"""
    try:
        batch_id = f"test_transfer_{int(time.time() * 1000)}"
        request_id = f"req_{int(time.time())}"
        
        transfers = [{
            "request_id": request_id,
            "from_address": "",
            "to_address": to_address,
            "amount": amount,
            "memo": f"Test transfer {amount} X2C",
            "callback_url": ""
        }]
        
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
        
        signature = generate_signature(params)
        params["sign"] = signature
        
        print(f"\n[Transfer] Initiating transfer...")
        print(f"  - Batch ID: {batch_id}")
        print(f"  - To Address: {to_address}")
        print(f"  - Amount: {amount} X2C")
        
        response = requests.post(
            f"{GIGGLE_API_URL}/batch-transfers",
            json=params,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        
        response.raise_for_status()
        result = response.json()
        
        print(f"\n[Transfer Response] code={result.get('code')}")
        
        if result.get("code") != 0:
            print(f"❌ API error: {result.get('msg')}")
            return None
        
        data = result.get("data", {})
        transfer_data = data.get("transfers", [{}])[0]
        
        print(f"✅ Transfer initiated successfully!")
        print(f"  - Status: {transfer_data.get('status')}")
        
        return {
            "batch_id": batch_id,
            "request_id": request_id,
            "status": transfer_data.get("status", "PENDING"),
            "tx_hash": transfer_data.get("tx_hash", ""),
            "to_address": to_address,
            "amount": amount
        }
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None


def query_transfer_status(batch_id: str) -> dict:
    """查询转账状态"""
    try:
        timestamp = int(time.time())
        params = {
            "batch_id": batch_id,
            "appid": GIGGLE_APP_ID,
            "timestamp": timestamp
        }
        
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
        
        if result.get("code") != 0:
            print(f"❌ Query error: {result.get('msg')}")
            return None
        
        data = result.get("data", {})
        return {
            "batch_id": batch_id,
            "batch_status": data.get("status", "PROCESSING"),
            "transfers": data.get("transfers", [])
        }
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return None


def wait_for_transfer_completion(batch_id: str, max_retries: int = 24, retry_interval: int = 5) -> str:
    """等待转账完成"""
    print(f"\n[Query] Waiting for transfer completion...")
    
    for attempt in range(max_retries):
        time.sleep(retry_interval)
        
        print(f"\n[Query] Attempt {attempt + 1}/{max_retries}")
        query_result = query_transfer_status(batch_id)
        
        if not query_result:
            print(f"⚠️  Query failed, retrying...")
            continue
        
        transfers = query_result.get("transfers", [])
        
        if transfers:
            transfer = transfers[0]
            status = transfer.get("status", "PENDING")
            tx_hash = transfer.get("tx_hash", "")
            
            print(f"  - Status: {status}")
            print(f"  - TX Hash: {tx_hash if tx_hash else 'N/A'}")
            
            if status == "SUCCESS":
                print(f"\n✅ Transfer completed!")
                return tx_hash
            elif status in ("FAILED", "CANCELLED"):
                print(f"\n❌ Transfer {status.lower()}")
                return None
            elif status in ("PENDING", "PROCESSING"):
                print(f"  - Waiting...")
                continue
    
    print(f"\n⚠️  Transfer timeout")
    return None


def main():
    print("=" * 60)
    print("Giggle API Real Transfer Test")
    print("=" * 60)
    print(f"Target: {TEST_TO_ADDRESS}")
    print(f"Amount: {TEST_AMOUNT} X2C")
    print("=" * 60)
    
    transfer_result = batch_transfer(TEST_TO_ADDRESS, TEST_AMOUNT)
    
    if not transfer_result:
        print("\n❌ Failed to initiate transfer")
        return
    
    batch_id = transfer_result["batch_id"]
    tx_hash = wait_for_transfer_completion(batch_id)
    
    print("\n" + "=" * 60)
    print("Result")
    print("=" * 60)
    
    if tx_hash:
        print(f"✅ SUCCESS")
        print(f"TX Hash: {tx_hash}")
    else:
        print(f"❌ FAILED")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
