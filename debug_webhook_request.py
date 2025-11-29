#!/usr/bin/env python3
"""
详细的 Webhook 请求调试脚本
显示完整的请求和响应信息
"""

import asyncio
import aiohttp
import hmac
import hashlib
import json
import time
from datetime import datetime

async def main():
    # 测试数据
    callback_url = "https://rxkcgquecleofqhyfchx.supabase.co/functions/v1/x2c-webhook-receiver"
    secret = "X2C_WEBHOOK_SECRET"
    
    # 构建 payload
    payload = {
        'event': 'task.completed',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'data': {
            'task_id': 38,
            'task_title': '短剧片段 · 《ruthless-kindness》',
            'user_id': 5156570084,
            'username': 'test_user',
            'platform': 'tiktok',
            'submission_link': 'https://www.tiktok.com/@wu.roger7/video/7577587517487107341',
            'submitted_at': datetime.utcnow().isoformat() + 'Z',
            'verified_at': datetime.utcnow().isoformat() + 'Z',
            'node_power_earned': 10,
            'verification_status': 'verified',
            'verification_details': {
                'matched': True,
                'match_rate': 100,
                'matched_keywords': ['test']
            }
        }
    }
    
    # 生成 JSON 字符串
    payload_str = json.dumps(payload, ensure_ascii=False)
    
    # 生成签名
    signature = 'sha256=' + hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # 准备请求头
    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Event': 'task.completed',
        'X-Webhook-Timestamp': str(int(time.time())),
        'X-Webhook-Secret': secret,
        'X-Webhook-Signature': signature,
        'User-Agent': 'X2C-Bot-Webhook/1.0'
    }
    
    print("=" * 80)
    print("🔍 Webhook 请求详细调试")
    print("=" * 80)
    
    print(f"\n📍 URL:")
    print(f"  {callback_url}")
    
    print(f"\n📤 请求头:")
    for key, value in headers.items():
        print(f"  {key}: {value}")
    
    print(f"\n📦 请求体 (JSON):")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    
    print(f"\n📏 请求体大小: {len(payload_str)} 字节")
    
    print(f"\n🔐 签名计算:")
    print(f"  Secret: {secret}")
    print(f"  Payload (前100字符): {payload_str[:100]}...")
    print(f"  Signature: {signature}")
    
    print(f"\n🚀 发送请求...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                callback_url,
                headers=headers,
                data=payload_str.encode('utf-8'),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                status = response.status
                response_text = await response.text()
                
                print(f"\n📥 响应:")
                print(f"  状态码: {status}")
                print(f"  响应头:")
                for key, value in response.headers.items():
                    print(f"    {key}: {value}")
                print(f"  响应体:")
                print(f"    {response_text}")
                
                if status == 200:
                    print(f"\n✅ Webhook 发送成功!")
                else:
                    print(f"\n❌ Webhook 发送失败!")
                    
                    # 尝试解析错误信息
                    try:
                        error_data = json.loads(response_text)
                        print(f"\n🔍 错误详情:")
                        print(json.dumps(error_data, indent=2, ensure_ascii=False))
                    except:
                        pass
                
    except Exception as e:
        print(f"\n❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
