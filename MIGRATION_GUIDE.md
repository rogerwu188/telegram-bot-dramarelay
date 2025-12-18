# Telegram Bot DramaRelay - 项目迁移指南

## 项目概述

这是一个Telegram机器人项目，用于短剧分发任务管理。主要功能包括：
- 接收X2C平台的任务分发
- 管理用户任务分配和提交
- 收集用户提交的视频链接（TikTok/YouTube等）
- 回调通知X2C平台任务完成情况
- 管理后台监控和数据统计

## 技术栈

### 后端
- **Python 3.11+**
- **python-telegram-bot**: Telegram Bot API框架
- **Flask**: Web框架（API服务和管理后台）
- **PostgreSQL**: 数据库
- **psycopg2**: PostgreSQL数据库驱动
- **APScheduler**: 定时任务调度

### 部署平台
- **Railway**: 当前部署平台
- **GitHub**: 代码仓库（自动部署）

## 项目结构

```
telegram-bot-dramarelay/
├── main.py                 # 主入口（启动bot和API服务）
├── api_server.py          # API服务器（接收任务、webhook回调）
├── admin_api.py           # 管理后台API
├── bot.py                 # Telegram Bot核心逻辑
├── database.py            # 数据库初始化和连接
├── broadcaster.py         # 定时回传任务
├── video_stats_fetcher.py # 视频播放量统计
├── requirements.txt       # Python依赖
├── Procfile              # Railway部署配置
├── railway.json          # Railway服务配置
├── templates/
│   └── admin.html        # 管理后台页面
└── 各种README.md         # 功能文档
```

## 核心文件说明

### 1. main.py
项目启动入口，负责：
- 初始化数据库
- 启动Telegram Bot
- 启动API服务器（Flask）
- 启动定时任务（broadcaster）

### 2. api_server.py
API服务器，提供以下端点：
- `POST /api/tasks` - 接收X2C平台的任务分发
- `GET /api/admin` - 管理后台页面
- `GET /api/logs/*` - 各种日志查询API
- `POST /api/broadcast` - 手动触发回传

### 3. admin_api.py
管理后台API逻辑，提供：
- Webhook回调日志查询
- 任务接收日志查询
- 回传错误日志查询
- 用户提交链接查询

### 4. bot.py
Telegram Bot核心功能：
- 用户注册和认证
- 任务分配和接收
- 视频链接提交和验证
- TikTok/YouTube链接解析

### 5. broadcaster.py
定时回传任务：
- 每3分钟自动回传已完成任务
- 支持手动触发回传
- 失败重试机制

### 6. database.py
数据库管理：
- 数据库连接池
- 表结构初始化
- 数据库迁移

## 数据库表结构

### drama_tasks
任务表，存储从X2C平台接收的任务
```sql
- task_id: 主键
- external_task_id: X2C平台的任务ID
- project_id: 项目ID
- title: 任务标题
- video_url: 原片视频链接
- category: 剧集类型
- platform: 目标平台
- reward: 奖励金额
- created_at: 创建时间
```

### user_tasks
用户任务表，存储用户领取和提交的任务
```sql
- id: 主键
- user_id: Telegram用户ID
- task_id: 关联drama_tasks
- status: 状态（in_progress/submitted）
- platform: 提交平台
- submission_link: 用户提交的视频链接
- submitted_at: 提交时间
```

### webhook_logs
Webhook回调日志
```sql
- id: 主键
- task_id: 关联drama_tasks
- callback_url: 回调URL
- callback_status: 回调状态（success/failed）
- payload: 回调数据（JSONB）
- created_at: 创建时间
```

## 环境变量配置

需要在部署平台配置以下环境变量：

```bash
# Telegram Bot配置
BOT_TOKEN=your_telegram_bot_token
ADMIN_USER_ID=your_telegram_user_id

# 数据库配置
DATABASE_URL=postgresql://user:password@host:port/database

# API配置
API_KEY=your_api_key_for_x2c_platform
WEBHOOK_SECRET=your_webhook_secret

# 回调配置
CALLBACK_URL=https://your-x2c-platform.com/callback
```

## 部署步骤

### 方式1: Railway部署（当前方式）

1. Fork GitHub仓库
2. 在Railway创建新项目
3. 连接GitHub仓库
4. 配置环境变量
5. Railway自动部署

### 方式2: 其他平台部署

1. 解压项目文件
2. 安装依赖：`pip install -r requirements.txt`
3. 配置环境变量
4. 初始化数据库：`python database.py`
5. 启动服务：`python main.py`

## API接口文档

### 接收任务
```
POST /api/tasks
Content-Type: application/json
X-API-Key: your_api_key

{
  "tasks": [
    {
      "task_id": 1,
      "project_id": "uuid",
      "title": "任务标题",
      "video_url": "https://...",
      "category": "romance",
      "platform": "TikTok",
      "reward": 10.0
    }
  ]
}
```

### 查询Webhook日志
```
GET /api/logs/webhooks?hours=24&limit=50
```

### 手动触发回传
```
POST /api/broadcast
```

## 已知问题和待优化项

1. **播放量统计**：目前播放量显示为0，需要X2C平台在回调时提供view_count数据
2. **视频链接验证**：TikTok链接验证依赖oembed API，可能受限
3. **错误重试**：回调失败时的重试机制可以优化

## 最近更新

### 2025-12-11
- ✅ 修复了webhook日志查询中video_url字段缺失的问题
- ✅ 修正了user_tasks表字段名（submission_link）
- ✅ 新增了"用户分发链接"列，显示所有用户提交的链接
- ✅ 优化了管理后台的数据展示

## 联系方式

- GitHub仓库: https://github.com/rogerwu188/telegram-bot-dramarelay
- 当前部署: Railway (worker-production-d960.up.railway.app)

## 迁移到第三方AI编程平台建议

### 推荐平台
1. **Cursor**: 基于VSCode，支持AI辅助编程
2. **GitHub Copilot**: 代码补全和生成
3. **Replit**: 在线IDE，支持协作
4. **Windsurf**: AI原生IDE

### 迁移步骤
1. 解压`telegram-bot-dramarelay-export.tar.gz`
2. 在新平台导入项目文件夹
3. 安装Python 3.11+环境
4. 安装依赖：`pip install -r requirements.txt`
5. 配置环境变量（参考上方）
6. 连接PostgreSQL数据库
7. 运行`python database.py`初始化数据库
8. 运行`python main.py`启动服务

### 注意事项
- 确保新平台支持长期运行的进程（Bot需要持续运行）
- 需要公网访问能力（接收X2C平台的webhook）
- 建议使用与Railway类似的PaaS平台（如Heroku、Render等）

## 文件清单

项目包含127个文件，主要包括：
- Python源代码文件（.py）
- 配置文件（requirements.txt, Procfile, railway.json）
- 文档文件（各种README.md）
- 模板文件（templates/admin.html）

详细文件列表请查看`project-files-list.txt`
