# 每日汇总数据回传功能使用文档

## 📋 概述

每日汇总数据回传功能用于定期扫描已完成的任务，聚合每日统计数据并回传到X2C平台，用于分账结算。

**核心特性**：
- ✅ 自动聚合每日任务完成数据
- ✅ 支持YouTube、TikTok、抖音三个平台
- ✅ 自动去重统计账号数
- ✅ 实时抓取视频数据（如有需要）
- ✅ 自动回传到X2C平台
- ✅ 支持手动和定时执行

---

## 🗂️ 数据库变更

### 1. users表新增字段

```sql
ALTER TABLE users ADD COLUMN agent_node VARCHAR(255);
```

**用途**：标识用户所属的代理节点，用于X2C平台分账。

### 2. 新增task_daily_stats表

```sql
CREATE TABLE task_daily_stats (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL,
    project_id VARCHAR(255),
    external_task_id INTEGER,
    stats_date DATE NOT NULL,
    
    -- 总体统计
    total_account_count INTEGER DEFAULT 0,
    total_completion_count INTEGER DEFAULT 0,
    
    -- YouTube 统计
    yt_account_count INTEGER DEFAULT 0,
    yt_view_count BIGINT DEFAULT 0,
    yt_like_count BIGINT DEFAULT 0,
    yt_comment_count BIGINT DEFAULT 0,
    
    -- TikTok 统计
    tt_account_count INTEGER DEFAULT 0,
    tt_view_count BIGINT DEFAULT 0,
    tt_like_count BIGINT DEFAULT 0,
    tt_comment_count BIGINT DEFAULT 0,
    
    -- 抖音 统计
    dy_account_count INTEGER DEFAULT 0,
    dy_view_count BIGINT DEFAULT 0,
    dy_like_count BIGINT DEFAULT 0,
    dy_comment_count BIGINT DEFAULT 0,
    dy_share_count BIGINT DEFAULT 0,
    dy_collect_count BIGINT DEFAULT 0,
    
    -- 回传状态
    webhook_sent BOOLEAN DEFAULT FALSE,
    webhook_sent_at TIMESTAMP,
    webhook_response TEXT,
    webhook_retry_count INTEGER DEFAULT 0,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(task_id, stats_date)
);
```

**用途**：存储每个任务每天的汇总统计数据。

---

## 🚀 使用方法

### 方法1：手动执行

#### 扫描昨天的数据（默认）

```bash
cd /home/ubuntu/telegram-bot-dramarelay
python3 daily_stats_scanner.py
```

#### 扫描指定日期的数据

```bash
python3 daily_stats_scanner.py 2024-12-09
```

### 方法2：使用Shell脚本

```bash
./run_daily_stats.sh
```

### 方法3：设置定时任务（推荐）

#### 使用cron定时执行

编辑crontab：

```bash
crontab -e
```

添加定时任务（每天凌晨2点执行）：

```cron
0 2 * * * /home/ubuntu/telegram-bot-dramarelay/run_daily_stats.sh >> /home/ubuntu/telegram-bot-dramarelay/daily_stats.log 2>&1
```

**说明**：
- `0 2 * * *`：每天凌晨2点执行
- `>> daily_stats.log 2>&1`：将输出追加到日志文件

---

## 📊 工作流程

### 1. 扫描阶段

```
扫描器启动
    ↓
查询目标日期有完成记录的任务
    ↓
遍历每个任务
```

### 2. 聚合阶段

```
获取任务在目标日期的所有完成记录
    ↓
按平台统计账号数（去重）
    ↓
提取或抓取视频数据
    ↓
聚合统计数据
```

### 3. 保存阶段

```
保存到 task_daily_stats 表
    ↓
使用 UPSERT 避免重复
```

### 4. 回传阶段

```
检查任务是否配置 callback_url
    ↓
构建回调数据（只包含有数据的字段）
    ↓
发送 Webhook 到 X2C 平台
    ↓
更新回传状态
```

---

## 📤 回传数据格式

### 完整示例（包含所有平台）

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
      "tt_view_count": 3500,
      "tt_like_count": 150,
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

### 只有YouTube的示例

```json
{
  "site_name": "DramaRelayBot",
  "event": "task.daily_stats",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 5,
      "yt_account_count": 5,
      "yt_view_count": 1200,
      "yt_like_count": 80
    }
  ]
}
```

**重要说明**：
- 只包含**有数据的字段**
- 如果某个平台没有完成记录，不会包含该平台的字段
- 如果某个数据为0，不会包含该字段

---

## 🔧 配置说明

### 环境变量

需要在 `.env` 文件或环境变量中配置：

```bash
# 数据库连接
DATABASE_URL=postgresql://user:password@host:port/database

# TikHub API Key（用于抖音）
TIKHUB_API_KEY=your_tikhub_api_key

# YouTube Data API v3 Key
YOUTUBE_API_KEY=your_youtube_api_key
```

### 已测试的API Keys

```bash
TIKHUB_API_KEY=0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA==
YOUTUBE_API_KEY=AIzaSyByw_ZPNgSCxkkvHCzmHx8R0wZ_8bc0Yi0
```

---

## 📝 代码结构

### 核心文件

```
telegram-bot-dramarelay/
├── daily_stats_scanner.py        # 每日统计扫描器（核心）
├── video_stats_fetcher.py        # 视频数据抓取器
├── webhook_notifier.py           # Webhook 发送模块（已更新支持抖音）
├── auto_migrate.py               # 数据库自动迁移（已更新）
├── run_daily_stats.sh            # 定时任务脚本
└── migrations/
    └── 006_add_daily_stats_system.sql  # 数据库变更SQL
```

