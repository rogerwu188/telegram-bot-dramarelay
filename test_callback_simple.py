#!/usr/bin/env python3
"""
简单测试：直接发送HTTP请求模拟回调
"""
import json
import hmac
import hashlib
import subprocess

# 回调数据（按照新的格式）
payload = {
    "site_name": "DramaRelayBot",
    "stats": [{
        "project_id": "test-project-20241129",
        "task_id": 888,  # external_task_id
        "duration": 30,
        "account_count": 1,
        "yt_view_count": 150,
        "yt_like_count": 20,
        "yt_account_count": 1
    }]
}

# 计算签名
secret = "test_secret_123"
payload_str = json.dumps(payload, separators=(',', ':'))
signature = hmac.new(
    secret.encode('utf-8'),
    payload_str.encode('utf-8'),
    hashlib.sha256
).hexdigest()

print("=" * 60)
print("模拟统计回传接口")
print("=" * 60)
print(f"\n回调数据：")
print(json.dumps(payload, indent=2))
print(f"\n签名：sha256={signature}")

# 发送HTTP请求
url = "https://webhook.site/b0cd07dc-d415-4caf-9a5b-c213b4adabe3"
cmd = [
    'curl', '-X', 'POST', url,
    '-H', 'Content-Type: application/json',
    '-H', f'X-Webhook-Signature: sha256={signature}',
    '-d', payload_str
]

print(f"\n发送请求到：{url}")
print(f"\n执行中...")

result = subprocess.run(cmd, capture_output=True, text=True)
print(f"\n响应状态码：{result.returncode}")
print(f"响应内容：{result.stdout}")

if result.returncode == 0:
    print("\n✅ 回调发送成功！")
    print(f"\n请访问以下URL查看接收到的数据：")
    print(f"https://webhook.site/#!/view/b0cd07dc-d415-4caf-9a5b-c213b4adabe3")
else:
    print(f"\n❌ 回调发送失败！")
    print(f"错误信息：{result.stderr}")

print("\n" + "=" * 60)
