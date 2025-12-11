# TG Bot 项目交接文档

## 📅 项目状态 (2024-12-10 更新 v3)

### 1. 核心功能
- **Bot 基础功能**: 任务分发、链接验证、用户管理 (已上线)
- **管理后台**: https://worker-production-d960.up.railway.app/admin (API Key: `x2c_admin_secret_key_2024`)
- **多平台支持**: 
  - YouTube (API Key 已配置)
  - TikTok (oEmbed)
  - 抖音 (TikHub API 已集成) ⭐

### 2. ✅ 已完成的开发任务

**每日汇总数据回传功能**已开发完成，包括：

#### 2.1 数据库变更
- ✅ `users` 表增加 `agent_node` 字段
- ✅ 新增 `task_daily_stats` 表（存储每日汇总统计）
- ✅ 更新 `auto_migrate.py` 支持自动迁移

#### 2.2 抖音平台支持 ⭐ 重要
- ✅ 完善 `VideoStatsFetcher` 支持抖音数据抓取
- ✅ 本地完整存储抖音数据（播放量、点赞数、评论数、分享数、收藏数）
- ✅ **抖音数据计入YouTube总量回传**（保持X2C Pool接口不变）
- ✅ 管理后台可查看抖音详细数据

#### 2.3 代码开发
- ✅ 开发 `DailyStatsScanner` 每日扫描器
- ✅ 更新 `webhook_notifier.py` 实时回传逻辑
- ✅ 创建定时任务脚本 `run_daily_stats.sh`
- ✅ 编写完整的使用文档

#### 2.4 新增文件
```
telegram-bot-dramarelay/
├── daily_stats_scanner.py              # 每日统计扫描器（新）
├── run_daily_stats.sh                  # 定时任务脚本（新）
├── test_daily_stats.py                 # 测试脚本（新）
├── DAILY_STATS_README.md               # 使用文档（新）
├── DOUYIN_DATA_HANDLING.md             # 抖音数据处理说明（新）⭐
├── migrations/
│   └── 006_add_daily_stats_system.sql  # 数据库变更SQL（新）
├── auto_migrate.py                     # 已更新
├── webhook_notifier.py                 # 已更新（抖音计入yt_*）
└── video_stats_fetcher.py              # 已完善（支持抖音）
```

### 3. 🎯 抖音数据处理策略 ⭐ 重要

#### 核心原则

**抖音数据只在本地展现，但计入回传总量**

#### 具体实现

1. **本地存储完整数据**
   - 所有抖音数据保存在 `user_tasks.verification_details`
   - 每日汇总保存在 `task_daily_stats` 表的 `dy_*` 字段
   - 包含：播放量、点赞数、评论数、分享数、收藏数

2. **回传计入总量**
   - 向X2C Pool回传时，抖音数据计入 `yt_*` 字段
   - `yt_account_count` = YouTube账号数 + 抖音账号数
   - `yt_view_count` = YouTube播放量 + 抖音播放量
   - `yt_like_count` = YouTube点赞数 + 抖音点赞数

3. **X2C Pool无需修改**
   - 保持现有数据结构不变
   - 无需增加 `dy_*` 字段
   - 接收逻辑保持不变

#### 回传数据示例

**实时回传**（用户在抖音完成任务）:
```json
{
  "site_name": "DramaRelayBot",
  "stats": [{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "duration": 30,
    "account_count": 1,
    "yt_account_count": 1,
    "yt_view_count": 2500,
    "yt_like_count": 120
  }]
}
```

**每日汇总**（混合平台）:
```json
{
  "site_name": "DramaRelayBot",
  "stats": [{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 42,
    "duration": 30,
    "account_count": 15,
    "yt_account_count": 9,      // YouTube 5 + 抖音 4
    "yt_view_count": 9200,       // YouTube 1200 + 抖音 8000
    "yt_like_count": 400,        // YouTube 80 + 抖音 320
    "tt_account_count": 6
  }]
}
```

### 4. 关键文件说明
- **DOUYIN_DATA_HANDLING.md** ⭐ - 抖音数据处理完整说明（必读）
- **DAILY_STATS_README.md** - 每日汇总功能完整使用文档
- `daily_stats_scanner.py` - 每日统计扫描器核心代码
- `video_stats_fetcher.py` - 统一的视频数据抓取工具（支持YouTube、TikTok、抖音）
- `webhook_notifier.py` - Webhook 发送逻辑（抖音计入yt_*）
- `admin_api.py` - 管理后台 API

### 5. 环境变量 (参考)
```bash
DATABASE_URL=postgresql://...
API_KEY=x2c_admin_secret_key_2024
TIKHUB_API_KEY=0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA==
YOUTUBE_API_KEY=AIzaSyByw_ZPNgSCxkkvHCzmHx8R0wZ_8bc0Yi0
```

### 6. 如何部署和使用

#### 6.1 部署数据库变更

**方法1：自动迁移（推荐）**
```bash
cd /home/ubuntu/telegram-bot-dramarelay
python3 auto_migrate.py
```

**方法2：手动执行SQL**
```bash
psql $DATABASE_URL < migrations/006_add_daily_stats_system.sql
```

#### 6.2 测试功能

