# X2C Drama Relay Bot - API 文档（精简版）

## 📋 概述

本 API 提供三个核心功能：

1. **任务管理** - 创建、更新、删除任务
2. **任务下架** - 停用不需要的任务
3. **播放量统计** - 查看任务的提交数据和统计

---

## 🔐 认证

所有 API 请求都需要提供 API Key。

### 方式 1：HTTP Header（推荐）

```http
X-API-Key: x2c_admin_secret_key_2024
```

### 方式 2：Query Parameter

```http
?api_key=x2c_admin_secret_key_2024
```

---

## 📡 Base URL

```
https://your-railway-app.railway.app
```

---

## 1️⃣ 任务管理 API

### 1.1 创建任务

创建一个新的短剧分享任务。

**请求**

```http
POST /api/tasks
Content-Type: application/json
X-API-Key: x2c_admin_secret_key_2024
```

**请求参数**

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `title` | string | **是** | 任务标题（短剧名称） | `"养母胜过生母"` |
| `description` | string | 否 | 任务描述 | `"分享短剧精彩片段"` |
| `video_file_id` | string | 否 | 视频 URL 或 Telegram File ID | `"https://example.com/video.mp4"` |
| `thumbnail_url` | string | 否 | 缩略图 URL | `"https://example.com/thumb.jpg"` |
| `duration` | integer | 否 | 视频时长（秒） | `15` |
| `node_power_reward` | integer | 否 | 奖励算力值 | `10` |
| `platform_requirements` | string | 否 | 支持的平台（逗号分隔） | `"TikTok,YouTube,Instagram"` |
| `status` | string | 否 | 任务状态 | `"active"` 或 `"inactive"` |

**请求示例**

```bash
curl -X POST "https://your-app.railway.app/api/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "霸道总裁爱上我",
    "description": "分享短剧《霸道总裁爱上我》甜蜜片段",
    "video_file_id": "https://example.com/video.mp4",
    "node_power_reward": 15,
    "status": "active"
  }'
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "title": "霸道总裁爱上我",
    "created_at": "2024-11-25T16:00:00"
  }
}
```

---

### 1.2 更新任务

更新现有任务的信息。

**请求**

```http
PUT /api/tasks/{task_id}
Content-Type: application/json
X-API-Key: x2c_admin_secret_key_2024
```

**请求参数**

所有字段都是可选的，只需提供需要更新的字段。

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 任务标题 |
| `description` | string | 任务描述 |
| `video_file_id` | string | 视频 URL |
| `node_power_reward` | integer | 奖励算力值 |
| `status` | string | 任务状态 |

**请求示例**

```bash
curl -X PUT "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "node_power_reward": 20,
    "description": "更新后的描述"
  }'
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "title": "霸道总裁爱上我",
    "node_power_reward": 20,
    "status": "active"
  }
}
```

---

### 1.3 删除任务

永久删除任务。

**请求**

```http
DELETE /api/tasks/{task_id}
X-API-Key: x2c_admin_secret_key_2024
```

**请求示例**

```bash
curl -X DELETE "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

**响应示例**

```json
{
  "success": true,
  "message": "Task 5 deleted successfully"
}
```

---

## 2️⃣ 任务下架 API

### 2.1 下架任务（停用）

将任务状态设置为 `inactive`，用户将看不到此任务。

**请求**

```http
PUT /api/tasks/{task_id}
Content-Type: application/json
X-API-Key: x2c_admin_secret_key_2024
```

**请求参数**

```json
{
  "status": "inactive"
}
```

**请求示例**

```bash
curl -X PUT "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive"
  }'
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "title": "霸道总裁爱上我",
    "status": "inactive"
  }
}
```

---

### 2.2 重新上架任务

将任务状态设置为 `active`，用户可以再次看到此任务。

**请求示例**

```bash
curl -X PUT "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active"
  }'
```

---

## 3️⃣ 播放量统计 API

### 3.1 获取任务详情和统计

获取单个任务的详细信息，包括提交统计。

**请求**

```http
GET /api/tasks/{task_id}
X-API-Key: x2c_admin_secret_key_2024
```

**请求示例**

```bash
curl -X GET "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "title": "霸道总裁爱上我",
    "description": "分享短剧甜蜜片段",
    "video_file_id": "https://example.com/video.mp4",
    "node_power_reward": 15,
    "status": "active",
    "created_at": "2024-11-25T16:00:00",
    "stats": {
      "submission_count": 156,
      "unique_users": 142
    }
  }
}
```

**统计字段说明**

| 字段 | 说明 |
|------|------|
| `submission_count` | 总提交次数（播放量） |
| `unique_users` | 独立用户数 |

---

### 3.2 获取所有任务统计

获取所有任务的统计数据。

**请求**

```http
GET /api/stats/tasks
X-API-Key: x2c_admin_secret_key_2024
```

**请求示例**

```bash
curl -X GET "https://your-app.railway.app/api/stats/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

