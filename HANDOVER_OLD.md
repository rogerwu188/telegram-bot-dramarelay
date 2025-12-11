# TG Bot 项目交接文档

## 📅 项目状态 (2025-12-10)

### 1. 核心功能
- **Bot 基础功能**: 任务分发、链接验证、用户管理 (已上线)
- **管理后台**: https://worker-production-d960.up.railway.app/admin (API Key: `x2c_admin_secret_key_2024`)
- **多平台支持**: 
  - YouTube (API Key 已配置)
  - TikTok (oEmbed)
  - 抖音 (TikHub API 已集成但需部署)

### 2. 正在进行的任务
我们正在开发**每日汇总数据回传功能**，用于 X2C 平台分账。

**待执行的变更**：
1. **数据库变更**:
   - `users` 表增加 `agent_node` 字段
   - 新增 `task_daily_stats` 表
2. **代码开发**:
   - 完善 `VideoStatsFetcher` (支持抖音)
   - 开发 `DailyStatsScanner` (每日扫描)
   - 更新 Webhook 回传逻辑 (增加 `dy_` 字段)

### 3. 关键文件说明
- `implementation_plan_v2.md`: 详细的实施方案（含数据库SQL和JSON结构）
- `video_stats_fetcher.py`: 统一的视频数据抓取工具
- `webhook_notifier.py`: Webhook 发送逻辑
- `admin_api.py`: 管理后台 API

### 4. 环境变量 (参考)
```bash
DATABASE_URL=postgresql://...
API_KEY=x2c_admin_secret_key_2024
TIKHUB_API_KEY=0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA==
YOUTUBE_API_KEY=AIzaSyByw_ZPNgSCxkkvHCzmHx8R0wZ_8bc0Yi0
```

### 5. 如何继续开发
1. 解压代码包: `unzip telegram-bot-dramarelay.zip`
2. 查看 `implementation_plan_v2.md` 了解设计方案
3. 执行数据库变更 (SQL在文档中)
4. 继续开发扫描器和回传逻辑
