# X2C Webhook 签名规则详细说明

## 🔐 签名算法

**算法:** HMAC-SHA256  
**输出格式:** `sha256=<hex_digest>`

---

## 📋 签名生成步骤

### 步骤 1: 准备 Payload 字符串

**关键点:**
- 使用 **JSON 序列化后的完整字符串**
- **必须使用原始的 JSON 字符串**,不能先解析再序列化
- 字符编码: **UTF-8**
- JSON 格式选项: `ensure_ascii=False` (保留中文字符)

**Python 示例:**
```python
import json

payload = {
    "event": "task.completed",
    "timestamp": "2025-11-28T18:04:10.123456Z",
    "data": {
        "task_id": 42,
        "task_title": "短剧片段 · 《养母胜过生母》",
        "user_id": 5156570084,
        "username": "test_user",
        "platform": "tiktok",
        "submission_link": "https://www.tiktok.com/@wu.roger7/video/7577349712...",
        "submitted_at": "2025-11-28T18:04:10.123456Z",
        "verified_at": "2025-11-28T18:04:10.123456Z",
        "node_power_earned": 10,
        "verification_status": "verified",
        "verification_details": {
            "matched": true,
            "match_rate": 100,
            "matched_keywords": ["test"]
        }
    }
}

# 生成 JSON 字符串
payload_str = json.dumps(payload, ensure_ascii=False)
```

**重要:** `ensure_ascii=False` 确保中文字符不被转义为 `\uXXXX` 格式

---

### 步骤 2: 获取签名密钥

**密钥来源:**
- 从 HTTP 请求头 `X-Webhook-Secret` 中获取
- 或从环境变量/配置中获取

**示例密钥:**
```
X2C_WEBHOOK_SECRET
```

**注意:** 密钥是**字面字符串**,不是环境变量名

---

### 步骤 3: 计算 HMAC-SHA256

**Python 实现:**
```python
import hmac
import hashlib

def generate_signature(payload_str: str, secret: str) -> str:
    """
    生成 HMAC-SHA256 签名
    
    Args:
        payload_str: JSON 字符串 (UTF-8 编码)
        secret: 签名密钥
    
    Returns:
        签名字符串,格式: sha256=<hex_digest>
    """
    signature = hmac.new(
        secret.encode('utf-8'),      # 密钥转为字节
        payload_str.encode('utf-8'),  # Payload 转为字节
        hashlib.sha256                # 使用 SHA256 算法
    ).hexdigest()                     # 转为十六进制字符串
    
    return f'sha256={signature}'
```

**JavaScript/Node.js 实现:**
```javascript
const crypto = require('crypto');

function generateSignature(payloadStr, secret) {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payloadStr, 'utf8');
    const signature = hmac.digest('hex');
    return `sha256=${signature}`;
}
```

**PHP 实现:**
```php
function generateSignature($payloadStr, $secret) {
    $signature = hash_hmac('sha256', $payloadStr, $secret);
    return 'sha256=' . $signature;
}
```

---

## 📤 HTTP 请求格式

### 请求头

```http
POST /functions/v1/x2c-webhook-receiver HTTP/1.1
Host: rxkcgquecleofqhyfchx.supabase.co
Content-Type: application/json
X-Webhook-Event: task.completed
X-Webhook-Timestamp: 1732813450
X-Webhook-Secret: X2C_WEBHOOK_SECRET
X-Webhook-Signature: sha256=abc123def456...
User-Agent: X2C-Bot-Webhook/1.0
```

**请求头说明:**

| 请求头 | 说明 | 示例 |
|--------|------|------|
| `Content-Type` | 固定为 `application/json` | `application/json` |
| `X-Webhook-Event` | 事件类型 | `task.completed` |
| `X-Webhook-Timestamp` | Unix 时间戳(秒) | `1732813450` |
| `X-Webhook-Secret` | 签名密钥(明文) | `X2C_WEBHOOK_SECRET` |
| `X-Webhook-Signature` | HMAC-SHA256 签名 | `sha256=abc123...` |
| `User-Agent` | 客户端标识 | `X2C-Bot-Webhook/1.0` |

