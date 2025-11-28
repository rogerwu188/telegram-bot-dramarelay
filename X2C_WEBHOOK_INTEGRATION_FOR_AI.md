# X2C Drama Relay - Webhook 回调集成开发文档

> **目标读者:** 外部应用开发者 / AI 开发助手  
> **文档版本:** v1.0.0  
> **最后更新:** 2025-11-27  
> **API 基础 URL:** https://web-production-b95cb.up.railway.app

---

## 📋 文档概述

本文档提供 X2C Drama Relay Bot Webhook 回调功能的完整技术规范,帮助外部应用实现任务完成通知的接收和处理。

**核心功能:** 当 Telegram Bot 用户完成短剧推广任务后,系统会自动向外部应用发送 HTTP POST 回调通知,包含任务详情、用户信息、提交链接和验证结果。

---

## 🎯 集成目标

实现以下功能:
1. 创建 HTTP POST 接收端点接收 Webhook 回调
2. 验证请求签名确保安全性
3. 解析回调数据并提取关键信息
4. 实现业务逻辑 (更新数据库、发送通知、结算奖励等)
5. 返回正确的 HTTP 响应

---

## 🔧 技术规范

### 1. 接收端点要求

**必须满足:**
- 协议: HTTPS (生产环境) 或 HTTP (测试环境)
- 方法: POST
- 响应时间: 建议 < 30 秒
- 成功状态码: 200-299 (任何 2xx 状态码都视为成功)
- 内容类型: application/json

**推荐实现:**
- 幂等性处理 (防止重复通知)
- 异步处理耗时操作
- 完整的错误日志记录

### 2. 请求格式

#### 请求头 (Headers)

```
POST /your-webhook-endpoint HTTP/1.1
Host: your-domain.com
Content-Type: application/json
X-Webhook-Event: task.completed
X-Webhook-Timestamp: 1732704600
X-Webhook-Secret: your_secret_key_2024
X-Webhook-Signature: sha256=abc123def456789...
User-Agent: X2C-Bot-Webhook/1.0
```

**字段说明:**

| 字段 | 类型 | 说明 |
|------|------|------|
| `Content-Type` | string | 固定为 `application/json` |
| `X-Webhook-Event` | string | 事件类型,目前固定为 `task.completed` |
| `X-Webhook-Timestamp` | integer | Unix 时间戳 (秒) |
| `X-Webhook-Secret` | string | 创建任务时配置的密钥 |
| `X-Webhook-Signature` | string | HMAC-SHA256 签名,格式: `sha256={hex}` |
| `User-Agent` | string | 固定为 `X2C-Bot-Webhook/1.0` |

#### 请求体 (Body)

```json
{
  "event": "task.completed",
  "timestamp": "2025-11-27T10:30:00Z",
  "data": {
    "task_id": 123,
    "task_title": "短剧任务 - 霸道总裁爱上我",
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
      "matched_keywords": ["霸道总裁", "爱情", "豪门"]
    }
  }
}
```

**字段说明:**

| 字段路径 | 类型 | 必填 | 说明 |
|---------|------|------|------|
| `event` | string | ✅ | 事件类型,固定为 `task.completed` |
| `timestamp` | string | ✅ | 事件发生时间 (ISO 8601 格式,UTC 时区) |
| `data.task_id` | integer | ✅ | 任务 ID |
| `data.task_title` | string | ✅ | 任务标题 |
| `data.user_id` | integer | ✅ | Telegram 用户 ID |
| `data.username` | string | ✅ | Telegram 用户名 |
| `data.platform` | string | ✅ | 提交平台: `tiktok`, `youtube`, `instagram` |
| `data.submission_link` | string | ✅ | 用户提交的社交媒体链接 |
| `data.submitted_at` | string | ✅ | 提交时间 (ISO 8601) |
| `data.verified_at` | string | ✅ | 验证通过时间 (ISO 8601) |
| `data.node_power_earned` | integer | ✅ | 用户获得的算力值 |
| `data.verification_status` | string | ✅ | 验证状态,固定为 `verified` |
| `data.verification_details.matched` | boolean | ✅ | 关键词是否匹配 |
| `data.verification_details.match_rate` | integer | ✅ | 匹配率 (0-100) |
| `data.verification_details.matched_keywords` | array | ✅ | 匹配到的关键词列表 |

