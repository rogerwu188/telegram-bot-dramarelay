# X2C Drama Relay - Webhook 回调集成指南

## 📋 概述

本文档面向需要集成 X2C Drama Relay Bot 的外部系统开发者,介绍如何接收和处理任务完成的 Webhook 回调通知。

## 🎯 使用场景

当您的系统通过 API 向 X2C Bot 分发任务后,您可能需要知道:
- 哪些任务已经被用户完成
- 用户提交的社交媒体链接
- 任务验证的详细结果
- 用户获得的算力奖励

通过配置 Webhook 回调,您的系统可以实时接收这些信息,无需轮询查询。

## 🔧 集成步骤

### 步骤 1: 准备接收端点

在您的服务器上创建一个 HTTP POST 端点用于接收 Webhook 回调:

```
POST https://your-domain.com/api/webhooks/x2c-tasks
```

**要求:**
- 必须支持 HTTPS (生产环境)
- 必须返回 HTTP 200-299 状态码表示成功接收
- 建议在 30 秒内返回响应
- 建议实现幂等性处理 (相同任务可能重复通知)

### 步骤 2: 创建任务时配置回调

使用 API 创建任务时,添加 `callback_url` 和可选的 `callback_secret` 参数:

```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "title": "短剧任务 #001",
    "description": "上传短剧片段到 TikTok",
    "video_url": "https://example.com/video.mp4",
    "node_power_reward": 10,
    "callback_url": "https://your-domain.com/api/webhooks/x2c-tasks",
    "callback_secret": "your_secret_key_for_verification"
  }'
```

**参数说明:**
- `callback_url` (必填): 您的接收端点 URL
- `callback_secret` (可选): 用于签名验证的密钥,建议使用 32 位以上随机字符串

### 步骤 3: 实现接收逻辑

#### 请求格式

**请求头:**
```
Content-Type: application/json
X-Webhook-Event: task.completed
X-Webhook-Timestamp: 1732704600
X-Webhook-Secret: your_secret_key_for_verification
X-Webhook-Signature: sha256=abc123def456...
User-Agent: X2C-Bot-Webhook/1.0
```

**请求体:**
```json
{
  "event": "task.completed",
  "timestamp": "2025-11-27T10:30:00Z",
  "data": {
    "task_id": 123,
    "task_title": "短剧任务 #001",
    "user_id": 987654321,
    "username": "user123",
    "platform": "tiktok",
    "submission_link": "https://www.tiktok.com/@user123/video/7234567890",
    "submitted_at": "2025-11-27T10:25:00Z",
    "verified_at": "2025-11-27T10:30:00Z",
    "node_power_earned": 10,
    "verification_status": "verified",
    "verification_details": {
      "matched": true,
      "match_rate": 95,
      "matched_keywords": ["爱情", "复仇", "豪门"]
    }
  }
}
```

#### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `event` | string | 事件类型,目前固定为 `task.completed` |
| `timestamp` | string | 事件发生时间 (ISO 8601 格式,UTC 时区) |
| `data.task_id` | integer | 任务 ID |
| `data.task_title` | string | 任务标题 |
| `data.user_id` | integer | Telegram 用户 ID |
| `data.username` | string | Telegram 用户名 |
| `data.platform` | string | 提交平台: `tiktok`, `youtube`, `instagram` |
| `data.submission_link` | string | 用户提交的社交媒体链接 |
| `data.submitted_at` | string | 提交时间 (ISO 8601 格式) |
| `data.verified_at` | string | 验证通过时间 (ISO 8601 格式) |
| `data.node_power_earned` | integer | 用户获得的算力值 |
| `data.verification_status` | string | 验证状态,固定为 `verified` |
| `data.verification_details.matched` | boolean | 关键词是否匹配 |
| `data.verification_details.match_rate` | integer | 匹配率 (0-100) |
| `data.verification_details.matched_keywords` | array | 匹配到的关键词列表 |

### 步骤 4: 实现签名验证 (推荐)

为了确保 Webhook 请求来自 X2C Bot 而非恶意攻击者,建议验证请求签名。

#### Python 示例

