# DramaRelay Bot - Project ID 数据结构文档

## 概述

本文档定义了 DramaRelay Bot 与 X2C 任务分发平台之间的数据接口规范，实现基于 `project_id` 的全链路追踪。

**核心设计原则：**
- `project_id` 作为全链路唯一标识符（UUID格式）
- 一个 project 可能包含多个 tasks/episodes
- 每个 task 独立统计，多集剧就是多个任务
- `project_id` 在整个数据流转过程中保持不变

**数据流转路径：**
```
X2C平台 → POST /api/tasks (含project_id) → Bot存储 → 用户完成任务 → Webhook回调 (含project_id) → X2C平台
```

---

## 1. 任务创建接口（X2C → Bot）

### 接口信息
- **URL**: `https://web-production-b95cb.up.railway.app/api/tasks`
- **方法**: `POST`
- **认证**: Header `X-API-Key: x2c_admin_secret_key_2024`

### 请求数据结构

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "霸道总裁爱上我 第1集",
  "description": "发布短剧《霸道总裁爱上我》第1集到社交平台",
  "video_file_id": "https://example.com/videos/drama-ep1.mp4",
  "video_url": "https://example.com/videos/drama-ep1.mp4",
  "thumbnail_url": "https://example.com/thumbnails/drama-ep1.jpg",
  "video_title": "霸道总裁爱上我 EP1",
  "task_template": "请将视频发布到 {platform}，标题：{title}，描述：{description}",
  "duration": 15,
  "node_power_reward": 10,
  "platform_requirements": "TikTok,YouTube,Instagram",
  "status": "active",
  "callback_url": "https://x2c-platform.com/api/webhooks/task-completion",
  "callback_secret": "your_webhook_secret_key"
}
```

### 字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `project_id` | String (UUID) | 否 | 项目唯一标识符，建议使用UUID格式。如果不提供，该任务将没有project_id关联 |
| `title` | String | 是 | 任务标题 |
| `description` | String | 否 | 任务描述 |
| `video_file_id` | String (URL) | 否 | 视频文件URL（优先使用此字段） |
| `video_url` | String (URL) | 否 | 视频文件URL（备用字段，与video_file_id二选一） |
| `thumbnail_url` | String (URL) | 否 | 视频缩略图URL |
| `video_title` | String | 否 | 视频标题 |
| `task_template` | String | 否 | 任务模板文本 |
| `duration` | Integer | 否 | 任务时长（天），默认15天 |
| `node_power_reward` | Integer | 否 | 节点算力奖励，默认10 |
| `platform_requirements` | String | 否 | 平台要求，逗号分隔，默认"TikTok,YouTube,Instagram" |
| `status` | String | 否 | 任务状态，默认"active"（可选值：active, inactive） |
| `callback_url` | String (URL) | 否 | 任务完成回调URL |
| `callback_secret` | String | 否 | 回调签名密钥 |

### 响应数据结构

**成功响应 (201 Created):**
```json
{
  "success": true,
  "data": {
    "task_id": 42,
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "霸道总裁爱上我 第1集",
    "created_at": "2024-11-29T10:30:00.000000"
  }
}
```

**失败响应 (400 Bad Request):**
```json
{
  "success": false,
  "error": "Title is required"
}
```

**认证失败 (401 Unauthorized):**
```json
{
  "success": false,
  "error": "Invalid or missing API key"
}
```

---

## 2. 任务完成回调接口（Bot → X2C）

### 接口信息
- **URL**: 由 X2C 平台在创建任务时通过 `callback_url` 字段提供
- **方法**: `POST`
- **认证**: HMAC-SHA256 签名（使用 `callback_secret`）

### 回调触发时机
当用户完成任务并通过验证后，Bot 会自动向 `callback_url` 发送回调通知。

### 请求头
```
Content-Type: application/json
X-Webhook-Signature: sha256=<HMAC-SHA256签名>
```

**签名算法：**
```python
import hmac
import hashlib
import json

payload = {...}  # 回调数据
secret = "your_webhook_secret_key"