### 3. 响应格式

**成功响应 (推荐):**

```json
{
  "success": true,
  "message": "Webhook received successfully"
}
```

**HTTP 状态码:** 200 或任何 2xx 状态码

**失败响应 (可选):**

```json
{
  "success": false,
  "error": "Invalid signature"
}
```

**HTTP 状态码:** 401 (签名错误) 或 500 (服务器错误)

---

## 🔐 签名验证

### 验证算法

使用 HMAC-SHA256 算法验证请求签名:

1. 获取原始请求体 (JSON 字符串)
2. 使用 `callback_secret` 作为密钥
3. 计算 HMAC-SHA256 哈希值
4. 转换为十六进制字符串
5. 添加 `sha256=` 前缀
6. 与 `X-Webhook-Signature` 对比

### 验证代码示例

#### Python

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload_str: str, signature: str, secret: str) -> bool:
    """
    验证 Webhook 请求签名
    
    Args:
        payload_str: 原始请求体 JSON 字符串
        signature: X-Webhook-Signature 头的值
        secret: X-Webhook-Secret 头的值 (创建任务时配置的密钥)
    
    Returns:
        bool: 签名是否有效
    """
    # 计算期望的签名
    expected_signature = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 使用时间安全的比较函数
    return hmac.compare_digest(signature, expected_signature)

# 使用示例
payload_str = request.get_data(as_text=True)  # 原始请求体
signature = request.headers.get('X-Webhook-Signature')
secret = request.headers.get('X-Webhook-Secret')

if verify_webhook_signature(payload_str, signature, secret):
    print("✅ 签名验证成功")
else:
    print("❌ 签名验证失败")
```

#### Node.js

```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payloadStr, signature, secret) {
  /**
   * 验证 Webhook 请求签名
   * 
   * @param {string} payloadStr - 原始请求体 JSON 字符串
   * @param {string} signature - X-Webhook-Signature 头的值
   * @param {string} secret - X-Webhook-Secret 头的值
   * @returns {boolean} 签名是否有效
   */
  
  // 计算期望的签名
  const expectedSignature = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(payloadStr)
    .digest('hex');
  
  // 使用时间安全的比较函数
  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature)
    );
  } catch (e) {
    return false;
  }
}

// 使用示例
const payloadStr = JSON.stringify(req.body);
const signature = req.headers['x-webhook-signature'];
const secret = req.headers['x-webhook-secret'];

if (verifyWebhookSignature(payloadStr, signature, secret)) {
  console.log('✅ 签名验证成功');
} else {
  console.log('❌ 签名验证失败');
}
```

#### PHP

```php
<?php
function verifyWebhookSignature($payloadStr, $signature, $secret) {
    /**
     * 验证 Webhook 请求签名
     * 
     * @param string $payloadStr 原始请求体 JSON 字符串
     * @param string $signature X-Webhook-Signature 头的值
     * @param string $secret X-Webhook-Secret 头的值
     * @return bool 签名是否有效
     */
    
    // 计算期望的签名
    $expectedSignature = 'sha256=' . hash_hmac('sha256', $payloadStr, $secret);
    
    // 使用时间安全的比较函数
    return hash_equals($signature, $expectedSignature);
}

// 使用示例
$payloadStr = file_get_contents('php://input');
$signature = $_SERVER['HTTP_X_WEBHOOK_SIGNATURE'] ?? '';
$secret = $_SERVER['HTTP_X_WEBHOOK_SECRET'] ?? '';