---

### 请求体

**格式:** JSON  
**编码:** UTF-8  
**Content-Type:** `application/json`

**示例:**
```json
{
  "event": "task.completed",
  "timestamp": "2025-11-28T18:04:10.123456Z",
  "data": {
    "task_id": 42,
    "task_title": "短剧片段 · 《养母胜过生母》",
    "user_id": 5156570084,
    "username": "test_user",
    "platform": "tiktok",
    "submission_link": "https://www.tiktok.com/@wu.roger7/video/7577349712...",
    "submitted_at": "2025-11-28T18:04:10.123456Z",
    "verified_at": "2025-11-28T18:04:10.123456Z",
    "node_power_earned": 10,
    "verification_status": "verified",
    "verification_details": {
      "matched": true,
      "match_rate": 100,
      "matched_keywords": ["test"]
    }
  }
}
```

---

## ✅ 签名验证步骤 (接收方)

### 步骤 1: 获取原始请求体

**关键:** 必须使用**原始请求体字符串**,不能先解析 JSON 再序列化

**正确做法 (Node.js/Deno):**
```javascript
// ✅ 正确: 直接读取原始请求体
const rawBody = await request.text();

// 验证签名
const expectedSignature = generateSignature(rawBody, secret);
```

**错误做法:**
```javascript
// ❌ 错误: 先解析再序列化会导致格式差异
const jsonData = await request.json();
const rawBody = JSON.stringify(jsonData);  // 格式可能不一致!

// 验证签名 (会失败)
const expectedSignature = generateSignature(rawBody, secret);
```

---

### 步骤 2: 获取签名密钥

从请求头 `X-Webhook-Secret` 中获取:

```javascript
const secret = request.headers.get('X-Webhook-Secret');
```

---

### 步骤 3: 计算期望的签名

```javascript
function generateSignature(payloadStr, secret) {
    const hmac = crypto.createHmac('sha256', secret);
    hmac.update(payloadStr, 'utf8');
    const signature = hmac.digest('hex');
    return `sha256=${signature}`;
}

const expectedSignature = generateSignature(rawBody, secret);
```

---

### 步骤 4: 比较签名

```javascript
const receivedSignature = request.headers.get('X-Webhook-Signature');

// 使用时间安全的比较函数
function secureCompare(a, b) {
    if (a.length !== b.length) return false;
    
    let result = 0;
    for (let i = 0; i < a.length; i++) {
        result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }
    return result === 0;
}

if (!secureCompare(receivedSignature, expectedSignature)) {
    return new Response(
        JSON.stringify({ success: false, error: 'Invalid signature' }),
        { status: 401, headers: { 'Content-Type': 'application/json' } }
    );
}
```

---

## 🔍 完整示例 (Supabase Edge Function)

