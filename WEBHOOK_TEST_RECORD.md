# X2C Webhook 测试记录

## 📋 测试概述

**测试时间:** 2025-11-28 04:12:44 UTC  
**测试目的:** 验证 X2C Bot Webhook 回调功能与 Supabase 集成  
**测试状态:** ✅ 成功

---

## 🔗 Webhook 端点信息

**Supabase Webhook 接收端点:**
```
https://rxkcgquecleofqhyfchx.supabase.co/functions/v1/x2c-webhook-receiver
```

**认证方式:** HMAC-SHA256 签名验证  
**签名密钥:** `X2C_WEBHOOK_SECRET`

---

## 📤 请求详情

### HTTP 请求头

```http
POST /functions/v1/x2c-webhook-receiver HTTP/1.1
Host: rxkcgquecleofqhyfchx.supabase.co
Content-Type: application/json
X-Webhook-Event: task.completed
X-Webhook-Timestamp: 1764303164
X-Webhook-Secret: X2C_WEBHOOK_SECRET
X-Webhook-Signature: sha256=57a911e4de97985cdfe10987ab7f234a3dd586509365d44053faa4a71bc2f305
User-Agent: X2C-Bot-Webhook/1.0
```

### 请求体 (JSON Payload)

```json
{
  "event": "task.completed",
  "timestamp": "2025-11-28T04:12:44.240437Z",
  "data": {
    "task_id": 38,
    "task_title": "短剧片段 · 《ruthless-kindness》",
    "user_id": 5156570084,
    "username": "test_user",
    "platform": "tiktok",
    "submission_link": "https://www.tiktok.com/@wu.roger7/video/7577587517487107341",
    "submitted_at": "2025-11-28T04:12:44.240445Z",
    "verified_at": "2025-11-28T04:12:44.240447Z",
    "node_power_earned": 10,
    "verification_status": "verified",
    "verification_details": {
      "matched": true,
      "match_rate": 100,
      "matched_keywords": [
        "test"
      ]
    }
  }
}
```

**Payload 大小:** 537 字节

---

## 🔐 签名计算详情

### 签名算法
```
HMAC-SHA256(secret, payload_string)
```

### 签名输入
- **Secret:** `X2C_WEBHOOK_SECRET`
- **Payload:** 完整的 JSON 字符串 (537 字节)
- **编码:** UTF-8

### 签名输出
```
sha256=57a911e4de97985cdfe10987ab7f234a3dd586509365d44053faa4a71bc2f305
```

### Python 签名代码示例
```python
import hmac
import hashlib
import json

secret = "X2C_WEBHOOK_SECRET"
payload = {
  "event": "task.completed",
  "timestamp": "2025-11-28T04:12:44.240437Z",
  "data": { ... }
}

payload_str = json.dumps(payload, ensure_ascii=False)
signature = 'sha256=' + hmac.new(
    secret.encode(),
    payload_str.encode(),
    hashlib.sha256
).hexdigest()
```

---

## 📥 响应详情

### HTTP 响应状态
```
HTTP/1.1 200 OK
```

### 响应头
```http
Date: Fri, 28 Nov 2025 04:12:44 GMT
Content-Type: application/json
Content-Length: 120
Server: cloudflare
Access-Control-Allow-Origin: *
sb-project-ref: rxkcgquecleofqhyfchx
x-sb-edge-region: us-east-1
x-served-by: supabase-edge-runtime
```

### 响应体
```json
{
  "success": true,
  "message": "Webhook received and processed successfully",
  "received_at": "2025-11-28T04:12:44.783Z"
}
```

---

## 📊 测试数据集

### 任务信息
- **Task ID:** 38
- **任务标题:** 短剧片段 · 《ruthless-kindness》
- **奖励:** 10 Node Power
- **平台:** TikTok

### 用户信息
- **User ID:** 5156570084
- **Username:** test_user

### 提交信息
- **提交链接:** https://www.tiktok.com/@wu.roger7/video/7577587517487107341
- **提交时间:** 2025-11-28T04:12:44.240445Z
- **验证时间:** 2025-11-28T04:12:44.240447Z
- **验证状态:** verified

### 验证详情
- **匹配状态:** true
- **匹配率:** 100%
- **匹配关键词:** ["test"]

---

## ✅ 测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| Webhook 发送 | ✅ 成功 | HTTP 请求成功发送 |
| 签名验证 | ✅ 通过 | HMAC-SHA256 签名正确 |
| Supabase 接收 | ✅ 成功 | 返回 HTTP 200 |
| 数据格式 | ✅ 正确 | JSON payload 符合规范 |
| 响应时间 | ✅ 正常 | < 1 秒 |

---

## 🔍 验证建议

### Supabase 端验证步骤

1. **检查 Edge Function 日志**
   - 查看 `x2c-webhook-receiver` 函数的执行日志
   - 确认接收到的 payload 内容
   - 验证签名计算过程

2. **检查数据库记录**
   - 表名: `task_completions` (或您定义的表名)
   - 查询条件: `user_id = 5156570084 AND task_id = 38`
   - 预期字段:
     - task_id: 38
     - user_id: 5156570084
     - platform: "tiktok"
     - submission_link: "https://www.tiktok.com/@wu.roger7/video/7577587517487107341"
     - node_power_earned: 10
     - verification_status: "verified"

3. **验证签名计算**
   - 使用相同的 secret: `X2C_WEBHOOK_SECRET`
   - 使用相同的 payload 字符串
   - 计算结果应为: `sha256=57a911e4de97985cdfe10987ab7f234a3dd586509365d44053faa4a71bc2f305`

---

## 📝 注意事项

1. **签名验证要点:**
   - 必须使用原始请求体字符串计算签名
   - 不能先解析 JSON 再序列化,会导致格式差异
   - 使用 `await request.text()` 获取原始请求体

2. **时间戳验证:**
   - 建议验证时间戳在 5 分钟内
   - 防止重放攻击

3. **错误处理:**
   - 签名不匹配应返回 401
   - 数据格式错误应返回 400
   - 服务器错误应返回 500

---

## 🔧 调试工具

**测试脚本位置:**
```
/home/ubuntu/telegram-bot-dramarelay/debug_webhook_request.py
```

**运行方式:**
```bash
cd /home/ubuntu/telegram-bot-dramarelay
source venv/bin/activate
python debug_webhook_request.py
```

---

## 📞 联系信息

如有问题,请提供:
1. Supabase Edge Function 日志
2. 数据库查询结果
3. 签名验证过程的详细日志

---

**文档生成时间:** 2025-11-28  
**文档版本:** 1.0