if (verifyWebhookSignature($payloadStr, $signature, $secret)) {
    error_log('✅ 签名验证成功');
} else {
    error_log('❌ 签名验证失败');
}
?>
```

---

## 💻 完整实现示例

### Python (Flask)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_signature(payload_str: str, signature: str, secret: str) -> bool:
    """验证 HMAC-SHA256 签名"""
    expected_sig = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_sig)

@app.route('/api/webhooks/x2c-tasks', methods=['POST'])
def receive_x2c_webhook():
    """接收 X2C Bot Webhook 回调"""
    
    try:
        # 1. 获取原始请求数据
        payload_str = request.get_data(as_text=True)
        payload = json.loads(payload_str)
        
        # 2. 获取请求头
        signature = request.headers.get('X-Webhook-Signature')
        secret = request.headers.get('X-Webhook-Secret')
        event_type = request.headers.get('X-Webhook-Event')
        timestamp = request.headers.get('X-Webhook-Timestamp')
        
        logger.info(f"收到 Webhook 回调: event={event_type}, timestamp={timestamp}")
        
        # 3. 验证签名 (强烈推荐)
        if not signature or not secret:
            logger.warning("缺少签名或密钥")
            return jsonify({'error': 'Missing signature or secret'}), 401
        
        if not verify_signature(payload_str, signature, secret):
            logger.error("签名验证失败")
            return jsonify({'error': 'Invalid signature'}), 401
        
        logger.info("✅ 签名验证成功")
        
        # 4. 解析数据
        event = payload.get('event')
        data = payload.get('data', {})
        
        task_id = data.get('task_id')
        task_title = data.get('task_title')
        user_id = data.get('user_id')
        username = data.get('username')
        platform = data.get('platform')
        submission_link = data.get('submission_link')
        submitted_at = data.get('submitted_at')
        verified_at = data.get('verified_at')
        node_power_earned = data.get('node_power_earned')
        verification_status = data.get('verification_status')
        verification_details = data.get('verification_details', {})
        
        # 5. 记录日志
        logger.info(f"任务完成通知:")
        logger.info(f"  - 任务 ID: {task_id}")
        logger.info(f"  - 任务标题: {task_title}")
        logger.info(f"  - 用户 ID: {user_id}")
        logger.info(f"  - 用户名: {username}")
        logger.info(f"  - 平台: {platform}")
        logger.info(f"  - 提交链接: {submission_link}")
        logger.info(f"  - 算力奖励: {node_power_earned}")
        logger.info(f"  - 验证状态: {verification_status}")
        logger.info(f"  - 匹配率: {verification_details.get('match_rate')}%")
        logger.info(f"  - 匹配关键词: {verification_details.get('matched_keywords')}")
        
        # 6. 实现业务逻辑
        # TODO: 在这里添加您的业务逻辑
        
        # 示例 1: 更新数据库
        # update_task_status(task_id, 'completed', submission_link)
        # update_user_node_power(user_id, node_power_earned)
        
        # 示例 2: 发送通知
        # send_notification(user_id, f"任务完成!获得 {node_power_earned} 算力")
        
        # 示例 3: 结算奖励
        # settle_rewards(user_id, node_power_earned)
        
        # 示例 4: 触发其他业务流程
        # trigger_reward_distribution(user_id, task_id)
        
        logger.info("✅ Webhook 处理成功")
        
        # 7. 返回成功响应
        return jsonify({
            'success': True,
            'message': 'Webhook received and processed successfully',
            'received_at': datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析错误: {e}")
        return jsonify({'error': 'Invalid JSON'}), 400
    
    except Exception as e:
        logger.error(f"处理 Webhook 时发生错误: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({'status': 'ok', 'service': 'x2c-webhook-receiver'}), 200

if __name__ == '__main__':
    # 生产环境建议使用 gunicorn 或 uwsgi
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### Node.js (Express)

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();

// 重要: 使用 express.text() 获取原始请求体用于签名验证
app.use(express.text({ type: 'application/json' }));

function verifySignature(payloadStr, signature, secret) {
  const expectedSig = 'sha256=' + crypto
    .createHmac('sha256', secret)
    .update(payloadStr)
    .digest('hex');
  
  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSig)
    );
  } catch (e) {
    return false;
  }
}

app.post('/api/webhooks/x2c-tasks', (req, res) => {
  try {
    // 1. 获取原始请求数据
    const payloadStr = req.body;
    const payload = JSON.parse(payloadStr);
    
    // 2. 获取请求头
    const signature = req.headers['x-webhook-signature'];
    const secret = req.headers['x-webhook-secret'];
    const eventType = req.headers['x-webhook-event'];
    const timestamp = req.headers['x-webhook-timestamp'];
    
    console.log(`收到 Webhook 回调: event=${eventType}, timestamp=${timestamp}`);
    
    // 3. 验证签名
    if (!signature || !secret) {
      console.warn('缺少签名或密钥');
      return res.status(401).json({ error: 'Missing signature or secret' });
    }
    
    if (!verifySignature(payloadStr, signature, secret)) {
      console.error('签名验证失败');
      return res.status(401).json({ error: 'Invalid signature' });
    }
    
    console.log('✅ 签名验证成功');
    
    // 4. 解析数据
    const { event, data } = payload;
    const {
      task_id,
      task_title,
      user_id,
      username,
      platform,
      submission_link,
      submitted_at,
      verified_at,
      node_power_earned,
      verification_status,
      verification_details
    } = data;
    
    // 5. 记录日志
    console.log('任务完成通知:');
    console.log(`  - 任务 ID: ${task_id}`);
    console.log(`  - 任务标题: ${task_title}`);
    console.log(`  - 用户 ID: ${user_id}`);
    console.log(`  - 用户名: ${username}`);
    console.log(`  - 平台: ${platform}`);
    console.log(`  - 提交链接: ${submission_link}`);
    console.log(`  - 算力奖励: ${node_power_earned}`);
    console.log(`  - 验证状态: ${verification_status}`);
    console.log(`  - 匹配率: ${verification_details.match_rate}%`);
    console.log(`  - 匹配关键词: ${verification_details.matched_keywords}`);
    
    // 6. 实现业务逻辑
    // TODO: 在这里添加您的业务逻辑
    
    // 示例: 异步处理
    // processTaskCompletion(task_id, user_id, submission_link, node_power_earned)
    //   .catch(err => console.error('处理任务失败:', err));
    
    console.log('✅ Webhook 处理成功');
    
    // 7. 返回成功响应
    res.status(200).json({
      success: true,
      message: 'Webhook received and processed successfully',
      received_at: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('处理 Webhook 时发生错误:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'x2c-webhook-receiver' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`X2C Webhook receiver listening on port ${PORT}`);
});
```