signature = hmac.new(
    secret.encode('utf-8'),
    json.dumps(payload, separators=(',', ':')).encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 请求头中发送: X-Webhook-Signature: sha256={signature}
```

### 回调数据结构

```json
{
  "event": "task.completed",
  "timestamp": "2024-11-29T10:45:30.123456Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "task_title": "霸道总裁爱上我 第1集",
    "user_id": 123456789,
    "username": "user_alice",
    "platform": "TikTok",
    "submission_link": "https://www.tiktok.com/@user/video/1234567890",
    "submitted_at": "2024-11-29T10:40:00.000000Z",
    "verified_at": "2024-11-29T10:45:30.123456Z",
    "node_power_earned": 10,
    "verification_status": "verified",
    "verification_details": {
      "likes": 150,
      "views": 1200,
      "comments": 30
    }
  }
}
```

### 字段说明

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `event` | String | 事件类型，固定为 "task.completed" |
| `timestamp` | String (ISO 8601) | 回调发送时间（UTC） |
| `data.project_id` | String (UUID) | 项目唯一标识符（与创建任务时传入的project_id一致，如果创建时未提供则为null） |
| `data.task_id` | Integer | Bot内部任务ID |
| `data.task_title` | String | 任务标题 |
| `data.user_id` | Integer | Telegram用户ID |
| `data.username` | String | Telegram用户名 |
| `data.platform` | String | 发布平台（TikTok/YouTube/Instagram等） |
| `data.submission_link` | String (URL) | 用户提交的链接 |
| `data.submitted_at` | String (ISO 8601) | 用户提交时间（UTC） |
| `data.verified_at` | String (ISO 8601) | 验证通过时间（UTC） |
| `data.node_power_earned` | Integer | 用户获得的节点算力奖励 |
| `data.verification_status` | String | 验证状态，固定为 "verified" |
| `data.verification_details` | Object | 验证详情（点赞数、浏览量、评论数等，可能为空对象） |

### 响应要求

X2C 平台的回调接收端应返回 HTTP 2xx 状态码表示成功接收。

**成功响应示例：**
```json
{
  "success": true,
  "message": "Webhook received successfully"
}
```

如果回调失败，Bot 会自动重试（最多3次）。

---

## 3. 数据库表结构

### drama_tasks 表

```sql
CREATE TABLE drama_tasks (
    task_id SERIAL PRIMARY KEY,
    project_id VARCHAR(255),  -- 新增字段：项目唯一标识符
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_file_id TEXT,
    video_url TEXT,
    thumbnail_url TEXT,
    video_title VARCHAR(255),
    task_template TEXT,
    keywords_template TEXT,  -- Bot自动生成，与外部平台无关
    duration INTEGER DEFAULT 15,
    node_power_reward INTEGER DEFAULT 10,
    platform_requirements VARCHAR(255) DEFAULT 'TikTok,YouTube,Instagram',
    status VARCHAR(50) DEFAULT 'active',
    callback_url TEXT,
    callback_secret VARCHAR(255),
    callback_retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 添加索引以提高查询性能
CREATE INDEX idx_project_id ON drama_tasks(project_id);
CREATE INDEX idx_status ON drama_tasks(status);
```

---

## 4. 使用场景示例

### 场景1：单集短剧任务

**X2C平台创建任务：**
```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "霸道总裁爱上我 第1集",
    "video_url": "https://example.com/videos/drama-ep1.mp4",
    "callback_url": "https://x2c-platform.com/api/webhooks/task-completion",
    "callback_secret": "secret_key_123"
  }'
```

**用户完成任务后，Bot回调：**
```json
{
  "event": "task.completed",
  "timestamp": "2024-11-29T10:45:30.123456Z",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "user_id": 123456789,
    "platform": "TikTok",
    "submission_link": "https://www.tiktok.com/@user/video/1234567890"
  }
}
```

### 场景2：多集短剧项目

同一个 `project_id` 可以创建多个任务（不同集数）：

```bash
# 第1集
curl -X POST ... -d '{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "霸道总裁爱上我 第1集",
  ...
}'

# 第2集
curl -X POST ... -d '{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "霸道总裁爱上我 第2集",
  ...
}'

# 第3集
curl -X POST ... -d '{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "霸道总裁爱上我 第3集",
  ...
}'
```

每个任务独立统计，但通过 `project_id` 可以关联到同一个项目。

---

## 5. 注意事项

### 5.1 字段兼容性
- `video_file_id` 和 `video_url` 两个字段功能相同，优先使用 `video_file_id`
- `keywords_template` 字段由Bot自动生成，外部平台无需传入

### 5.2 回调重试机制
- Bot会自动重试失败的回调（最多3次）
- 重试间隔：第1次立即，第2次30秒后，第3次60秒后
- 建议X2C平台实现幂等性处理，避免重复回调导致数据问题

### 5.3 签名验证
X2C平台接收回调时，应验证 `X-Webhook-Signature` 签名：

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload, signature, secret):
    """验证Webhook签名"""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        json.dumps(payload, separators=(',', ':')).encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # 去除 "sha256=" 前缀
    if signature.startswith('sha256='):
        signature = signature[7:]
    
    return hmac.compare_digest(signature, expected_signature)
```

### 5.4 project_id 格式建议
- 推荐使用标准UUID格式（如 `550e8400-e29b-41d4-a716-446655440000`）
- 最大长度255字符
- 可以为空（null），但建议所有任务都提供project_id以便追踪

### 5.5 统计查询
如需按项目统计所有任务的完成情况，可以使用以下SQL查询：

```sql
-- 按project_id统计任务完成情况
SELECT 
    dt.project_id,
    COUNT(DISTINCT dt.task_id) as total_tasks,
    COUNT(ut.user_id) as total_submissions,
    COUNT(CASE WHEN ut.status = 'verified' THEN 1 END) as verified_submissions,
    COUNT(DISTINCT ut.user_id) as unique_users
FROM drama_tasks dt
LEFT JOIN user_tasks ut ON dt.task_id = ut.task_id
WHERE dt.project_id = '550e8400-e29b-41d4-a716-446655440000'
GROUP BY dt.project_id;
```

---

## 6. 技术支持

如有问题，请联系：
- **GitHub仓库**: https://github.com/rogerwu188/telegram-bot-dramarelay
- **部署地址**: https://web-production-b95cb.up.railway.app

---

**文档版本**: 1.0  
**最后更新**: 2024-11-29  
**维护者**: DramaRelay Bot Team
