# X2C 平台 ↔ DramaRelay Bot 对接文档（最终版）

## 文档说明

本文档定义了 X2C 任务分发平台与 DramaRelay Bot 之间的数据接口规范，遵循**最小改动原则**。

**核心设计：**
- `project_id` (UUID) + `task_id` (整数) 双重标识
- 一个 project 可包含多个 tasks/episodes
- 每个 task 独立统计
- 完成即调用，实时回传统计数据

---

## 1. 任务下发接口（X2C → Bot）

### 接口信息
- **URL**: `https://web-production-b95cb.up.railway.app/api/tasks`
- **方法**: `POST`
- **认证**: Header `X-API-Key: x2c_admin_secret_key_2024`

### 请求数据结构

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 42,
  "title": "霸道总裁爱上我 第1集",
  "description": "发布短剧《霸道总裁爱上我》第1集到社交平台",
  "video_url": "https://example.com/videos/drama-ep1.mp4",
  "duration": 30,
  "node_power_reward": 10,
  "platform_requirements": "TikTok,YouTube",
  "status": "active",
  "callback_url": "https://x2c-platform.com/api/webhooks/stats",
  "callback_secret": "your_webhook_secret_key"
}
```

### 字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `project_id` | String (UUID) | 否 | 项目唯一标识符 |
| `task_id` | Integer | 否 | X2C 平台的任务 ID |
| `title` | String | 是 | 任务标题 |
| `description` | String | 否 | 任务描述 |
| `video_url` | String (URL) | 否 | 视频文件 URL |
| `duration` | Integer | 否 | 任务时长（天），默认 15 |
| `node_power_reward` | Integer | 否 | 节点算力奖励，默认 10 |
| `platform_requirements` | String | 否 | 平台要求，逗号分隔 |
| `status` | String | 否 | 任务状态，默认 "active" |
| `callback_url` | String (URL) | 否 | 统计回调 URL |
| `callback_secret` | String | 否 | 回调签名密钥 |

### 响应数据结构

**成功响应 (201 Created):**
```json
{
  "success": true,
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 42
}
```
✅ **两个值都返回 = 下发成功**

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

## 2. 统计回传接口（Bot → X2C）

### 接口信息
- **URL**: 由 X2C 平台在下发任务时通过 `callback_url` 字段提供
- **方法**: `POST`
- **认证**: HMAC-SHA256 签名（使用 `callback_secret`）

### 触发时机
**完成即调用**：每个用户完成任务并通过验证后，Bot 立即发送该次完成的统计数据。

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
  "site_name": "DramaRelayBot",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 1,
      "yt_view_count": 150,
      "yt_like_count": 20,
      "yt_account_count": 1
    }
  ]
}
```

### 字段说明

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `site_name` | String | 是 | 分发站点名称，固定为 "DramaRelayBot" |
| `stats` | Array | 是 | 统计数据数组（每次回调只包含 1 条记录） |
| `stats[].project_id` | String (UUID) | 否 | 项目 ID（与下发时一致） |
| `stats[].task_id` | Integer | 否 | 任务 ID（与下发时一致） |
| `stats[].duration` | Integer | 是 | 任务时长（天） |
| `stats[].account_count` | Integer | 是 | 完成账号数（单次完成为 1） |
| `stats[].yt_view_count` | Integer | 否 | YouTube 播放量（仅 YouTube 平台且有数据时包含） |
| `stats[].yt_like_count` | Integer | 否 | YouTube 点赞数（仅 YouTube 平台且有数据时包含） |
| `stats[].yt_account_count` | Integer | 否 | YouTube 账号数（仅 YouTube 平台时包含） |
| `stats[].tt_view_count` | Integer | 否 | TikTok 播放量（仅 TikTok 平台且有数据时包含） |
| `stats[].tt_like_count` | Integer | 否 | TikTok 点赞数（仅 TikTok 平台且有数据时包含） |
| `stats[].tt_account_count` | Integer | 否 | TikTok 账号数（仅 TikTok 平台时包含） |

**重要说明：**
- `view_count`、`like_count` 等数据**只在 Bot 有数据时才包含**
- 如果 Bot 没有抓取到这些数据，对应字段**不会出现在回调中**
- 平台字段（`yt_*`、`tt_*`）根据用户提交的平台自动识别填充