### PHP

```php
<?php
// x2c_webhook_receiver.php

// 设置错误日志
ini_set('log_errors', 1);
ini_set('error_log', '/var/log/x2c_webhook.log');

function verifySignature($payloadStr, $signature, $secret) {
    $expectedSig = 'sha256=' . hash_hmac('sha256', $payloadStr, $secret);
    return hash_equals($signature, $expectedSig);
}

function logInfo($message) {
    error_log("[INFO] " . $message);
}

function logError($message) {
    error_log("[ERROR] " . $message);
}

try {
    // 1. 获取原始请求数据
    $payloadStr = file_get_contents('php://input');
    $payload = json_decode($payloadStr, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid JSON']);
        exit;
    }
    
    // 2. 获取请求头
    $signature = $_SERVER['HTTP_X_WEBHOOK_SIGNATURE'] ?? '';
    $secret = $_SERVER['HTTP_X_WEBHOOK_SECRET'] ?? '';
    $eventType = $_SERVER['HTTP_X_WEBHOOK_EVENT'] ?? '';
    $timestamp = $_SERVER['HTTP_X_WEBHOOK_TIMESTAMP'] ?? '';
    
    logInfo("收到 Webhook 回调: event={$eventType}, timestamp={$timestamp}");
    
    // 3. 验证签名
    if (empty($signature) || empty($secret)) {
        logError("缺少签名或密钥");
        http_response_code(401);
        echo json_encode(['error' => 'Missing signature or secret']);
        exit;
    }
    
    if (!verifySignature($payloadStr, $signature, $secret)) {
        logError("签名验证失败");
        http_response_code(401);
        echo json_encode(['error' => 'Invalid signature']);
        exit;
    }
    
    logInfo("✅ 签名验证成功");
    
    // 4. 解析数据
    $event = $payload['event'] ?? '';
    $data = $payload['data'] ?? [];
    
    $taskId = $data['task_id'] ?? 0;
    $taskTitle = $data['task_title'] ?? '';
    $userId = $data['user_id'] ?? 0;
    $username = $data['username'] ?? '';
    $platform = $data['platform'] ?? '';
    $submissionLink = $data['submission_link'] ?? '';
    $submittedAt = $data['submitted_at'] ?? '';
    $verifiedAt = $data['verified_at'] ?? '';
    $nodePowerEarned = $data['node_power_earned'] ?? 0;
    $verificationStatus = $data['verification_status'] ?? '';
    $verificationDetails = $data['verification_details'] ?? [];
    
    // 5. 记录日志
    logInfo("任务完成通知:");
    logInfo("  - 任务 ID: {$taskId}");
    logInfo("  - 任务标题: {$taskTitle}");
    logInfo("  - 用户 ID: {$userId}");
    logInfo("  - 用户名: {$username}");
    logInfo("  - 平台: {$platform}");
    logInfo("  - 提交链接: {$submissionLink}");
    logInfo("  - 算力奖励: {$nodePowerEarned}");
    logInfo("  - 验证状态: {$verificationStatus}");
    
    // 6. 实现业务逻辑
    // TODO: 在这里添加您的业务逻辑
    
    // 示例: 更新数据库
    // updateTaskStatus($taskId, 'completed', $submissionLink);
    // updateUserNodePower($userId, $nodePowerEarned);
    
    // 示例: 发送通知
    // sendNotification($userId, "任务完成!获得 {$nodePowerEarned} 算力");
    
    logInfo("✅ Webhook 处理成功");
    
    // 7. 返回成功响应
    http_response_code(200);
    header('Content-Type: application/json');
    echo json_encode([
        'success' => true,
        'message' => 'Webhook received and processed successfully',
        'received_at' => gmdate('Y-m-d\TH:i:s\Z')
    ]);
    
} catch (Exception $e) {
    logError("处理 Webhook 时发生错误: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['error' => 'Internal server error']);
}
?>
```