```javascript
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

serve(async (req) => {
    // 1. 读取原始请求体
    const rawBody = await req.text();
    
    // 2. 获取签名密钥
    const secret = req.headers.get('X-Webhook-Secret');
    if (!secret) {
        return new Response(
            JSON.stringify({ success: false, error: 'Missing secret' }),
            { status: 401 }
        );
    }
    
    // 3. 计算期望的签名
    const expectedSignature = await generateSignature(rawBody, secret);
    
    // 4. 获取接收到的签名
    const receivedSignature = req.headers.get('X-Webhook-Signature');
    
    // 5. 验证签名
    if (receivedSignature !== expectedSignature) {
        console.error('Signature mismatch:', {
            received: receivedSignature,
            expected: expectedSignature,
            rawBodyLength: rawBody.length,
            rawBodyPreview: rawBody.substring(0, 100)
        });
        
        return new Response(
            JSON.stringify({ success: false, error: 'Invalid signature' }),
            { status: 401 }
        );
    }
    
    // 6. 解析 JSON 数据
    const payload = JSON.parse(rawBody);
    
    // 7. 处理数据...
    const supabase = createClient(
        Deno.env.get('SUPABASE_URL'),
        Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
    );
    
    const { error } = await supabase
        .from('task_completions')
        .insert({
            task_id: payload.data.task_id,
            user_id: payload.data.user_id,
            platform: payload.data.platform,
            submission_link: payload.data.submission_link,
            node_power_earned: payload.data.node_power_earned,
            verification_status: payload.data.verification_status,
            submitted_at: payload.data.submitted_at,
            verified_at: payload.data.verified_at
        });
    
    if (error) {
        console.error('Database error:', error);
        return new Response(
            JSON.stringify({ success: false, error: error.message }),
            { status: 500 }
        );
    }
    
    return new Response(
        JSON.stringify({ 
            success: true, 
            message: 'Webhook received and processed successfully',
            received_at: new Date().toISOString()
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
});

async function generateSignature(payloadStr, secret) {
    const encoder = new TextEncoder();
    const keyData = encoder.encode(secret);
    const messageData = encoder.encode(payloadStr);
    
    const key = await crypto.subtle.importKey(
        'raw',
        keyData,
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
    );
    
    const signature = await crypto.subtle.sign('HMAC', key, messageData);
    const hashArray = Array.from(new Uint8Array(signature));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    
    return `sha256=${hashHex}`;
}
```

---

## ⚠️ 常见错误

### 1. JSON 序列化格式不一致

**问题:** 先解析 JSON 再序列化,导致格式差异

**解决:** 使用原始请求体字符串

```javascript
// ✅ 正确
const rawBody = await request.text();

// ❌ 错误
const data = await request.json();
const rawBody = JSON.stringify(data);
```

---

### 2. 字符编码问题

**问题:** 使用了错误的字符编码

**解决:** 统一使用 UTF-8

```python
# ✅ 正确
payload_str.encode('utf-8')

# ❌ 错误
payload_str.encode('ascii')  # 中文会报错
```

---

### 3. 签名格式错误

**问题:** 缺少 `sha256=` 前缀

**解决:** 确保签名格式为 `sha256=<hex_digest>`

```python
# ✅ 正确
return f'sha256={signature}'

# ❌ 错误
return signature  # 缺少前缀
```

---

### 4. 密钥不一致

**问题:** 发送方和接收方使用了不同的密钥

**解决:** 确保双方使用相同的密钥字符串

```
发送方: X2C_WEBHOOK_SECRET
接收方: X2C_WEBHOOK_SECRET  ✅

发送方: X2C_WEBHOOK_SECRET
接收方: some_other_secret   ❌
```

---

## 🧪 调试建议

### 1. 记录详细日志

```javascript
console.log('Signature verification:', {
    receivedSignature: receivedSignature,
    expectedSignature: expectedSignature,
    secret: secret,
    rawBodyLength: rawBody.length,
    rawBodyPreview: rawBody.substring(0, 200),
    match: receivedSignature === expectedSignature
});
```

---

### 2. 验证 Payload 字符串

```javascript
console.log('Raw body:', rawBody);
console.log('Raw body bytes:', new TextEncoder().encode(rawBody));
```

---

### 3. 验证密钥

```javascript
console.log('Secret:', secret);
console.log('Secret length:', secret.length);
console.log('Secret bytes:', new TextEncoder().encode(secret));
```

---

## 📞 联系支持

如果签名验证仍然失败,请提供:

1. **接收到的签名** (`X-Webhook-Signature`)
2. **原始请求体** (前 500 字符)
3. **使用的密钥** (`X-Webhook-Secret`)
4. **计算出的期望签名**
5. **详细的错误日志**

---

**文档版本:** 1.0  
**最后更新:** 2025-11-28
