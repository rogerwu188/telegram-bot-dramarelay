# X2C Drama Relay Bot - API 文档

## 📋 目录

- [概述](#概述)
- [认证](#认证)
- [任务管理 API](#任务管理-api)
  - [获取任务列表](#1-获取任务列表)
  - [获取单个任务](#2-获取单个任务)
  - [创建任务](#3-创建任务)
  - [更新任务](#4-更新任务)
  - [删除任务](#5-删除任务)
  - [下发任务给用户](#6-下发任务给用户)
- [统计数据 API](#统计数据-api)
- [用户管理 API](#用户管理-api)
- [提交记录 API](#提交记录-api)
- [错误处理](#错误处理)

---

## 概述

**Base URL:** `https://your-railway-app.railway.app`

**API 版本:** v1.0.0

**数据格式:** JSON

**字符编码:** UTF-8

---

## 认证

所有 API 请求都需要提供 API Key 进行认证。

### 方式 1：HTTP Header（推荐）

```http
X-API-Key: your_api_key_here
```

### 方式 2：Query Parameter

```http
GET /api/tasks?api_key=your_api_key_here
```

### 默认 API Key

```
x2c_admin_secret_key_2024
```

> ⚠️ **生产环境请务必修改默认 API Key！** 在 Railway 环境变量中设置 `API_KEY`。

---

## 任务管理 API

### 1. 获取任务列表

获取所有任务的列表，支持分页和状态筛选。

**请求**

```http
GET /api/tasks
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `status` | string | 否 | 任务状态筛选 | `active`, `inactive`, `all` |
| `limit` | integer | 否 | 每页数量 | `10` |
| `offset` | integer | 否 | 偏移量 | `0` |

**响应示例**

```json
{
  "success": true,
  "data": [
    {
      "task_id": 1,
      "title": "养母胜过生母",
      "description": "分享短剧《养母胜过生母》真情反转片段",
      "video_file_id": "https://example.com/video.mp4",
      "thumbnail_url": "https://example.com/thumb.jpg",
      "duration": 15,
      "node_power_reward": 10,
      "platform_requirements": "TikTok,YouTube,Instagram",
      "status": "active",
      "created_at": "2024-11-25T10:00:00"
    }
  ],
  "count": 1
}
```

**cURL 示例**

```bash
curl -X GET "https://your-app.railway.app/api/tasks?status=active&limit=10" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

---

### 2. 获取单个任务

获取指定任务的详细信息，包括提交统计。

**请求**

```http
GET /api/tasks/{task_id}
```

**Path Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 是 | 任务 ID |

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 1,
    "title": "养母胜过生母",
    "description": "分享短剧《养母胜过生母》真情反转片段",
    "video_file_id": "https://example.com/video.mp4",
    "thumbnail_url": "https://example.com/thumb.jpg",
    "duration": 15,
    "node_power_reward": 10,
    "platform_requirements": "TikTok,YouTube,Instagram",
    "status": "active",
    "created_at": "2024-11-25T10:00:00",
    "stats": {
      "submission_count": 25,
      "unique_users": 20
    }
  }
}
```

**cURL 示例**

```bash
curl -X GET "https://your-app.railway.app/api/tasks/1" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

---

### 3. 创建任务

创建一个新的任务。

**请求**

```http
POST /api/tasks
Content-Type: application/json
```

**Request Body**

| 字段 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| `title` | string | **是** | 任务标题 | - |
| `description` | string | 否 | 任务描述 | `null` |
| `video_file_id` | string | 否 | 视频文件 URL 或 Telegram File ID | `null` |
| `thumbnail_url` | string | 否 | 缩略图 URL | `null` |
| `duration` | integer | 否 | 视频时长（秒） | `15` |
| `node_power_reward` | integer | 否 | 奖励算力值 | `10` |
| `platform_requirements` | string | 否 | 支持的平台（逗号分隔） | `TikTok,YouTube,Instagram` |
| `status` | string | 否 | 任务状态 | `active` |

**请求示例**

```json
{
  "title": "霸道总裁爱上我",
  "description": "分享短剧《霸道总裁爱上我》甜蜜片段",
  "video_file_id": "https://example.com/video2.mp4",
  "thumbnail_url": "https://example.com/thumb2.jpg",
  "duration": 20,
  "node_power_reward": 15,
  "platform_requirements": "TikTok,YouTube",
  "status": "active"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 2,
    "title": "霸道总裁爱上我",
    "created_at": "2024-11-25T14:30:00"
  }
}
```

**cURL 示例**

```bash
curl -X POST "https://your-app.railway.app/api/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "霸道总裁爱上我",
    "description": "分享短剧《霸道总裁爱上我》甜蜜片段",
    "video_file_id": "https://example.com/video2.mp4",
    "node_power_reward": 15,
    "status": "active"
  }'
```

---

### 4. 更新任务

更新现有任务的信息。

**请求**

```http
PUT /api/tasks/{task_id}
Content-Type: application/json
```

**Path Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 是 | 任务 ID |

**Request Body**

所有字段都是可选的，只需要提供需要更新的字段。

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 任务标题 |
| `description` | string | 任务描述 |
| `video_file_id` | string | 视频文件 URL |
| `thumbnail_url` | string | 缩略图 URL |
| `duration` | integer | 视频时长 |
| `node_power_reward` | integer | 奖励算力值 |
| `platform_requirements` | string | 支持的平台 |
| `status` | string | 任务状态（`active` 或 `inactive`） |

**请求示例**

```json
{
  "node_power_reward": 20,
  "status": "inactive"
}
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "task_id": 2,
    "title": "霸道总裁爱上我",
    "node_power_reward": 20,
    "status": "inactive",
    "created_at": "2024-11-25T14:30:00"
  }
}
```

**cURL 示例**

```bash
curl -X PUT "https://your-app.railway.app/api/tasks/2" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "node_power_reward": 20,
    "status": "inactive"
  }'
```

---

### 5. 删除任务

删除指定的任务。

**请求**

```http
DELETE /api/tasks/{task_id}
```

**Path Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 是 | 任务 ID |

**响应示例**

```json
{
  "success": true,
  "message": "Task 2 deleted successfully"
}
```

**cURL 示例**

```bash
curl -X DELETE "https://your-app.railway.app/api/tasks/2" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

---

### 6. 下发任务给用户

将任务分配给指定用户或所有用户。

**请求**

```http
POST /api/tasks/{task_id}/assign
Content-Type: application/json
```

**Path Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 是 | 任务 ID |

**Request Body**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `user_ids` | array | 否 | 用户 ID 列表（不提供则下发给所有用户） |
| `notify` | boolean | 否 | 是否发送 Telegram 通知 |

**请求示例 1：下发给所有用户**

```json
{
  "notify": true
}
```

**请求示例 2：下发给指定用户**

```json
{
  "user_ids": [123456789, 987654321],
  "notify": true
}
```

**响应示例**

```json
{
  "success": true,
  "message": "Task assigned to 150 users",
  "data": {
    "task_id": 1,
    "assigned_count": 150,
    "notified": true
  }
}
```

**cURL 示例**

```bash
# 下发给所有用户
curl -X POST "https://your-app.railway.app/api/tasks/1/assign" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "notify": true
  }'

# 下发给指定用户
curl -X POST "https://your-app.railway.app/api/tasks/1/assign" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [123456789, 987654321],
    "notify": true
  }'
```

---

## 统计数据 API

### 获取总览统计

**请求**

```http
GET /api/stats/overview
```

**响应示例**

```json
{
  "success": true,
  "data": {
    "total_users": 1500,
    "total_tasks": 25,
    "total_submissions": 3200,
    "total_node_power": 45000,
    "active_users_today": 320
  }
}
```

**cURL 示例**

```bash
curl -X GET "https://your-app.railway.app/api/stats/overview" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

---

## 用户管理 API

### 获取用户列表

**请求**

```http
GET /api/users
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `limit` | integer | 否 | 每页数量 |
| `offset` | integer | 否 | 偏移量 |
| `sort_by` | string | 否 | 排序字段（`node_power`, `created_at`） |

**响应示例**

```json
{
  "success": true,
  "data": [
    {
      "user_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "total_node_power": 150,
      "completed_tasks": 15,
      "created_at": "2024-11-01T10:00:00"
    }
  ],
  "count": 1
}
```

---

## 提交记录 API

### 获取提交列表

**请求**

```http
GET /api/submissions
```

**Query Parameters**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 否 | 按任务 ID 筛选 |
| `user_id` | integer | 否 | 按用户 ID 筛选 |
| `platform` | string | 否 | 按平台筛选 |
| `limit` | integer | 否 | 每页数量 |
| `offset` | integer | 否 | 偏移量 |

**响应示例**

```json
{
  "success": true,
  "data": [
    {
      "submission_id": 1,
      "user_id": 123456789,
      "task_id": 1,
      "platform": "TikTok",
      "video_link": "https://www.tiktok.com/@user/video/123",
      "submitted_at": "2024-11-25T15:30:00",
      "reward": 10
    }
  ],
  "count": 1
}
```

---

## 错误处理

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
| `401` | 认证失败（API Key 无效） |
| `404` | 资源不存在 |
| `500` | 服务器内部错误 |

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

## 完整示例：创建并下发任务

### 步骤 1：创建任务

```bash
curl -X POST "https://your-app.railway.app/api/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "重生之我在古代当皇帝",
    "description": "分享短剧《重生之我在古代当皇帝》精彩片段",
    "video_file_id": "https://example.com/video3.mp4",
    "node_power_reward": 12,
    "status": "active"
  }'
```

**响应：**

```json
{
  "success": true,
  "data": {
    "task_id": 3,
    "title": "重生之我在古代当皇帝",
    "created_at": "2024-11-25T16:00:00"
  }
}
```

### 步骤 2：下发任务给所有用户

```bash
curl -X POST "https://your-app.railway.app/api/tasks/3/assign" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "notify": true
  }'
```

**响应：**

```json
{
  "success": true,
  "message": "Task assigned to 1500 users",
  "data": {
    "task_id": 3,
    "assigned_count": 1500,
    "notified": true
  }
}
```

---

## 注意事项

1. **API Key 安全**：请妥善保管 API Key，不要在客户端代码中暴露
2. **速率限制**：目前没有速率限制，但建议合理使用避免过载
3. **时区**：所有时间戳使用 UTC 时区，格式为 ISO 8601
4. **视频文件**：`video_file_id` 可以是：
   - Telegram File ID（如果视频已上传到 Telegram）
   - 公开可访问的视频 URL
5. **任务状态**：
   - `active`：任务激活，用户可以看到并提交
   - `inactive`：任务停用，用户看不到

---

## 技术支持

如有问题或建议，请联系开发团队。

**API 版本：** v1.0.0  
**最后更新：** 2024-11-25