---

## 🔄 重试机制

### 重试策略

如果您的接收端返回非 2xx 状态码或请求超时 (>30秒),X2C Bot 会自动重试:

| 尝试次数 | 延迟时间 | 说明 |
|---------|---------|------|
| 第 1 次 | 立即 | 初次尝试 |
| 第 2 次 | 5 秒后 | 首次重试 |
| 第 3 次 | 25 秒后 | 第二次重试 |
| 第 4 次 | 125 秒后 | 最后重试 |

**重试失败后:** 任务状态标记为 `failed`,不再重试。

### 幂等性处理

**重要:** 由于重试机制,您的接收端可能收到重复的通知,必须实现幂等性处理。

**推荐方案:**

```python
import redis

# 使用 Redis 记录已处理的 Webhook
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def is_webhook_processed(task_id, user_id):
    """检查 Webhook 是否已处理"""
    key = f"webhook_processed:{task_id}_{user_id}"
    return redis_client.exists(key)

def mark_webhook_processed(task_id, user_id):
    """标记 Webhook 已处理 (24小时过期)"""
    key = f"webhook_processed:{task_id}_{user_id}"
    redis_client.setex(key, 86400, '1')

# 在处理 Webhook 时使用
if is_webhook_processed(task_id, user_id):
    logger.info(f"Webhook 已处理过: task_id={task_id}, user_id={user_id}")
    return jsonify({'success': True, 'message': 'Already processed'}), 200

# 处理业务逻辑
process_task_completion(task_id, user_id, submission_link, node_power_earned)

# 标记为已处理
mark_webhook_processed(task_id, user_id)
```