### 关键类和函数

#### DailyStatsScanner类

```python
from daily_stats_scanner import DailyStatsScanner

scanner = DailyStatsScanner()
result = await scanner.scan_and_aggregate(target_date)
```

**方法**：
- `scan_and_aggregate(target_date)`: 扫描并聚合指定日期的数据
- `_aggregate_task_stats(cur, task_id, target_date)`: 聚合单个任务的统计
- `_save_daily_stats(...)`: 保存统计数据到数据库
- `_send_daily_webhook(...)`: 发送每日汇总Webhook

#### 便捷函数

```python
from daily_stats_scanner import run_daily_scan

# 扫描昨天的数据
result = await run_daily_scan()

# 扫描指定日期
result = await run_daily_scan(date(2024, 12, 9))
```

---

## 🧪 测试验证

### 1. 测试数据库迁移

```bash
cd /home/ubuntu/telegram-bot-dramarelay
python3 auto_migrate.py
```

**预期输出**：
```
✅ Column 'agent_node' added successfully
✅ task_daily_stats table created successfully
✅ All migrations completed successfully
```

### 2. 测试手动扫描

```bash
# 扫描昨天的数据
python3 daily_stats_scanner.py

# 扫描指定日期
python3 daily_stats_scanner.py 2024-12-09
```

**预期输出**：
```
======================================================================
📊 每日统计扫描结果
======================================================================
日期: 2024-12-09
处理任务数: 3
创建统计数: 3
发送Webhook数: 2
======================================================================
```

### 3. 测试Webhook接收

使用 [webhook.site](https://webhook.site) 创建临时回调URL进行测试：

1. 访问 https://webhook.site 获取临时URL
2. 在管理后台创建测试任务，设置callback_url为临时URL
3. 完成任务提交
4. 运行扫描器
5. 在webhook.site查看接收到的数据

---

## 🔍 数据统计逻辑

### 账号数统计（去重）

```python
# 总账号数：按 user_id 去重
total_account_count = len(set(user_ids))

# 平台账号数：按 user_id + platform 去重
yt_account_count = len({user_id for user_id, platform in completions if platform == 'youtube'})
```

### 数据来源优先级

1. **优先使用已保存的数据**：从 `user_tasks.verification_details` 提取
2. **实时抓取**：如果没有保存的数据，使用 `VideoStatsFetcher` 实时抓取
3. **聚合计算**：将所有完成记录的数据累加

### 平台识别

```python
platform_lower = platform.lower()

if 'youtube' in platform_lower or 'yt' in platform_lower:
    # YouTube 统计
elif 'tiktok' in platform_lower or 'tt' in platform_lower:
    # TikTok 统计
elif 'douyin' in platform_lower or 'dy' in platform_lower:
    # 抖音 统计
```

---

## 💡 最佳实践

### 1. 定时执行时间建议

- **推荐时间**：每天凌晨2-4点
- **原因**：
  - 避开用户活跃时段
  - 确保前一天的数据已完整
  - 减少数据库负载

### 2. 日志管理

```bash
# 查看最近的日志
tail -f /home/ubuntu/telegram-bot-dramarelay/daily_stats.log

# 清理旧日志（保留最近30天）
find /home/ubuntu/telegram-bot-dramarelay -name "daily_stats.log" -mtime +30 -delete
```

### 3. 错误处理

- 扫描器会自动跳过失败的任务，继续处理其他任务
- 所有错误都会记录在返回结果的 `errors` 数组中
- Webhook发送失败不会影响统计数据的保存

### 4. 重复执行

- 使用 `UPSERT` 机制，重复执行不会产生重复数据
- 可以安全地重新扫描历史日期

---

## 🐛 常见问题

### Q1: 扫描器运行后没有创建统计？

**A**: 检查以下几点：
1. 目标日期是否有完成记录？
2. 任务状态是否为 `active`？
3. 查看日志中的错误信息

### Q2: Webhook没有发送？

**A**: 检查：
1. 任务是否配置了 `callback_url`？
2. `callback_url` 是否可访问？
3. 查看 `task_daily_stats` 表的 `webhook_sent` 字段

### Q3: 数据不准确？

**A**: 可能原因：
1. `verification_details` 中没有保存数据
2. 视频链接已失效，无法实时抓取
3. API配额不足（YouTube API）

### Q4: 如何重新扫描某一天的数据？

**A**: 直接指定日期重新运行：

```bash
python3 daily_stats_scanner.py 2024-12-09
```

数据会自动更新（UPSERT）。

---

## 📞 技术支持

### 相关文档

- [X2C平台对接文档](./X2C平台对接文档_最终版.md)
- [VideoStatsFetcher使用文档](./VIDEO_STATS_FETCHER_README.md)
- [HANDOVER文档](./HANDOVER.md)

### 调试命令

```bash
# 查看数据库中的每日统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats ORDER BY stats_date DESC LIMIT 10;"

# 查看某个任务的统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats WHERE task_id = 42;"

# 查看未回传的统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats WHERE webhook_sent = FALSE;"
```

---

## 📄 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2024-12-10 | 初始版本，支持YouTube、TikTok、抖音三个平台 |

---

**文档版本**: 1.0  
**最后更新**: 2024-12-10  
**维护者**: DramaRelay Bot Team