```python
import hmac
import hashlib
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

def verify_signature(payload_str: str, signature: str, secret: str) -> bool:
    """验证 HMAC-SHA256 签名"""
    expected_signature = 'sha256=' + hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

@app.route('/api/webhooks/x2c-tasks', methods=['POST'])
def receive_webhook():
    # 获取请求数据
    payload = request.get_json()
    payload_str = json.dumps(payload, ensure_ascii=False)
    
    # 获取签名和密钥
    signature = request.headers.get('X-Webhook-Signature')
    secret = request.headers.get('X-Webhook-Secret')
    
    # 验证签名
    if not verify_signature(payload_str, signature, secret):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # 处理任务完成事件
    data = payload.get('data', {})
    task_id = data.get('task_id')
    user_id = data.get('user_id')
    submission_link = data.get('submission_link')
    
    # TODO: 在这里实现您的业务逻辑
    # 例如: 更新数据库、发送通知、结算奖励等
    
    print(f"✅ 任务 {task_id} 已完成,用户 {user_id} 提交链接: {submission_link}")
    
    # 返回成功响应
    return jsonify({
        'success': True,
        'message': 'Webhook received successfully'
    }), 200
```

#### Node.js 示例

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.json());

function verifySignature(payloadStr, signature, secret) {
  const expectedSignature = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(payloadStr)
    .digest('hex');
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

app.post('/api/webhooks/x2c-tasks', (req, res) => {
  const payload = req.body;
  const payloadStr = JSON.stringify(payload);
  
  const signature = req.headers['x-webhook-signature'];
  const secret = req.headers['x-webhook-secret'];
  
  // 验证签名
  if (!verifySignature(payloadStr, signature, secret)) {
    return res.status(401).json({ error: 'Invalid signature' });
  }
  
  // 处理任务完成事件
  const { task_id, user_id, submission_link } = payload.data;
  
  // TODO: 实现您的业务逻辑
  
  console.log(`✅ 任务 ${task_id} 已完成,用户 ${user_id} 提交链接: ${submission_link}`);
  
  // 返回成功响应
  res.status(200).json({
    success: true,
    message: 'Webhook received successfully'
  });
});

app.listen(3000, () => {
  console.log('Webhook receiver listening on port 3000');
});
```

#### PHP 示例

```php
<?php
function verifySignature($payloadStr, $signature, $secret) {
    $expectedSignature = 'sha256=' . hash_hmac('sha256', $payloadStr, $secret);
    return hash_equals($signature, $expectedSignature);
}

// 获取请求数据
$payloadStr = file_get_contents('php://input');
$payload = json_decode($payloadStr, true);

// 获取请求头
$signature = $_SERVER['HTTP_X_WEBHOOK_SIGNATURE'] ?? '';
$secret = $_SERVER['HTTP_X_WEBHOOK_SECRET'] ?? '';

// 验证签名
if (!verifySignature($payloadStr, $signature, $secret)) {
    http_response_code(401);
    echo json_encode(['error' => 'Invalid signature']);
    exit;
}

// 处理任务完成事件
$data = $payload['data'];
$taskId = $data['task_id'];
$userId = $data['user_id'];
$submissionLink = $data['submission_link'];

// TODO: 实现您的业务逻辑

error_log("✅ 任务 {$taskId} 已完成,用户 {$userId} 提交链接: {$submissionLink}");

// 返回成功响应
http_response_code(200);
echo json_encode([
    'success' => true,
    'message' => 'Webhook received successfully'
]);
?>
```

## 🔄 重试机制

如果您的接收端点返回非 2xx 状态码或请求超时,X2C Bot 会自动重试:

| 尝试次数 | 延迟时间 |
|---------|---------|
| 第 1 次 | 立即 |
| 第 2 次 | 5 秒后 |
| 第 3 次 | 25 秒后 |
| 第 4 次 | 125 秒后 |

**注意事项:**
- 最多重试 3 次 (共 4 次尝试)
- 使用指数退避策略避免过载
- 重试失败后任务状态会标记为 `failed`
- 建议实现幂等性处理,避免重复处理同一任务

## 🔐 安全建议

1. **使用 HTTPS**: 生产环境必须使用 HTTPS 保护数据传输
2. **验证签名**: 始终验证 `X-Webhook-Signature` 确保请求来源可信
3. **保护密钥**: 将 `callback_secret` 存储在环境变量中,不要硬编码
4. **IP 白名单**: 如果可能,限制只接受来自 Railway 平台的 IP
5. **请求日志**: 记录所有 Webhook 请求用于审计和故障排查
6. **超时处理**: 设置合理的超时时间,避免长时间阻塞

## 📊 监控和调试

### 查询回调状态

使用 API 查询任务的回调状态:

```bash
curl -X GET "https://web-production-b95cb.up.railway.app/api/tasks/123" \
  -H "X-API-Key: your_api_key"
```

响应示例:
```json
{
  "success": true,
  "data": {
    "task_id": 123,
    "title": "短剧任务 #001",
    "callback_url": "https://your-domain.com/api/webhooks/x2c-tasks",
    "callback_status": "success",
    "callback_retry_count": 0,
    "callback_last_attempt": "2025-11-27T10:30:05Z"
  }
}
```

### 回调状态说明

| 状态 | 说明 |
|------|------|
| `pending` | 待回调 (任务尚未完成或回调未发送) |
| `success` | 回调成功 (接收端返回 2xx 状态码) |
| `failed` | 回调失败 (重试 3 次后仍失败) |

### 测试 Webhook

在开发阶段,您可以使用以下工具测试 Webhook:

1. **Webhook.site**: https://webhook.site - 在线查看请求详情
2. **RequestBin**: https://requestbin.com - 收集和检查 HTTP 请求
3. **ngrok**: https://ngrok.com - 将本地服务暴露到公网进行测试

示例 (使用 ngrok):
```bash
# 启动本地服务
python your_webhook_receiver.py

# 在另一个终端启动 ngrok
ngrok http 5000

# 使用 ngrok 提供的 URL 作为 callback_url
# 例如: https://abc123.ngrok.io/api/webhooks/x2c-tasks
```

## 🐛 常见问题

### Q1: 为什么没有收到 Webhook 回调?

**可能原因:**
1. 任务创建时未配置 `callback_url`
2. 接收端点 URL 错误或无法访问
3. 接收端返回了非 2xx 状态码
4. 请求超时 (超过 30 秒)

**解决方法:**
- 检查任务配置: `GET /api/tasks/{task_id}`
- 测试接收端点是否可访问
- 查看接收端日志
- 检查防火墙和网络配置

### Q2: 如何处理重复的 Webhook 通知?

**建议实现幂等性处理:**
```python
# 使用 task_id + user_id 作为唯一标识
unique_key = f"{task_id}_{user_id}"

# 检查是否已处理
if redis.exists(f"processed_webhook:{unique_key}"):
    return {'success': True, 'message': 'Already processed'}

# 处理业务逻辑
process_task_completion(task_id, user_id, submission_link)

# 标记为已处理 (设置 24 小时过期)
redis.setex(f"processed_webhook:{unique_key}", 86400, '1')
```

### Q3: 签名验证失败怎么办?

**检查清单:**
1. 确认发送端和接收端使用相同的 `callback_secret`
2. 确认签名算法为 HMAC-SHA256
3. 确认 payload 字符串完全一致 (包括空格、换行、字符编码)
4. 使用 `json.dumps(payload, ensure_ascii=False)` 生成 payload 字符串

### Q4: 如何处理大量并发的 Webhook?

**建议使用消息队列:**
```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def process_webhook(payload):
    # 异步处理 Webhook 数据
    task_id = payload['data']['task_id']
    # ... 业务逻辑
    
@app.route('/api/webhooks/x2c-tasks', methods=['POST'])
def receive_webhook():
    payload = request.get_json()
    
    # 快速返回 200,异步处理
    process_webhook.delay(payload)
    
    return jsonify({'success': True}), 200
```

## 📚 相关文档

- [X2C API 完整文档](./X2C_API_Documentation.md)
- [Webhook 测试指南](./WEBHOOK_TESTING.md)
- [Bot 部署指南](./DEPLOYMENT_GUIDE.md)

## 🆘 技术支持

如果您在集成过程中遇到问题:
1. 查看 [常见问题](#常见问题) 部分
2. 参考 [测试指南](./WEBHOOK_TESTING.md)
3. 联系技术支持团队

---

**版本:** v1.0.0  
**更新日期:** 2025-11-27  
**维护者:** X2C Drama Relay Team
