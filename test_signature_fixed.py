"""
修复后的签名生成逻辑 - JSON 对象字段也需要排序
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


def sort_dict_keys(obj):
    """
    递归排序字典的所有键
    """
    if isinstance(obj, dict):
        return {k: sort_dict_keys(obj[k]) for k in sorted(obj.keys())}
    elif isinstance(obj, list):
        return [sort_dict_keys(item) for item in obj]
    else:
        return obj


def generate_signature_fixed(params: dict, app_secret: str) -> str:
    """
    修复后的签名生成 - 递归排序所有字典键
    """
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
            # 使用 separators 确保紧凑格式，sort_keys 确保键排序
            v_str = json.dumps(v, separators=(',', ':'), ensure_ascii=False, sort_keys=True)
        else:
            v_str = str(v)
        param_parts.append(f"{k}={v_str}")
    
    param_str = ",".join(param_parts)
    sign_str = f"{param_str},key={app_secret}"
    signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
    
    return signature, param_str


# 测试
print("=" * 80)
print("Testing Fixed Signature Generation")
print("=" * 80)

sig, param_str = generate_signature_fixed(OFFICIAL_EXAMPLE, OFFICIAL_SECRET)

print(f"\nGenerated String:")
print(f"{param_str}")

print(f"\nGenerated Signature:")
print(f"Expected: {OFFICIAL_EXPECTED}")
print(f"Actual:   {sig}")
print(f"Match: {'✅ YES' if sig == OFFICIAL_EXPECTED else '❌ NO'}")

