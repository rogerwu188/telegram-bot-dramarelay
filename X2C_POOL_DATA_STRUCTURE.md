# X2C Pool 平台数据回传结构文档

## 📋 文档信息

- **版本**: 2.0（支持抖音平台）
- **更新日期**: 2024-12-10
- **适用场景**: DramaRelay Bot → X2C Pool 平台数据回传
- **回传类型**: 
  - 实时回传（用户完成任务时）
  - 每日汇总回传（定时任务）

---

## 🔄 回传触发机制

### 1. 实时回传（Immediate Callback）

**触发时机**: 用户完成任务并通过验证后，立即发送

**特点**:
- ✅ 实时性强，用户完成即回传
- ✅ 单次完成数据，account_count = 1
- ✅ 包含当次完成的视频数据（如有）

### 2. 每日汇总回传（Daily Summary Callback）

**触发时机**: 每天凌晨定时扫描前一天的数据

**特点**:
- ✅ 聚合统计，account_count = 当天完成的不重复用户数
- ✅ 累加所有视频数据
- ✅ 按平台分别统计

---

## 📤 数据结构定义

### 通用字段

所有回传数据都包含以下基础结构：

```json
{
  "site_name": "DramaRelayBot",
  "event": "task.completed" | "task.daily_stats",
  "stats": [...]
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `site_name` | String | 是 | 固定值 "DramaRelayBot" |
| `event` | String | 是 | 事件类型：<br>- `task.completed`: 实时完成<br>- `task.daily_stats`: 每日汇总 |
| `stats` | Array | 是 | 统计数据数组 |

---

## 📊 stats数组元素结构

### 基础字段（所有回传都包含）

```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": 42,
  "duration": 30,
  "account_count": 1
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `project_id` | String (UUID) | 否 | X2C项目ID，与下发时一致 |
| `task_id` | Integer | 否 | X2C任务ID（external_task_id），与下发时一致 |
| `duration` | Integer | 是 | 任务时长（天） |
| `account_count` | Integer | 是 | 完成账号数<br>- 实时回传: 固定为1<br>- 每日汇总: 当天不重复用户数 |

### YouTube平台字段（可选）

**仅当有YouTube完成记录时包含**

```json
{
  "yt_account_count": 5,
  "yt_view_count": 1200,
  "yt_like_count": 80,
  "yt_comment_count": 15
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `yt_account_count` | Integer | 条件必填* | YouTube完成账号数 |
| `yt_view_count` | Integer | 可选 | YouTube播放量（仅有数据时包含） |
| `yt_like_count` | Integer | 可选 | YouTube点赞数（仅有数据时包含） |
| `yt_comment_count` | Integer | 可选 | YouTube评论数（仅有数据时包含） |

*条件必填：如果有YouTube完成记录，必须包含此字段

### TikTok平台字段（可选）

**仅当有TikTok完成记录时包含**

```json
{
  "tt_account_count": 6,
  "tt_view_count": 3500,
  "tt_like_count": 150,
  "tt_comment_count": 28
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `tt_account_count` | Integer | 条件必填* | TikTok完成账号数 |
| `tt_view_count` | Integer | 可选 | TikTok播放量（仅有数据时包含） |
| `tt_like_count` | Integer | 可选 | TikTok点赞数（仅有数据时包含） |
| `tt_comment_count` | Integer | 可选 | TikTok评论数（仅有数据时包含） |

*条件必填：如果有TikTok完成记录，必须包含此字段

### 抖音平台字段（可选）⭐ 新增

**仅当有抖音完成记录时包含**

```json
{
  "dy_account_count": 4,
  "dy_view_count": 8000,
  "dy_like_count": 320,
  "dy_comment_count": 45,
  "dy_share_count": 28,
  "dy_collect_count": 62
}
```

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `dy_account_count` | Integer | 条件必填* | 抖音完成账号数 |
| `dy_view_count` | Integer | 可选 | 抖音播放量（仅有数据时包含） |
| `dy_like_count` | Integer | 可选 | 抖音点赞数（仅有数据时包含） |
| `dy_comment_count` | Integer | 可选 | 抖音评论数（仅有数据时包含） |
| `dy_share_count` | Integer | 可选 | 抖音分享数（仅有数据时包含）⭐ |
| `dy_collect_count` | Integer | 可选 | 抖音收藏数（仅有数据时包含）⭐ |

*条件必填：如果有抖音完成记录，必须包含此字段

**抖音特有字段**:
- `dy_share_count`: 分享数（抖音独有）
- `dy_collect_count`: 收藏数（抖音独有）

---

## 📝 完整示例

### 示例1：实时回传 - YouTube平台（有数据）

```json
{
  "site_name": "DramaRelayBot",
  "event": "task.completed",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 1,
      "yt_account_count": 1,
      "yt_view_count": 150,
      "yt_like_count": 20
    }
  ]
}
```

### 示例2：实时回传 - 抖音平台（完整数据）⭐

```json
{
  "site_name": "DramaRelayBot",
  "event": "task.completed",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 1,
      "dy_account_count": 1,
      "dy_view_count": 2500,
      "dy_like_count": 120,
      "dy_comment_count": 15,
      "dy_share_count": 8,
      "dy_collect_count": 22
    }
  ]
}
```

### 示例3：每日汇总 - 多平台混合

```json
{
  "site_name": "DramaRelayBot",
  "event": "task.daily_stats",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 15,
      "yt_account_count": 5,
      "yt_view_count": 1200,
      "yt_like_count": 80,
      "tt_account_count": 6,
      "dy_account_count": 4,
      "dy_view_count": 8000,
      "dy_like_count": 320,
      "dy_comment_count": 45,
      "dy_share_count": 28,
      "dy_collect_count": 62
    }
  ]
}
```

---

## 🔐 安全认证

### Webhook签名

所有回传请求都包含HMAC-SHA256签名：

**请求头**:
```
Content-Type: application/json
X-Webhook-Signature: sha256=<HMAC-SHA256签名>
X-Webhook-Event: task.completed | task.daily_stats
X-Webhook-Timestamp: <Unix时间戳>
```

---

## 🆕 版本更新说明

### v2.0（2024-12-10）

**新增功能**:
1. ✅ 支持抖音平台（`dy_*` 字段）
2. ✅ 抖音特有字段：`dy_share_count`、`dy_collect_count`
3. ✅ 每日汇总回传功能
4. ✅ 新增 `event` 字段区分回传类型

**新增字段**:
- `dy_account_count`: 抖音账号数
- `dy_view_count`: 抖音播放量
- `dy_like_count`: 抖音点赞数
- `dy_comment_count`: 抖音评论数
- `dy_share_count`: 抖音分享数 ⭐
- `dy_collect_count`: 抖音收藏数 ⭐

---

**文档版本**: 2.0  
**最后更新**: 2024-12-10  
**维护者**: DramaRelay Bot Team