---

## 🧪 测试方法

### 方法 1: 使用 Webhook.site (在线测试)

**步骤:**

1. 访问 https://webhook.site
2. 复制页面显示的唯一 URL (例如: `https://webhook.site/abc-123-def`)
3. 使用该 URL 创建测试任务:

```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -d '{
    "title": "测试任务",
    "video_url": "https://example.com/video.mp4",
    "node_power_reward": 10,
    "callback_url": "https://webhook.site/abc-123-def",
    "callback_secret": "test_secret_123"
  }'
```

4. 在 Telegram Bot 中完成任务
5. 在 webhook.site 页面查看收到的请求详情

### 方法 2: 使用 ngrok (本地测试)

**步骤:**

1. 启动本地接收服务:
```bash
python webhook_receiver.py
# 或
node webhook_receiver.js
```

2. 在另一个终端启动 ngrok:
```bash
ngrok http 5000
```

3. 复制 ngrok 提供的 HTTPS URL (例如: `https://abc123.ngrok.io`)

4. 使用该 URL 创建测试任务:
```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -d '{
    "title": "测试任务",
    "video_url": "https://example.com/video.mp4",
    "node_power_reward": 10,
    "callback_url": "https://abc123.ngrok.io/api/webhooks/x2c-tasks",
    "callback_secret": "test_secret_123"
  }'
```

5. 在 Telegram Bot 中完成任务
6. 查看本地服务日志

### 方法 3: 使用测试脚本 (模拟回调)

**Python 测试脚本:**

```python
import requests
import hmac
import hashlib
import json
from datetime import datetime

# 配置
WEBHOOK_URL = "http://localhost:5000/api/webhooks/x2c-tasks"
SECRET = "test_secret_123"

# 构造测试数据
payload = {
    "event": "task.completed",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "data": {
        "task_id": 999,
        "task_title": "测试任务",
        "user_id": 123456789,
        "username": "test_user",
        "platform": "tiktok",
        "submission_link": "https://www.tiktok.com/@test/video/123456",
        "submitted_at": datetime.utcnow().isoformat() + "Z",
        "verified_at": datetime.utcnow().isoformat() + "Z",
        "node_power_earned": 10,
        "verification_status": "verified",
        "verification_details": {
            "matched": True,
            "match_rate": 100,
            "matched_keywords": ["测试", "关键词"]
        }
    }
}

# 生成签名
payload_str = json.dumps(payload, ensure_ascii=False)
signature = 'sha256=' + hmac.new(
    SECRET.encode(),
    payload_str.encode(),
    hashlib.sha256
).hexdigest()

# 发送请求
headers = {
    'Content-Type': 'application/json',
    'X-Webhook-Event': 'task.completed',
    'X-Webhook-Timestamp': str(int(datetime.utcnow().timestamp())),
    'X-Webhook-Secret': SECRET,
    'X-Webhook-Signature': signature,
    'User-Agent': 'X2C-Bot-Webhook/1.0'
}

response = requests.post(WEBHOOK_URL, json=payload, headers=headers)

print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")
```

---

## 📊 业务逻辑示例

### 示例 1: 更新数据库

