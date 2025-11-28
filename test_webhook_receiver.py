#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook 接收端测试服务器
用于模拟外部系统接收 Webhook 回调
"""

from flask import Flask, request, jsonify
import hmac
import hashlib
import json
from datetime import datetime

app = Flask(__name__)

# 测试密钥 (与发送端保持一致)
TEST_SECRET = 'test_secret_key_2024'

def verify_signature(payload_str: str, signature: str, secret: str) -> bool:
    """验证 HMAC 签名"""
    expected_signature = 'sha256=' + hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.route('/webhook', methods=['POST'])
def receive_webhook():
    """接收 Webhook 回调"""
    print("\n" + "=" * 80)
    print(f"📥 收到 Webhook 回调 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 打印请求头
    print("\n📋 请求头:")
    for key, value in request.headers.items():
        if key.lower().startswith('x-webhook'):
            print(f"  {key}: {value}")
    
    # 获取请求体
    try:
        payload = request.get_json()
        payload_str = json.dumps(payload, ensure_ascii=False)
        
        print("\n📦 请求体:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        # 验证签名 (如果提供了密钥)
        signature = request.headers.get('X-Webhook-Signature')
        secret = request.headers.get('X-Webhook-Secret')
        
        if signature and secret:
            if verify_signature(payload_str, signature, secret):
                print("\n✅ 签名验证成功")
            else:
                print("\n❌ 签名验证失败")
                return jsonify({
                    'success': False,
                    'error': 'Invalid signature'
                }), 401
        else:
            print("\n⚠️  未提供签名,跳过验证")
        
        # 提取关键信息
        data = payload.get('data', {})
        print("\n📊 任务信息:")
        print(f"  - 任务 ID: {data.get('task_id')}")
        print(f"  - 任务标题: {data.get('task_title')}")
        print(f"  - 用户 ID: {data.get('user_id')}")
        print(f"  - 用户名: {data.get('username')}")
        print(f"  - 平台: {data.get('platform')}")
        print(f"  - 提交链接: {data.get('submission_link')}")
        print(f"  - 获得算力: {data.get('node_power_earned')}")
        print(f"  - 验证状态: {data.get('verification_status')}")
        
        verification_details = data.get('verification_details', {})
        if verification_details:
            print(f"\n🔍 验证详情:")
            print(f"  - 匹配成功: {verification_details.get('matched')}")
            print(f"  - 匹配率: {verification_details.get('match_rate')}%")
            print(f"  - 匹配关键词: {', '.join(verification_details.get('matched_keywords', []))}")
        
        print("\n" + "=" * 80)
        print("✅ Webhook 处理成功")
        print("=" * 80 + "\n")
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'message': 'Webhook received successfully',
            'received_at': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        print(f"\n❌ 处理 Webhook 时发生错误: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'message': 'Webhook receiver is running'
    }), 200

if __name__ == '__main__':
    print("=" * 80)
    print("🚀 启动 Webhook 接收端测试服务器")
    print("=" * 80)
    print(f"\n📍 服务地址: http://localhost:5001")
    print(f"📍 Webhook 端点: http://localhost:5001/webhook")
    print(f"📍 健康检查: http://localhost:5001/health")
    print(f"\n⚠️  测试密钥: {TEST_SECRET}")
    print("\n按 Ctrl+C 停止服务器\n")
    print("=" * 80 + "\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)
