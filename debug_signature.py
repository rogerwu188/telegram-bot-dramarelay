#!/usr/bin/env python3
"""
签名调试脚本
显示 Webhook 请求的详细签名信息
"""

import hmac
import hashlib
import json
import time
from datetime import datetime

def generate_signature(payload_str: str, secret: str) -> str:
    """生成 HMAC-SHA256 签名"""
    return 'sha256=' + hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

# 测试数据
task_id = 38
user_id = 5156570084
platform = "tiktok"
submission_link = "https://www.tiktok.com/@wu.roger7/video/7577587517487107341"
node_power_earned = 10
secret = "X2C_WEBHOOK_SECRET"

# 构建 payload
payload = {
    'event': 'task.completed',
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'data': {
        'task_id': task_id,
        'task_title': '短剧片段 · 《ruthless-kindness》',
        'user_id': user_id,
        'username': 'test_user',
        'platform': platform,
        'submission_link': submission_link,
        'submitted_at': datetime.utcnow().isoformat() + 'Z',
        'verified_at': datetime.utcnow().isoformat() + 'Z',
        'node_power_earned': node_power_earned,
        'verification_status': 'verified',
        'verification_details': {
            'matched': True,
            'match_rate': 100,
            'matched_keywords': ['test']
        }
    }
}

# 生成 JSON 字符串 (ensure_ascii=False 保持中文)
payload_str = json.dumps(payload, ensure_ascii=False)

# 生成签名
signature = generate_signature(payload_str, secret)

# 显示信息
print("=" * 80)
print("🔐 Webhook 签名调试信息")
print("=" * 80)

print(f"\n📋 Secret:")
print(f"  {secret}")

print(f"\n📦 Payload (前 200 字符):")
print(f"  {payload_str[:200]}...")

print(f"\n📏 Payload 长度:")
print(f"  {len(payload_str)} 字节")

print(f"\n🔑 生成的签名:")
print(f"  {signature}")

print(f"\n📤 请求头:")
headers = {
    'Content-Type': 'application/json',
    'X-Webhook-Event': 'task.completed',
    'X-Webhook-Timestamp': str(int(time.time())),
    'X-Webhook-Secret': secret,
    'X-Webhook-Signature': signature,
    'User-Agent': 'X2C-Bot-Webhook/1.0'
}
for key, value in headers.items():
    print(f"  {key}: {value}")

print("\n" + "=" * 80)
print("📝 Supabase 端验证步骤:")
print("=" * 80)
print("""
1. 接收请求体 (body)
2. 读取 X-Webhook-Secret 头 (应该是: X2C_WEBHOOK_SECRET)
3. 读取 X-Webhook-Signature 头
4. 使用相同的 secret 对 body 生成签名:
   signature = 'sha256=' + hmac.new(
       secret.encode(),
       body.encode(),  # 注意: 必须是原始 JSON 字符串
       hashlib.sha256
   ).hexdigest()
5. 比较生成的签名与接收到的签名是否一致

⚠️ 注意事项:
- 必须使用原始的 JSON 字符串,不能先解析再序列化
- ensure_ascii=False 保持中文字符
- 签名格式必须是 'sha256=<hex_digest>'
""")

print("=" * 80)
