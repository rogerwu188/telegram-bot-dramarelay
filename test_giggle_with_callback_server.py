#!/usr/bin/env python3
"""
Giggle API 转账服务完整测试 - 带有真实 Callback 服务器

测试流程：
1. 启动本地 HTTP 服务器接收 Callback
2. 发起转账请求（包含 callback_url）
3. 轮询查询转账状态
4. 接收 Callback 回调
5. 输出最终交易哈希
"""

import os
import sys
import json
import time
import hashlib
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# ============================================================================
# 配置
# ============================================================================

GIGGLE_API_URL = "https://api-gv1.giggle.fun"
GIGGLE_APP_ID = "1WyXH9uE2UKCt5DqaV"
GIGGLE_APP_SECRET = "C8laAnozXqbG9l0PaHRmKBcSuzuS8fcL"

TO_ADDRESS = "8yfhM9wDAF7UkguPrwqWj4qxLm1R2wWAtqwqma8Q53Ci"
AMOUNT = "10"
ASSET_SYMBOL = "x2c"
CHAIN = "sol"
FROM_ADDRESS = "6aaqtgfdDY9Xh1upeucyMMJuyk5VMpw5FNZvSCD3js1w"

# Callback 服务器配置
CALLBACK_HOST = "0.0.0.0"
CALLBACK_PORT = 8888
CALLBACK_URL = f"http://127.0.0.1:{CALLBACK_PORT}/api/solana/callback"

# 全局变量
callback_received = False
callback_tx_hash = None
callback_event = threading.Event()

# ============================================================================
# Callback 服务器
# ============================================================================

class CallbackHandler(BaseHTTPRequestHandler):
    """处理 Giggle API 的 Callback 回调"""
    
    def do_POST(self):
        global callback_received, callback_tx_hash
        
        if self.path == "/api/solana/callback":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            try:
                callback_data = json.loads(body.decode('utf-8'))
                
                print(f"\n{'='*70}")
                print(f"[CALLBACK] 接收到 Callback 回调")
                print(f"{'='*70}")
                print(f"Batch ID: {callback_data.get('batch_id')}")
                print(f"Status: {callback_data.get('status')}")
                
                # 验证签名
                if verify_callback_signature(callback_data):
                    print(f"✅ 签名验证成功")
                    
                    # 提取转账结果
                    transfers = callback_data.get("transfers", [])
                    if transfers:
                        transfer = transfers[0]
                        status = transfer.get("status")
                        tx_hash = transfer.get("tx_hash", "")
                        
                        print(f"Transfer Status: {status}")
                        print(f"TX Hash: {tx_hash}")
                        
                        if status == "SUCCESS" and tx_hash:
                            callback_tx_hash = tx_hash
                            callback_received = True
                            callback_event.set()
                    
                    # 返回成功响应
                    response = json.dumps({"code": 0, "data": None, "msg": ""})
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', len(response))
                    self.end_headers()
                    self.wfile.write(response.encode())
                else:
                    print(f"❌ 签名验证失败")
                    response = json.dumps({"code": 1, "msg": "Signature verification failed"})
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', len(response))
                    self.end_headers()
                    self.wfile.write(response.encode())
                    
            except Exception as e:
                print(f"❌ Callback 处理异常: {e}")
                response = json.dumps({"code": 1, "msg": str(e)})
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', len(response))
                self.end_headers()
                self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # 抑制默认日志
        pass