### 平台识别逻辑

Bot 根据用户提交任务时选择的平台（`platform` 字段）自动识别：
- **YouTube**: 包含 `yt_account_count`，如有数据则包含 `yt_view_count`、`yt_like_count`
- **TikTok**: 包含 `tt_account_count`，如有数据则包含 `tt_view_count`、`tt_like_count`
- **其他平台**: 可类似扩展

### 响应要求

X2C 平台应返回 HTTP 2xx 状态码表示成功接收。

**成功响应示例：**
```json
{
  "success": true,
  "message": "Stats received successfully"
}
```

如果回调失败，Bot 会自动重试（最多 3 次）。

---

## 3. 数据库表结构

### drama_tasks 表

```sql
CREATE TABLE drama_tasks (
    task_id SERIAL PRIMARY KEY,              -- Bot 内部 ID（自增）
    project_id VARCHAR(255),                 -- X2C 项目 ID
    external_task_id INTEGER,                -- X2C 任务 ID
    title VARCHAR(255) NOT NULL,
    description TEXT,
    video_file_id TEXT,
    video_url TEXT,
    thumbnail_url TEXT,
    video_title VARCHAR(255),
    task_template TEXT,
    keywords_template TEXT,
    duration INTEGER DEFAULT 15,
    node_power_reward INTEGER DEFAULT 10,
    platform_requirements VARCHAR(255) DEFAULT 'TikTok,YouTube,Instagram',
    status VARCHAR(50) DEFAULT 'active',
    callback_url TEXT,
    callback_secret VARCHAR(255),
    callback_retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_project_id ON drama_tasks(project_id);
CREATE INDEX idx_external_task_id ON drama_tasks(external_task_id);
CREATE INDEX idx_status ON drama_tasks(status);
```

**字段说明：**
- `task_id`: Bot 内部主键，自动递增
- `external_task_id`: 存储 X2C 平台提供的 `task_id`
- `project_id`: 存储 X2C 平台提供的 `project_id`

---

## 4. 使用场景示例

### 场景 1：单集短剧任务

**X2C 平台下发任务：**
```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "title": "霸道总裁爱上我 第1集",
    "video_url": "https://example.com/videos/drama-ep1.mp4",
    "duration": 30,
    "callback_url": "https://x2c-platform.com/api/webhooks/stats",
    "callback_secret": "secret_key_123"
  }'
```

**Bot 响应：**
```json
{
  "success": true,
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 42
}
```

**用户完成任务后，Bot 回传统计（YouTube 平台，有播放数据）：**
```json
{
  "site_name": "DramaRelayBot",
  "stats": [{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "duration": 30,
    "account_count": 1,
    "yt_view_count": 150,
    "yt_like_count": 20,
    "yt_account_count": 1
  }]
}
```

**用户完成任务后，Bot 回传统计（TikTok 平台，无播放数据）：**
```json
{
  "site_name": "DramaRelayBot",
  "stats": [{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "duration": 30,
    "account_count": 1,
    "tt_account_count": 1
  }]
}
```
*注意：因为没有播放数据，所以不包含 `tt_view_count` 和 `tt_like_count` 字段*

---

### 场景 2：多集短剧项目

同一个 `project_id` 可以下发多个任务（不同集数）：

```bash
# 第 1 集
curl -X POST ... -d '{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 101,
  "title": "霸道总裁爱上我 第1集",
  ...
}'

# 第 2 集
curl -X POST ... -d '{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 102,
  "title": "霸道总裁爱上我 第2集",
  ...
}'

# 第 3 集
curl -X POST ... -d '{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 103,
  "title": "霸道总裁爱上我 第3集",
  ...
}'
```

每个任务独立统计，但通过 `project_id` 关联到同一个项目。

---

### 场景 3：聚合统计查询

X2C 平台可以根据 `project_id` 聚合所有回传的统计数据，计算项目总体进度：

