"""
Solana 转账 Callback 流程测试
测试完整的 Callback 处理流程，包括签名验证和转账结果处理
"""

import json
import hashlib
import requests
from typing import Dict, Any

# 测试配置
GIGGLE_APP_SECRET = "C8laAnozXqbG9l0PaHRmKBcSuzuS8fcL"
CALLBACK_ENDPOINT = "http://localhost:5001/api/solana/callback"


def generate_callback_signature(callback_data: Dict[str, Any]) -> str:
    """生成 Callback 签名"""
    # 提取需要签名的字段
    sign_params = {
        "batch_id": callback_data.get("batch_id"),
        "status": callback_data.get("status"),
        "summary": callback_data.get("summary"),
        "transfers": callback_data.get("transfers")
    }
    
    # 参数排序（ASCII 码）
    sorted_items = sorted(sign_params.items())
    
    # 拼接参数字符串
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
    sign_str = f"{param_str},key={GIGGLE_APP_SECRET}"
    signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
    
    print(f"\n[Signature] Generated signature: {signature}")
    print(f"[Signature] Sign string: {sign_str}")
    
    return signature


def test_callback_success():
    """测试成功的 Callback"""
    print("\n" + "=" * 60)
    print("Test 1: Successful Transfer Callback")
    print("=" * 60)
    
    # 构建 Callback 数据
    callback_data = {
        "batch_id": "KUGjbW2bMa4t9CysrvG12P",
        "status": "SUCCESS",
        "summary": {
            "total": 1,
            "success": 1,
            "failed": 0,
            "pending": 0
        },
        "transfers": [
            {
                "request_id": "withdrawal_1",
                "status": "SUCCESS",
                "tx_hash": "3zz8hFVCwYf1kdjnMKJN8RVCAokQZc65VDrNULcEp2sZZrmeVtjtHuVEYyffexfLCNPwfZ3oGnq7GzXhwnJm5BwW",
                "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                "amount": "0.1"
            }
        ]
    }
    
    # 生成签名
    signature = generate_callback_signature(callback_data)
    callback_data["sign"] = signature
    
    # 发送 Callback
    print(f"\n[Request] Sending callback to {CALLBACK_ENDPOINT}")
    print(f"[Request] Payload: {json.dumps(callback_data, indent=2)}")
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=callback_data,
            timeout=10
        )
        
        print(f"\n[Response] Status: {response.status_code}")
        print(f"[Response] Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print("\n✅ Test passed: Callback processed successfully")
                return True
            else:
                print(f"\n❌ Test failed: Unexpected response code {result.get('code')}")
                return False
        else:
            print(f"\n❌ Test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_callback_failed():
    """测试失败的 Callback"""
    print("\n" + "=" * 60)
    print("Test 2: Failed Transfer Callback")
    print("=" * 60)
    
    # 构建 Callback 数据
    callback_data = {
        "batch_id": "KUGjbW2bMa4t9CysrvG12P",
        "status": "FAILED",
        "summary": {
            "total": 1,
            "success": 0,
            "failed": 1,
            "pending": 0
        },
        "transfers": [
            {
                "request_id": "withdrawal_2",
                "status": "FAILED",
                "tx_hash": "",
                "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                "amount": "0.1"
            }
        ]
    }
    
    # 生成签名
    signature = generate_callback_signature(callback_data)
    callback_data["sign"] = signature
    
    # 发送 Callback
    print(f"\n[Request] Sending callback to {CALLBACK_ENDPOINT}")
    print(f"[Request] Payload: {json.dumps(callback_data, indent=2)}")
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=callback_data,
            timeout=10
        )
        
        print(f"\n[Response] Status: {response.status_code}")
        print(f"[Response] Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print("\n✅ Test passed: Callback processed successfully")
                return True
            else:
                print(f"\n❌ Test failed: Unexpected response code {result.get('code')}")
                return False
        else:
            print(f"\n❌ Test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_callback_invalid_signature():
    """测试无效签名的 Callback"""
    print("\n" + "=" * 60)
    print("Test 3: Invalid Signature Callback")
    print("=" * 60)
    
    # 构建 Callback 数据
    callback_data = {
        "batch_id": "KUGjbW2bMa4t9CysrvG12P",
        "status": "SUCCESS",
        "summary": {
            "total": 1,
            "success": 1,
            "failed": 0,
            "pending": 0
        },
        "transfers": [
            {
                "request_id": "withdrawal_3",
                "status": "SUCCESS",
                "tx_hash": "3zz8hFVCwYf1kdjnMKJN8RVCAokQZc65VDrNULcEp2sZZrmeVtjtHuVEYyffexfLCNPwfZ3oGnq7GzXhwnJm5BwW",
                "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                "amount": "0.1"
            }
        ]
    }
    
    # 使用错误的签名
    callback_data["sign"] = "INVALID_SIGNATURE_12345"
    
    # 发送 Callback
    print(f"\n[Request] Sending callback to {CALLBACK_ENDPOINT}")
    print(f"[Request] Payload: {json.dumps(callback_data, indent=2)}")
    
    try:
        response = requests.post(
            CALLBACK_ENDPOINT,
            json=callback_data,
            timeout=10
        )
        
        print(f"\n[Response] Status: {response.status_code}")
        print(f"[Response] Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print("\n✅ Test passed: Callback processed (invalid signature handled)")
                return True
            else:
                print(f"\n❌ Test failed: Unexpected response code {result.get('code')}")
                return False
        else:
            print(f"\n❌ Test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


def test_official_example():
    """测试官方示例的签名"""
    print("\n" + "=" * 60)
    print("Test 4: Official Example Signature Verification")
    print("=" * 60)
    
    # 官方示例数据
    callback_data = {
        "batch_id": "KUGjbW2bMa4t9CysrvG12P",
        "status": "SUCCESS",
        "summary": {
            "total": 1,
            "success": 1,
            "failed": 0,
            "pending": 0
        },
        "transfers": [
            {
                "request_id": "req11",
                "status": "SUCCESS",
                "tx_hash": "3zz8hFVCwYf1kdjnMKJN8RVCAokQZc65VDrNULcEp2sZZrmeVtjtHuVEYyffexfLCNPwfZ3oGnq7GzXhwnJm5BwW",
                "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
                "amount": "0.1"
            }
        ]
    }
    
    # 官方示例签名
    official_sign = "14C047374B6E68470D80998B89D00443"
    
    # 生成签名
    generated_sign = generate_callback_signature(callback_data)
    
    print(f"\n[Verification]")
    print(f"  Official sign:  {official_sign}")
    print(f"  Generated sign: {generated_sign}")
    
    if generated_sign == official_sign:
        print("\n✅ Test passed: Signature matches official example")
        return True
    else:
        print("\n❌ Test failed: Signature does not match")
        return False


def main():
    print("=" * 60)
    print("Solana Transfer Callback Flow Test")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("Official Example Signature", test_official_example()))
    results.append(("Successful Transfer Callback", test_callback_success()))
    results.append(("Failed Transfer Callback", test_callback_failed()))
    results.append(("Invalid Signature Callback", test_callback_invalid_signature()))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
