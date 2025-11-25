# X2C Drama Relay Bot - API 文档

## 📋 概述

本 API 提供三个核心功能，用于外部平台管理短剧分享任务：

1. **生成任务** - 创建新的短剧分享任务
2. **下架任务** - 停用不需要的任务
3. **管理任务** - 查看任务的成功分发次数

---

## 🔐 认证

所有 API 请求都需要提供 API Key。

### HTTP Header（推荐）

```http
X-API-Key: x2c_admin_secret_key_2024
```

### Query Parameter

```http
?api_key=x2c_admin_secret_key_2024
```

> ⚠️ **生产环境请务必修改默认 API Key！** 在 Railway 环境变量中设置 `API_KEY`。

---

## 📡 Base URL

```
https://your-railway-app.railway.app
```

---

## 1️⃣ 生成任务

创建一个新的短剧分享任务，用户将在 Telegram Bot 中看到此任务。

### 请求

```http
POST /api/tasks
Content-Type: application/json
X-API-Key: x2c_admin_secret_key_2024
```

### 请求参数

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `video_title` | string | **是** | 视频标题 | `"养母胜过生母 第15集"` |
| `video_url` | string | **是** | 任务视频链接 | `"https://example.com/video.mp4"` |
| `task_template` | string | **是** | 任务下发模板（用户看到的任务描述） | `"分享短剧《养母胜过生母》精彩片段"` |
| `keywords_template` | string | **是** | 关键词模板（用于验证用户提交，逗号分隔） | `"养母,胜过,生母"` |
| `node_power_reward` | integer | 否 | 奖励算力值 | `10` |
| `platform_requirements` | string | 否 | 支持的平台（逗号分隔） | `"TikTok,YouTube,Instagram"` |
| `status` | string | 否 | 任务状态 | `"active"` 或 `"inactive"` |

### 请求示例

```bash
curl -X POST "https://your-app.railway.app/api/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "video_title": "养母胜过生母 第15集",
    "video_url": "https://example.com/drama/episode15.mp4",
    "task_template": "分享短剧《养母胜过生母》第15集精彩片段，讲述养母的无私付出",
    "keywords_template": "养母,胜过,生母,第15集",
    "node_power_reward": 10,
    "platform_requirements": "TikTok,YouTube,Instagram",
    "status": "active"
  }'
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "title": "养母胜过生母 第15集",
    "created_at": "2024-11-25T16:00:00"
  }
}
```

### 字段说明

- **video_title**: 视频标题，会显示在任务列表中
- **video_url**: 原始视频链接，用于用户下载参考
- **task_template**: 任务描述模板，告诉用户需要做什么
- **keywords_template**: 关键词列表，用于验证用户上传的视频是否与任务相关
  - Bot 会检查用户提交的视频标题/描述是否包含这些关键词
  - 至少匹配 30% 的关键词才算验证通过

---

## 2️⃣ 下架任务

将任务状态设置为 `inactive`，用户将不再看到此任务。

### 请求

```http
PUT /api/tasks/{task_id}
Content-Type: application/json
X-API-Key: x2c_admin_secret_key_2024
```

### Path Parameters

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 是 | 任务 ID |

### 请求参数

```json
{
  "status": "inactive"
}
```

### 请求示例

```bash
curl -X PUT "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive"
  }'
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "title": "养母胜过生母 第15集",
    "status": "inactive"
  }
}
```

### 重新上架

如需重新上架任务，将 `status` 设置为 `"active"` 即可。

```bash
curl -X PUT "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "active"
  }'
```

---

## 3️⃣ 管理任务（查看成功分发次数）

获取任务的详细信息和统计数据，包括成功分发次数。

### 请求

```http
GET /api/tasks/{task_id}
X-API-Key: x2c_admin_secret_key_2024
```

### Path Parameters

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | integer | 是 | 任务 ID |

### 请求示例

```bash
curl -X GET "https://your-app.railway.app/api/tasks/5" \
  -H "X-API-Key: x2c_admin_secret_key_2024"
```

### 响应示例