```python
# 伪代码示例
total_stats = {
    'view_count': 0,
    'like_count': 0,
    'account_count': 0,
    'yt_view_count': 0,
    'yt_like_count': 0,
    'yt_account_count': 0,
    'tt_view_count': 0,
    'tt_like_count': 0,
    'tt_account_count': 0
}

# 遍历所有回传的 stats 数据
for stat in all_stats_from_bot:
    if stat['project_id'] == '550e8400-...':
        total_stats['account_count'] += stat.get('account_count', 0)
        total_stats['yt_view_count'] += stat.get('yt_view_count', 0)
        total_stats['yt_like_count'] += stat.get('yt_like_count', 0)
        total_stats['yt_account_count'] += stat.get('yt_account_count', 0)
        total_stats['tt_view_count'] += stat.get('tt_view_count', 0)
        total_stats['tt_like_count'] += stat.get('tt_like_count', 0)
        total_stats['tt_account_count'] += stat.get('tt_account_count', 0)

# 计算总播放量和点赞数
total_stats['view_count'] = total_stats['yt_view_count'] + total_stats['tt_view_count']
total_stats['like_count'] = total_stats['yt_like_count'] + total_stats['tt_like_count']
```

---

## 5. 注意事项

### 5.1 ID 映射关系
- **Bot 内部 ID**: `task_id` (SERIAL 主键，自增)
- **X2C 平台 ID**: `external_task_id` (存储 X2C 的 `task_id`)
- **回传时使用**: `external_task_id`（即 X2C 的 `task_id`）

### 5.2 数据完整性
- 只发送 Bot **已有的数据**
- 没有的字段（如 `view_count`、`like_count`）**不包含在回调中**
- X2C 平台应处理字段缺失的情况，默认为 0 或忽略

### 5.3 回调重试机制
- Bot 会自动重试失败的回调（最多 3 次）
- 重试间隔：第 1 次立即，第 2 次 30 秒后，第 3 次 60 秒后
- 建议 X2C 平台实现幂等性处理

### 5.4 签名验证
X2C 平台接收回调时，应验证 `X-Webhook-Signature` 签名：

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload, signature, secret):
    """验证 Webhook 签名"""
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

### 5.5 平台扩展
目前支持的平台：
- YouTube (yt_*)
- TikTok (tt_*)

如需支持更多平台（如 Instagram、Facebook 等），可以类似扩展：
- `ig_view_count`, `ig_like_count`, `ig_account_count`
- `fb_view_count`, `fb_like_count`, `fb_account_count`

### 5.6 统计数据来源
- `view_count`、`like_count` 来自 Bot 的链接验证结果（`verification_details`）
- 并非所有提交都有这些数据（取决于平台 API 是否返回）
- 如果没有数据，对应字段不会出现在回调中

---

## 6. 测试验证

### 6.1 测试任务下发

```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "test-project-001",
    "task_id": 999,
    "title": "测试任务",
    "video_url": "https://example.com/test.mp4",
    "callback_url": "https://webhook.site/your-unique-url",
    "callback_secret": "test_secret"
  }'
```

**预期响应：**
```json
{
  "success": true,
  "project_id": "test-project-001",
  "task_id": 999
}
```

### 6.2 测试回调接收

使用 [webhook.site](https://webhook.site) 创建临时回调 URL，观察 Bot 发送的回调数据格式。

**预期回调数据：**
```json
{
  "site_name": "DramaRelayBot",
  "stats": [{
    "project_id": "test-project-001",
    "task_id": 999,
    "duration": 15,
    "account_count": 1,
    "yt_account_count": 1
  }]
}
```

### 6.3 验证签名

确保回调请求包含正确的签名：
```
X-Webhook-Signature: sha256=abc123...
```

---

## 7. 技术支持

### 部署信息
- **GitHub 仓库**: https://github.com/rogerwu188/telegram-bot-dramarelay
- **部署地址**: https://web-production-b95cb.up.railway.app
- **API 认证**: `X-API-Key: x2c_admin_secret_key_2024`

### 联系方式
如有问题，请通过 GitHub Issues 反馈。

---

## 8. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2024-11-29 | 初始版本，基于最小改动原则设计 |

---

**文档版本**: 1.0  
**最后更新**: 2024-11-29  
**维护者**: DramaRelay Bot Team