```python
import psycopg2

def update_task_and_user(task_id, user_id, submission_link, node_power):
    """更新任务状态和用户算力"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # 更新任务状态
        cur.execute("""
            UPDATE tasks 
            SET status = 'completed',
                submission_link = %s,
                completed_at = NOW()
            WHERE task_id = %s
        """, (submission_link, task_id))
        
        # 更新用户算力
        cur.execute("""
            UPDATE users 
            SET total_node_power = total_node_power + %s,
                completed_tasks = completed_tasks + 1
            WHERE user_id = %s
        """, (node_power, user_id))
        
        # 记录算力变更日志
        cur.execute("""
            INSERT INTO node_power_logs (user_id, task_id, amount, type, created_at)
            VALUES (%s, %s, %s, 'task_reward', NOW())
        """, (user_id, task_id, node_power))
        
        conn.commit()
        print(f"✅ 数据库更新成功: task_id={task_id}, user_id={user_id}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 数据库更新失败: {e}")
        raise
    finally:
        cur.close()
        conn.close()
```

### 示例 2: 发送通知

```python
import requests

def send_user_notification(user_id, task_title, node_power):
    """发送用户通知"""
    
    # 邮件通知
    send_email(
        to=get_user_email(user_id),
        subject="任务完成通知",
        body=f"恭喜!您完成了任务「{task_title}」,获得 {node_power} 算力奖励!"
    )
    
    # 站内消息
    create_notification(
        user_id=user_id,
        title="任务完成",
        message=f"您的任务「{task_title}」已完成,获得 {node_power} 算力",
        type="task_completed"
    )
    
    # 推送通知 (可选)
    send_push_notification(
        user_id=user_id,
        title="任务完成",
        body=f"获得 {node_power} 算力奖励"
    )
    
    print(f"✅ 通知发送成功: user_id={user_id}")
```

### 示例 3: 结算奖励

```python
def settle_task_rewards(user_id, task_id, node_power):
    """结算任务奖励"""
    
    # 计算 x2c 代币奖励 (1 算力 = 10 x2c)
    x2c_tokens = node_power * 10
    
    # 更新用户钱包
    update_user_wallet(user_id, x2c_tokens)
    
    # 记录交易
    create_transaction(
        user_id=user_id,
        amount=x2c_tokens,
        type='task_reward',
        description=f'Task {task_id} completion reward',
        related_task_id=task_id
    )
    
    # 检查是否达成成就
    check_and_award_achievements(user_id)
    
    # 更新排行榜
    update_leaderboard(user_id, node_power)
    
    print(f"✅ 奖励结算成功: user_id={user_id}, x2c={x2c_tokens}")
```

### 示例 4: 异步处理 (推荐)

```python
from celery import Celery

app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def process_task_completion_async(task_id, user_id, submission_link, node_power):
    """异步处理任务完成"""
    try:
        # 更新数据库
        update_task_and_user(task_id, user_id, submission_link, node_power)
        
        # 发送通知
        send_user_notification(user_id, task_id, node_power)
        
        # 结算奖励
        settle_task_rewards(user_id, task_id, node_power)
        
        print(f"✅ 任务处理完成: task_id={task_id}")
    except Exception as e:
        print(f"❌ 任务处理失败: {e}")
        # 可以在这里实现重试逻辑

# 在 Webhook 接收端使用
@app.route('/api/webhooks/x2c-tasks', methods=['POST'])
def receive_webhook():
    # ... 验证签名等步骤 ...
    
    # 异步处理,快速返回 200
    process_task_completion_async.delay(
        task_id, user_id, submission_link, node_power_earned
    )
    
    return jsonify({'success': True}), 200
```

---

## 🔍 故障排查

### 问题 1: 未收到 Webhook 回调

**可能原因:**
- 任务创建时未配置 `callback_url`
- 接收端 URL 错误或无法访问
- 防火墙阻止了请求
- 接收端返回了非 2xx 状态码

**排查步骤:**
1. 检查任务配置:
```bash
curl -X GET "https://web-production-b95cb.up.railway.app/api/tasks/123" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

2. 测试接收端是否可访问:
```bash
curl -X POST "https://your-domain.com/api/webhooks/x2c-tasks" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

3. 查看 X2C Bot 日志 (联系管理员)

### 问题 2: 签名验证失败