def start_callback_server():
    """启动 Callback 服务器"""
    print(f"\n[Callback Server] 启动服务器...")
    print(f"  监听地址: {CALLBACK_HOST}:{CALLBACK_PORT}")
    print(f"  Callback URL: {CALLBACK_URL}")
    
    server = HTTPServer((CALLBACK_HOST, CALLBACK_PORT), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    time.sleep(0.5)  # 等待服务器启动
    print(f"✅ Callback 服务器已启动")
    
    return server


# ============================================================================
# 工具函数
# ============================================================================

def generate_signature(params: Dict[str, Any], secret: str) -> str:
    """生成 Giggle API 签名"""
    sign_fields = [
        "appid", "asset_symbol", "batch_id", "callback_url", "chain",
        "default_from_address", "timestamp", "transfers"
    ]
    
    sign_parts = []
    for field in sorted(sign_fields):
        if field in params:
            value = params[field]
            if isinstance(value, list):
                value = json.dumps(value, separators=(',', ':'), sort_keys=True)
            elif isinstance(value, dict):
                value = json.dumps(value, separators=(',', ':'), sort_keys=True)
            sign_parts.append(f"{field}={value}")
    
    sign_string = ",".join(sign_parts) + f",key={secret}"
    signature = hashlib.md5(sign_string.encode()).hexdigest().upper()
    return signature


def verify_callback_signature(callback_data: Dict[str, Any]) -> bool:
    """验证 Callback 签名"""
    provided_sign = callback_data.get("sign", "")
    
    # 提取需要签名的字段
    verify_params = {
        "batch_id": callback_data.get("batch_id"),
        "status": callback_data.get("status"),
        "summary": callback_data.get("summary"),
        "transfers": callback_data.get("transfers")
    }
    
    expected_sign = generate_signature(verify_params, GIGGLE_APP_SECRET)
    
    return expected_sign == provided_sign


def batch_transfer(to_address: str, amount: str, withdrawal_id: int = 1) -> Optional[Dict[str, Any]]:
    """发起批量转账请求"""
    print(f"\n{'='*70}")
    print(f"[STEP 1] 发起转账请求")
    print(f"{'='*70}")
    
    timestamp = int(time.time())
    unique_id = int(time.time() * 1000) % 1000000
    batch_id = f"test_transfer_{unique_id}"
    
    transfers = [{
        "request_id": f"withdrawal_test_{unique_id}",
        "from_address": "",
        "to_address": to_address,
        "amount": amount,
        "memo": f"X2C test withdrawal",
        "callback_url": ""
    }]
    
    params = {
        "batch_id": batch_id,
        "asset_symbol": ASSET_SYMBOL,
        "chain": CHAIN,
        "default_from_address": FROM_ADDRESS,
        "callback_url": CALLBACK_URL,  # 提供真实的 callback_url
        "transfers": transfers,
        "appid": GIGGLE_APP_ID,
        "timestamp": timestamp
    }
    
    signature = generate_signature(params, GIGGLE_APP_SECRET)
    params["sign"] = signature
    
    print(f"Batch ID: {batch_id}")
    print(f"Request ID: {transfers[0]['request_id']}")
    print(f"To Address: {to_address}")
    print(f"Amount: {amount} {ASSET_SYMBOL}")
    print(f"Callback URL: {CALLBACK_URL}")
    
    try:
        response = requests.post(f"{GIGGLE_API_URL}/batch-transfers", json=params, timeout=10)
        result = response.json()
        
        if result.get("code") == 0 and result.get("data"):
            data = result["data"]
            print(f"\n✅ 转账请求成功")
            print(f"   Batch ID: {data.get('batch_id')}")
            print(f"   Status: {data.get('status')}")
            return data
        else:
            print(f"\n❌ 转账请求失败: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        return None


def query_transfer_status(batch_id: str) -> Optional[Dict[str, Any]]:
    """查询转账状态"""
    timestamp = int(time.time())
    
    params = {
        "batch_id": batch_id,
        "appid": GIGGLE_APP_ID,
        "timestamp": timestamp
    }
    
    signature = generate_signature(params, GIGGLE_APP_SECRET)
    params["sign"] = signature
    
    try:
        response = requests.post(f"{GIGGLE_API_URL}/batch-transfers-query", json=params, timeout=10)
        result = response.json()
        
        if result.get("code") == 0 and result.get("data"):
            return result["data"]
        else:
            return None
    except Exception as e:
        return None


def poll_transfer_status(batch_id: str, max_duration: int = 120) -> Optional[str]:
    """轮询查询转账状态"""
    print(f"\n{'='*70}")
    print(f"[STEP 2] 轮询查询转账状态 + 等待 Callback")
    print(f"{'='*70}")
    
    current_interval = 2
    max_interval = 60
    backoff_multiplier = 1.5
    total_wait_time = 0
    retry_count = 0
    
    start_time = time.time()
    
    while total_wait_time < max_duration:
        # 等待指定时间后查询
        print(f"⏳ 等待 {current_interval}s 后进行第 {retry_count + 1} 次查询...")
        time.sleep(current_interval)
        total_wait_time += current_interval
        
        # 检查是否收到 Callback
        if callback_event.is_set():
            print(f"\n✅ 已收到 Callback 回调")
            return callback_tx_hash
        
        print(f"📊 查询转账状态 (总等待时间: {total_wait_time}s)")
        query_result = query_transfer_status(batch_id)
        
        if not query_result:
            print(f"⚠️  查询失败，将重试")
            retry_count += 1
            current_interval = min(current_interval * backoff_multiplier, max_interval)
            continue
        
        transfers = query_result.get("transfers", [])
        if transfers:
            transfer = transfers[0]
            status = transfer.get("status", "PENDING")
            tx_hash = transfer.get("tx_hash", "")
            
            print(f"   Status: {status}")
            if tx_hash:
                print(f"   TX Hash: {tx_hash}")
            
            if status == "SUCCESS" and tx_hash:
                print(f"✅ 转账成功!")
                return tx_hash
            elif status in ["FAILED", "CANCELLED"]:
                print(f"❌ 转账失败: {status}")
                return None
            elif status in ["PENDING", "PROCESSING"]:
                current_interval = min(current_interval * backoff_multiplier, max_interval)
        
        retry_count += 1
    
    # 轮询超时，等待 Callback
    print(f"\n⏹️  轮询超时 ({max_duration}s)")
    print(f"   等待 Callback 回调...")
    
    # 继续等待 Callback（最多 30 秒）
    print(f"   等待 Callback... (最多 30 秒)")
    if callback_event.wait(timeout=30):
        print(f"✅ 已收到 Callback 回调")
        return callback_tx_hash
    else:
        print(f"❌ 未收到 Callback 回调")
        return None


# ============================================================================
# 主测试流程
# ============================================================================

def main():
    """完整的转账测试流程"""
    print(f"\n{'#'*70}")
    print(f"# Giggle API 转账服务完整测试 (带 Callback 服务器)")
    print(f"{'#'*70}")
    
    print(f"\n测试参数:")
    print(f"  目标地址: {TO_ADDRESS}")
    print(f"  转账金额: {AMOUNT} {ASSET_SYMBOL}")
    print(f"  API 地址: {GIGGLE_API_URL}")
    
    # 启动 Callback 服务器
    server = start_callback_server()
    
    try:
        # STEP 1: 发起转账请求
        transfer_result = batch_transfer(TO_ADDRESS, AMOUNT)
        
        if not transfer_result:
            print(f"\n❌ 转账请求失败，测试中止")
            return None
        
        batch_id = transfer_result["batch_id"]
        
        # STEP 2: 轮询查询状态 + 等待 Callback
        tx_hash = poll_transfer_status(batch_id, max_duration=120)
        
        if tx_hash:
            print(f"\n{'='*70}")
            print(f"[RESULT] 转账完成")
            print(f"{'='*70}")
            print(f"✅ 交易成功")
            print(f"   TX Hash: {tx_hash}")
            return tx_hash
        else:
            print(f"\n{'='*70}")
            print(f"[RESULT] 转账失败或超时")
            print(f"{'='*70}")
            print(f"❌ 交易失败")
            return None
            
    finally:
        # 关闭服务器
        server.shutdown()


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
