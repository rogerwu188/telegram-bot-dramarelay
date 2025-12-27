"""
调试签名生成逻辑
"""

import json
import hashlib

# 官方示例
OFFICIAL_EXAMPLE = {
    "batch_id": "KUGjbW2bMa4t9CysrvGEzP",
    "asset_symbol": "x2c",
    "chain": "sol",
    "default_from_address": "BXytRkCtk6eLPv2c2fWib3bAPpDmZvUo735JLrAhA1Rp",
    "callback_url": "http://127.0.0.1:8020/do",
    "transfers": [
        {
            "request_id": "req10",
            "from_address": "",
            "to_address": "7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p",
            "amount": "0.1",
            "memo": "req1 memo",
            "callback_url": ""
        }
    ],
    "appid": "AxyA5555GAQ2fgqQy",
    "timestamp": 1766644279
}

OFFICIAL_SECRET = "DXrocNWEBkWS38Rp5Br1fcOZ0aHg3Unmu"
OFFICIAL_EXPECTED = "D723C7EFF18E1E25301FC503BE2B22B9"

# 官方示例中的签名字符串
OFFICIAL_STRING = "appid=AxyA5555GAQ2fgqQy,asset_symbol=x2c,batch_id=KUGjbW2bMa4t9CysrvGEzP,callback_url=http://127.0.0.1:8020/do,chain=sol,default_from_address=BXytRkCtk6eLPv2c2fWib3bAPpDmZvUo735JLrAhA1Rp,timestamp=1766644279,transfers=[{\"amount\":\"0.1\",\"callback_url\":\"\",\"from_address\":\"\",\"memo\":\"req1 memo\",\"request_id\":\"req10\",\"to_address\":\"7Krw7trf1JDufFQWguhiiprXxDpHuftPHYTQYJvzop7p\"}]"


def test_official_example():
    """
    测试官方示例
    """
    print("=" * 80)
    print("Testing Official Example")
    print("=" * 80)
    
    # 直接验证官方示例中的签名字符串
    official_sign_str = f"{OFFICIAL_STRING},key={OFFICIAL_SECRET}"
    official_sig = hashlib.md5(official_sign_str.encode()).hexdigest().upper()
    
    print(f"\nOfficial String:")
    print(f"{OFFICIAL_STRING}")
    
    print(f"\nOfficial Signature:")
    print(f"Expected: {OFFICIAL_EXPECTED}")
    print(f"Actual:   {official_sig}")
    print(f"Match: {'✅ YES' if official_sig == OFFICIAL_EXPECTED else '❌ NO'}")
    
    # 测试方法 1: 紧凑 JSON
    print("\n" + "-" * 80)
    print("Method 1: Compact JSON Format")
    print("-" * 80)
    
    filtered_params = {k: v for k, v in OFFICIAL_EXAMPLE.items() if v is not None and v != "" and k != "sign"}
    sorted_items = sorted(filtered_params.items())
    
    param_parts = []
    for k, v in sorted_items:
        if isinstance(v, (dict, list)):
            v_str = json.dumps(v, separators=(',', ':'), ensure_ascii=False)
        else:
            v_str = str(v)
        param_parts.append(f"{k}={v_str}")
    
    param_str = ",".join(param_parts)
    sig1 = hashlib.md5(f"{param_str},key={OFFICIAL_SECRET}".encode()).hexdigest().upper()
    
    print(f"\nGenerated String:")
    print(f"{param_str}")
    
    print(f"\nGenerated Signature:")
    print(f"Expected: {OFFICIAL_EXPECTED}")
    print(f"Actual:   {sig1}")
    print(f"Match: {'✅ YES' if sig1 == OFFICIAL_EXPECTED else '❌ NO'}")
    
    # 比较字符串
    if param_str != OFFICIAL_STRING:
        print(f"\n⚠️  Generated string differs from official:")
        print(f"\nGenerated length: {len(param_str)}")
        print(f"Official length:  {len(OFFICIAL_STRING)}")
        
        # 找出差异
        min_len = min(len(param_str), len(OFFICIAL_STRING))
        for i in range(min_len):
            if param_str[i] != OFFICIAL_STRING[i]:
                print(f"\nFirst difference at position {i}:")
                print(f"Generated: '{param_str[i]}' (ord={ord(param_str[i])})")
                print(f"Official:  '{OFFICIAL_STRING[i]}' (ord={ord(OFFICIAL_STRING[i])})")
                print(f"Context (generated): ...{param_str[max(0, i-20):i+20]}...")
                print(f"Context (official):  ...{OFFICIAL_STRING[max(0, i-20):i+20]}...")
                break


if __name__ == "__main__":
    test_official_example()