```json
{
  "success": true,
  "data": {
    "task_id": 5,
    "video_title": "养母胜过生母 第15集",
    "video_url": "https://example.com/drama/episode15.mp4",
    "task_template": "分享短剧《养母胜过生母》第15集精彩片段",
    "keywords_template": "养母,胜过,生母,第15集",
    "node_power_reward": 10,
    "platform_requirements": "TikTok,YouTube,Instagram",
    "status": "active",
    "created_at": "2024-11-25T16:00:00",
    "stats": {
      "total_submissions": 156,
      "successful_distributions": 142,
      "unique_users": 138
    }
  }
}
```

### 统计字段说明

| 字段 | 说明 |
|------|------|
| `total_submissions` | 总提交次数（包括验证失败的） |
| `successful_distributions` | **成功分发次数**（验证通过的提交数） |
| `unique_users` | 独立用户数 |

**成功分发次数** = 用户成功提交并通过验证的次数，代表任务的实际完成量。

---

## 📊 完整工作流程示例

### 场景：创建任务 → 查看统计 → 下架任务

```bash
# ========================================
# 步骤 1：创建任务
# ========================================
curl -X POST "https://your-app.railway.app/api/tasks" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "video_title": "重生之我在古代当皇帝 第8集",
    "video_url": "https://example.com/drama/emperor_ep8.mp4",
    "task_template": "分享短剧《重生之我在古代当皇帝》第8集，主角开启逆袭之路",
    "keywords_template": "重生,古代,皇帝,第8集",
    "node_power_reward": 12,
    "status": "active"
  }'

# 响应：
# {
#   "success": true,
#   "data": {
#     "task_id": 10,
#     "title": "重生之我在古代当皇帝 第8集",
#     "created_at": "2024-11-25T18:00:00"
#   }
# }

# ========================================
# 步骤 2：查看任务统计（等待一段时间后）
# ========================================
curl -X GET "https://your-app.railway.app/api/tasks/10" \
  -H "X-API-Key: x2c_admin_secret_key_2024"

# 响应：
# {
#   "success": true,
#   "data": {
#     "task_id": 10,
#     "video_title": "重生之我在古代当皇帝 第8集",
#     "stats": {
#       "total_submissions": 95,
#       "successful_distributions": 89,
#       "unique_users": 85
#     }
#   }
# }

# ========================================
# 步骤 3：下架任务
# ========================================
curl -X PUT "https://your-app.railway.app/api/tasks/10" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "inactive"
  }'

# 响应：
# {
#   "success": true,
#   "data": {
#     "task_id": 10,
#     "status": "inactive"
#   }
# }
```

---

## 🔄 任务验证流程

当用户提交视频链接后，Bot 会自动验证：

1. **访问用户提交的链接**
2. **提取视频标题和描述**
3. **检查是否包含关键词**
   - 从 `keywords_template` 中提取关键词列表
   - 计算匹配率：匹配的关键词数 / 总关键词数
   - 匹配率 ≥ 30% 才算验证通过
4. **验证通过**
   - 发放奖励
   - 计入成功分发次数
5. **验证失败**
   - 提示用户重新提交
   - 不计入成功分发次数

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
  "error": "video_title is required"
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
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 必须配置 |

---

## 📝 注意事项

1. **API Key 安全**：请妥善保管 API Key，不要在客户端代码中暴露

2. **任务状态**：
   - `active`：任务激活，用户可以看到并提交
   - `inactive`：任务停用，用户看不到

3. **关键词模板**：
   - 使用逗号分隔多个关键词
   - 关键词越精确，验证越准确
   - 建议包含短剧名称、集数等关键信息

4. **成功分发次数**：
   - 只统计验证通过的提交
   - 代表任务的实际完成量
   - 可用于计算任务效果和用户活跃度

5. **时区**：所有时间戳使用 UTC 时区，格式为 ISO 8601

---

## 📞 技术支持

如有问题或建议，请联系开发团队。

**API 版本：** v1.0.0  
**最后更新：** 2024-11-25
