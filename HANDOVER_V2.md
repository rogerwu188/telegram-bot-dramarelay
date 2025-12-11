# TG Bot 项目交接文档

## 📅 项目状态 (2024-12-10 更新)

### 1. 核心功能
- **Bot 基础功能**: 任务分发、链接验证、用户管理 (已上线)
- **管理后台**: https://worker-production-d960.up.railway.app/admin (API Key: `x2c_admin_secret_key_2024`)
- **多平台支持**: 
  - YouTube (API Key 已配置)
  - TikTok (oEmbed)
  - 抖音 (TikHub API 已集成)

### 2. ✅ 已完成的开发任务

**每日汇总数据回传功能**已开发完成，包括：

#### 2.1 数据库变更
- ✅ `users` 表增加 `agent_node` 字段
- ✅ 新增 `task_daily_stats` 表（存储每日汇总统计）
- ✅ 更新 `auto_migrate.py` 支持自动迁移

#### 2.2 代码开发
- ✅ 完善 `VideoStatsFetcher` 支持抖音平台
- ✅ 开发 `DailyStatsScanner` 每日扫描器
- ✅ 更新 `webhook_notifier.py` 支持抖音字段（`dy_*`）
- ✅ 创建定时任务脚本 `run_daily_stats.sh`
- ✅ 编写完整的使用文档 `DAILY_STATS_README.md`

#### 2.3 新增文件
```
telegram-bot-dramarelay/
├── daily_stats_scanner.py              # 每日统计扫描器（新）
├── run_daily_stats.sh                  # 定时任务脚本（新）
├── test_daily_stats.py                 # 测试脚本（新）
├── DAILY_STATS_README.md               # 使用文档（新）
├── migrations/
│   └── 006_add_daily_stats_system.sql  # 数据库变更SQL（新）
├── auto_migrate.py                     # 已更新
├── webhook_notifier.py                 # 已更新（支持抖音）
└── video_stats_fetcher.py              # 已完善（支持抖音）
```

### 3. 关键文件说明
- `DAILY_STATS_README.md`: **每日汇总功能完整使用文档**（必读）
- `daily_stats_scanner.py`: 每日统计扫描器核心代码
- `video_stats_fetcher.py`: 统一的视频数据抓取工具（支持YouTube、TikTok、抖音）
- `webhook_notifier.py`: Webhook 发送逻辑（已支持抖音字段）
- `admin_api.py`: 管理后台 API

### 4. 环境变量 (参考)
```bash
DATABASE_URL=postgresql://...
API_KEY=x2c_admin_secret_key_2024
TIKHUB_API_KEY=0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA==
YOUTUBE_API_KEY=AIzaSyByw_ZPNgSCxkkvHCzmHx8R0wZ_8bc0Yi0
```

### 5. 如何部署和使用

#### 5.1 部署数据库变更

**方法1：自动迁移（推荐）**
```bash
cd /home/ubuntu/telegram-bot-dramarelay
python3 auto_migrate.py
```

**方法2：手动执行SQL**
```bash
psql $DATABASE_URL < migrations/006_add_daily_stats_system.sql
```

#### 5.2 测试功能

```bash
# 测试扫描器
python3 test_daily_stats.py

# 手动扫描昨天的数据
python3 daily_stats_scanner.py

# 扫描指定日期
python3 daily_stats_scanner.py 2024-12-09
```

#### 5.3 设置定时任务

编辑crontab：
```bash
crontab -e
```

添加定时任务（每天凌晨2点执行）：
```cron
0 2 * * * /home/ubuntu/telegram-bot-dramarelay/run_daily_stats.sh >> /home/ubuntu/telegram-bot-dramarelay/daily_stats.log 2>&1
```

### 6. 每日汇总数据格式

#### 完整示例（包含所有平台）
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

**重要说明**：
- 只包含**有数据的字段**
- 如果某个平台没有完成记录，不会包含该平台的字段
- 如果某个数据为0，不会包含该字段

### 7. 工作流程

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
    ├─ 保存到 task_daily_stats 表
    └─ 如果配置了 callback_url，发送 Webhook
    ↓
记录日志到 daily_stats.log
```

### 8. 技术要点

#### 8.1 数据聚合逻辑
- **账号数去重**：按 `user_id` 去重统计
- **平台账号数**：按 `user_id` + `platform` 去重
- **数据来源优先级**：
  1. 优先使用 `verification_details` 中已保存的数据
  2. 如果没有，使用 `VideoStatsFetcher` 实时抓取
  3. 将所有完成记录的数据累加

#### 8.2 UPSERT机制
使用 `INSERT ... ON CONFLICT ... DO UPDATE` 实现：
- 重复执行不会产生重复数据
- 可以安全地重新扫描历史日期

#### 8.3 错误处理
- 单个任务失败不影响其他任务
- 所有错误记录在返回结果的 `errors` 数组
- Webhook发送失败不影响统计数据保存

### 9. 监控和调试

#### 查看日志
```bash
tail -f /home/ubuntu/telegram-bot-dramarelay/daily_stats.log
```

#### 查询数据库
```bash
# 查看最近的每日统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats ORDER BY stats_date DESC LIMIT 10;"

# 查看未回传的统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats WHERE webhook_sent = FALSE;"

# 查看某个任务的统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats WHERE task_id = 42;"
```

### 10. 下一步建议

#### 10.1 立即执行
1. ✅ 部署数据库变更（运行 `auto_migrate.py`）
2. ✅ 测试扫描功能（运行 `test_daily_stats.py`）
3. ✅ 设置定时任务（配置 crontab）

#### 10.2 可选优化
- [ ] 添加监控告警（扫描失败时发送通知）
- [ ] 优化视频数据抓取（添加缓存机制）
- [ ] 支持更多平台（Instagram、Facebook等）
- [ ] 添加数据可视化（管理后台展示每日统计）

### 11. 相关文档

- **每日汇总功能**: `DAILY_STATS_README.md` ⭐
- **X2C平台对接**: `X2C平台对接文档_最终版.md`
- **视频数据抓取**: `VIDEO_STATS_FETCHER_README.md`
- **管理后台**: `ADMIN_README.md`

### 12. 联系方式

如有问题，请查看：
1. `DAILY_STATS_README.md` 中的常见问题部分
2. 日志文件 `daily_stats.log`
3. GitHub Issues

---

## 📝 更新日志

| 日期 | 版本 | 说明 |
|------|------|------|
| 2024-12-10 | 2.0 | ✅ 完成每日汇总数据回传功能开发 |
| 2024-12-10 | 1.0 | 初始版本 |

---

**文档版本**: 2.0  
**最后更新**: 2024-12-10  
**维护者**: DramaRelay Bot Team