**响应示例**

```json
{
  "success": true,
  "data": [
    {
      "task_id": 1,
      "title": "养母胜过生母",
      "status": "active",
      "node_power_reward": 10,
      "created_at": "2024-11-20T10:00:00",
      "submission_count": 320,
      "unique_users": 280,
      "verified_count": 315
    },
    {
      "task_id": 5,
      "title": "霸道总裁爱上我",
      "status": "active",
      "node_power_reward": 15,
      "created_at": "2024-11-25T16:00:00",
      "submission_count": 156,
      "unique_users": 142,
      "verified_count": 150
    }
  ]
}
```

**统计字段说明**

| 字段 | 说明 |
|------|------|
| `submission_count` | 总提交次数（播放量） |
| `unique_users` | 独立用户数 |
| `verified_count` | 已验证的提交数 |

---

### 3.3 获取任务提交记录

获取指定任务的所有提交记录。

**请求**

```http
GET /api/submissions/task/{task_id}
X-API-Key: x2c_admin_secret_key_2024
```

**Query Parameters**

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `limit` | integer | 每页数量 | `50` |
| `offset` | integer | 偏移量 | `0` |

**请求示例**

```bash
curl -X GET "https://your-app.railway.app/api/submissions/task/5?limit=50&offset=0" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

**响应示例**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "user_id": 123456789,
      "username": "john_doe",
      "task_id": 5,
      "platform": "TikTok",
      "video_link": "https://www.tiktok.com/@user/video/123456",
      "status": "verified",
      "submitted_at": "2024-11-25T17:30:00",
      "reward": 15
    },
    {
      "id": 2,
      "user_id": 987654321,
      "username": "jane_smith",
      "task_id": 5,
      "platform": "YouTube",
      "video_link": "https://www.youtube.com/watch?v=abc123",
      "status": "verified",
      "submitted_at": "2024-11-25T17:45:00",
      "reward": 15
    }
  ],
  "count": 2,
  "total": 156
}
```

---

## 📊 完整工作流程示例

### 场景：创建任务 → 查看统计 → 下架任务

```bash
# 1️⃣ 创建任务
curl -X POST "https://your-app.railway.app/api/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "重生之我在古代当皇帝",
    "description": "分享短剧精彩片段",
    "node_power_reward": 12,
    "status": "active"
  }'

# 响应：{"success": true, "data": {"task_id": 10, ...}}

# 2️⃣ 查看任务统计（等待一段时间后）
curl -X GET "https://your-app.railway.app/api/tasks/10" \
  -H "X-API-Key: x2c_admin_secret_key_2024"

# 响应：
# {
#   "success": true,
#   "data": {
#     "task_id": 10,
#     "title": "重生之我在古代当皇帝",
#     "stats": {
#       "submission_count": 89,
#       "unique_users": 78
#     }
#   }
# }

# 3️⃣ 下架任务
curl -X PUT "https://your-app.railway.app/api/tasks/10" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive"
  }'

# 响应：{"success": true, "data": {"task_id": 10, "status": "inactive"}}
```

---

## ❌ 错误处理

### 错误响应格式

```json
{
  "success": false,
  "error": "Error message here"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| `200` | 请求成功 |
| `201` | 创建成功 |
| `400` | 请求参数错误 |
| `401` | API Key 无效 |
| `404` | 任务不存在 |
| `500` | 服务器错误 |

### 常见错误

**1. API Key 无效**

```json
{
  "success": false,
  "error": "Invalid or missing API key"
}
```

**2. 任务不存在**

```json
{
  "success": false,
  "error": "Task not found"
}
```

**3. 缺少必填字段**

```json
{
  "success": false,
  "error": "Title is required"
}
```

---

## 🔧 配置说明

### 环境变量

在 Railway 中设置以下环境变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `API_KEY` | API 认证密钥 | `x2c_admin_secret_key_2024` |
| `API_PORT` | API 服务端口 | `5000` |
| `DATABASE_URL` | PostgreSQL 数据库连接 | 自动配置 |

---

## 📝 注意事项

1. **API Key 安全**：请妥善保管 API Key，不要在客户端代码中暴露
2. **任务状态**：
   - `active`：任务激活，用户可以看到并提交
   - `inactive`：任务停用，用户看不到
3. **播放量统计**：
   - `submission_count`：总提交次数，相当于播放量
   - `unique_users`：独立用户数，去重后的真实用户数
4. **时区**：所有时间戳使用 UTC 时区，格式为 ISO 8601

---

## 📞 技术支持

如有问题或建议，请联系开发团队。

**API 版本：** v1.0.0  
**最后更新：** 2024-11-25