**可能原因:**
- 发送端和接收端使用的 `secret` 不一致
- 签名算法实现错误
- payload 字符串不一致

**排查步骤:**
1. 确认 `secret` 一致
2. 打印 `payload_str` 和 `signature` 进行对比
3. 使用测试脚本验证签名算法

### 问题 3: 收到重复通知

**原因:** 重试机制导致

**解决方案:** 实现幂等性处理 (见上文)

### 问题 4: 处理超时

**原因:** 业务逻辑耗时过长

**解决方案:**
- 使用异步处理 (Celery, RabbitMQ 等)
- 快速返回 200 OK
- 将耗时操作放到后台队列

---

## 📋 检查清单

开发完成前请确认:

- [ ] 实现了 POST 接收端点
- [ ] 实现了签名验证
- [ ] 正确解析了所有必填字段
- [ ] 实现了业务逻辑 (更新数据库/发送通知/结算奖励)
- [ ] 返回了正确的 HTTP 响应
- [ ] 实现了幂等性处理
- [ ] 添加了完整的日志记录
- [ ] 实现了错误处理
- [ ] 使用 HTTPS (生产环境)
- [ ] 进行了本地测试
- [ ] 进行了在线测试
- [ ] 文档化了接收端 API

---

## 📞 技术支持

### 获取帮助

- **API 文档:** 查看完整 API 文档了解更多接口
- **测试工具:** 使用 webhook.site 或 ngrok 进行测试
- **日志查询:** 联系管理员查看 Bot 端日志

### 常见问题

**Q: 如何查询任务的回调状态?**

A: 使用 GET /api/tasks/{task_id} 接口:
```bash
curl -X GET "https://web-production-b95cb.up.railway.app/api/tasks/123" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

响应包含:
- `callback_status`: pending/success/failed
- `callback_retry_count`: 重试次数
- `callback_last_attempt`: 最后尝试时间

**Q: 可以修改已创建任务的 callback_url 吗?**

A: 目前不支持,需要在创建任务时配置。

**Q: 支持其他事件类型吗?**

A: 目前只支持 `task.completed` 事件,未来可能支持更多事件。

---

## 📚 相关资源

- **X2C API 完整文档:** 查看所有可用 API 接口
- **Webhook 测试指南:** 详细的测试步骤和方法
- **Bot 使用说明:** 了解 Telegram Bot 的使用方式

---

**文档版本:** v1.0.0  
**最后更新:** 2025-11-27  
**维护者:** X2C Drama Relay Team  
**API 基础 URL:** https://web-production-b95cb.up.railway.app

---

## 附录: 快速参考

### API 认证

所有 API 请求需要在请求头中包含:
```
X-API-Key: x2c_admin_secret_key_2024
```

### 创建任务 API

```bash
POST https://web-production-b95cb.up.railway.app/api/tasks
Content-Type: application/json
X-API-Key: x2c_admin_secret_key_2024

{
  "title": "任务标题",
  "description": "任务描述",
  "video_url": "https://example.com/video.mp4",
  "node_power_reward": 10,
  "keywords_template": "关键词1,关键词2,关键词3",
  "callback_url": "https://your-domain.com/webhook",
  "callback_secret": "your_secret_key"
}
```

### 查询任务 API

```bash
GET https://web-production-b95cb.up.railway.app/api/tasks/{task_id}
X-API-Key: x2c_admin_secret_key_2024
```

### Webhook 请求示例

```bash
POST https://your-domain.com/webhook
Content-Type: application/json
X-Webhook-Event: task.completed
X-Webhook-Timestamp: 1732704600
X-Webhook-Secret: your_secret_key
X-Webhook-Signature: sha256=abc123...

{
  "event": "task.completed",
  "timestamp": "2025-11-27T10:30:00Z",
  "data": {
    "task_id": 123,
    "user_id": 456,
    "platform": "tiktok",
    "submission_link": "https://...",
    "node_power_earned": 10
  }
}
```

---

**祝开发顺利! 🚀**