```bash
# 测试扫描器
python3 test_daily_stats.py

# 手动扫描昨天的数据
python3 daily_stats_scanner.py

# 扫描指定日期
python3 daily_stats_scanner.py 2024-12-09
```

#### 6.3 设置定时任务

编辑crontab：
```bash
crontab -e
```

添加定时任务（每天凌晨2点执行）：
```cron
0 2 * * * /home/ubuntu/telegram-bot-dramarelay/run_daily_stats.sh >> /home/ubuntu/telegram-bot-dramarelay/daily_stats.log 2>&1
```

### 7. 回传数据格式（与X2C Pool一致）

#### 实时回传示例

```json
{
  "site_name": "DramaRelayBot",
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

#### 每日汇总示例

```json
{
  "site_name": "DramaRelayBot",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 15,
      "yt_account_count": 9,
      "yt_view_count": 9200,
      "yt_like_count": 400,
      "tt_account_count": 6
    }
  ]
}
```

**重要说明**:
- 只包含**有数据的字段**
- 如果某个平台没有完成记录，不会包含该平台的字段
- 如果某个数据为0，不会包含该字段
- **抖音数据已计入 `yt_*` 字段**

### 8. 工作流程

```
定时任务触发（每天凌晨2点）
    ↓
DailyStatsScanner 扫描昨天的数据
    ↓
查询所有在昨天有完成记录的任务
    ↓
遍历每个任务：
    ├─ 聚合该任务昨天的所有完成记录
    ├─ 按平台统计账号数（去重）
    ├─ 提取或实时抓取视频数据
    ├─ 保存到 task_daily_stats 表（完整数据）
    ├─ 抖音数据计入 yt_* 字段
    └─ 如果配置了 callback_url，发送 Webhook
    ↓
记录日志到 daily_stats.log
```

### 9. 技术要点

#### 9.1 抖音数据处理

**本地存储**（完整数据）:
```sql
-- task_daily_stats 表
dy_account_count: 4
dy_view_count: 8000
dy_like_count: 320
dy_comment_count: 45
dy_share_count: 28
dy_collect_count: 62
```

**回传数据**（计入yt_*）:
```json
{
  "yt_account_count": 9,    // YouTube 5 + 抖音 4
  "yt_view_count": 9200,     // YouTube 1200 + 抖音 8000
  "yt_like_count": 400       // YouTube 80 + 抖音 320
}
```

#### 9.2 UPSERT机制
使用 `INSERT ... ON CONFLICT ... DO UPDATE` 实现：
- 重复执行不会产生重复数据
- 可以安全地重新扫描历史日期

#### 9.3 错误处理
- 单个任务失败不影响其他任务
- 所有错误记录在返回结果的 `errors` 数组
- Webhook发送失败不影响统计数据保存

### 10. 监控和调试

#### 查看日志
```bash
tail -f /home/ubuntu/telegram-bot-dramarelay/daily_stats.log
```

#### 查询数据库
```bash
# 查看最近的每日统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats ORDER BY stats_date DESC LIMIT 10;"

# 查看抖音统计
psql $DATABASE_URL -c "SELECT task_id, stats_date, dy_account_count, dy_view_count, dy_like_count FROM task_daily_stats WHERE dy_account_count > 0 ORDER BY stats_date DESC LIMIT 10;"

# 查看某个任务的统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats WHERE task_id = 42;"
```

### 11. 下一步建议

#### 11.1 立即执行
1. ✅ 部署数据库变更（运行 `auto_migrate.py`）
2. ✅ 测试扫描功能（运行 `test_daily_stats.py`）
3. ✅ 设置定时任务（配置 crontab）

#### 11.2 可选优化
- [ ] 添加监控告警（扫描失败时发送通知）
- [ ] 优化视频数据抓取（添加缓存机制）
- [ ] 添加数据可视化（管理后台展示每日统计）
- [ ] 支持更多平台（Instagram、Facebook等）

### 12. 相关文档

- **抖音数据处理**: `DOUYIN_DATA_HANDLING.md` ⭐ 必读
- **每日汇总功能**: `DAILY_STATS_README.md` ⭐ 必读
- **X2C平台对接**: `X2C平台对接文档_最终版.md`
- **视频数据抓取**: `VIDEO_STATS_FETCHER_README.md`
- **管理后台**: `ADMIN_README.md`

### 13. 重要提醒 ⭐

#### 关于X2C Pool平台

**无需任何修改**！

- ✅ 数据结构保持不变
- ✅ 接收逻辑保持不变
- ✅ 数据库表保持不变
- ✅ 抖音数据已计入 `yt_*` 字段

#### 关于数据准确性

- ✅ 本地保存完整抖音数据
- ✅ 回传数据包含抖音贡献
- ✅ 管理后台可查看详细分平台数据
- ✅ 分账计算准确无误

---

## 📝 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2024-12-10 | 3.0 | ⭐ 调整抖音数据处理策略：计入yt_*总量回传 |
| 2024-12-10 | 2.0 | 完成每日汇总数据回传功能开发 |
| 2024-12-10 | 1.0 | 初始版本 |

---

**文档版本**: 3.0  
**最后更新**: 2024-12-10  
**维护者**: DramaRelay Bot Team
