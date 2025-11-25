# X2C DramaRelayBot - 全球短剧分发节点

这是 X2C 全球短剧分发节点的 Telegram Bot，用于管理短剧任务分发、用户提交、算力统计和空投管理。

## 功能特性

### 用户功能
- 🎬 **领取短剧任务** - 获取短剧视频素材和下载链接
- 📤 **提交链接** - 上传到社交平台后提交链接
- 📊 **我的算力** - 查看个人 Node Power 统计
- 🏆 **排行榜** - 全球用户算力排名
- 🎁 **空投状态** - 查看空投资格和预计奖励
- 💼 **绑定钱包** - 绑定 EVM 钱包地址
- ℹ️ **使用教程** - 详细的使用说明
- 🌐 **双语支持** - 中文/英文切换

### 管理员功能
- 添加新的短剧任务
- 管理任务状态
- 查看用户统计
- 管理空投快照

## 工作流程

1. **用户领取任务** → 选择喜欢的短剧任务
2. **下载视频** → 点击确认领取后下载视频文件
3. **上传到平台** → 将视频上传到 TikTok/YouTube/Instagram 等平台
4. **提交链接** → 回到 Bot 提交社交平台链接
5. **获得奖励** → 立即获得 Node Power 算力点数
6. **参与空投** → 累积 100+ Node Power 即可参与每月空投

## 技术栈

- **语言**: Python 3.11
- **框架**: python-telegram-bot 22.5
- **数据库**: PostgreSQL
- **部署**: Railway
- **依赖**: psycopg2-binary, APScheduler, python-dotenv

## 数据库结构

### users 表
- `user_id` - Telegram 用户 ID（主键）
- `username` - Telegram 用户名
- `first_name` - 用户名字
- `language` - 用户语言偏好（zh/en）
- `wallet_address` - EVM 钱包地址
- `total_node_power` - 总算力点数
- `completed_tasks` - 已完成任务数
- `created_at` - 创建时间
- `updated_at` - 更新时间

### drama_tasks 表
- `task_id` - 任务 ID（主键）
- `title` - 任务标题
- `description` - 任务描述
- `video_file_id` - Telegram 视频文件 ID
- `thumbnail_url` - 缩略图 URL
- `duration` - 视频时长（秒）
- `node_power_reward` - 算力奖励
- `platform_requirements` - 支持的平台
- `status` - 任务状态（active/inactive）
- `created_at` - 创建时间

### user_tasks 表
- `id` - 记录 ID（主键）
- `user_id` - 用户 ID
- `task_id` - 任务 ID
- `status` - 状态（in_progress/submitted/verified）
- `platform` - 上传平台
- `submission_link` - 提交的链接
- `submitted_at` - 提交时间
- `verified_at` - 验证时间
- `node_power_earned` - 获得的算力
- `created_at` - 创建时间

### airdrop_snapshots 表
- `id` - 记录 ID（主键）
- `round_number` - 空投轮次
- `user_id` - 用户 ID
- `node_power` - 算力快照
- `rank` - 排名
- `estimated_airdrop` - 预计空投数量
- `snapshot_date` - 快照时间

## 环境变量

```bash
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=comma_separated_admin_ids
DATABASE_URL=postgresql://user:password@host:port/database
```

## 部署到 Railway

### 方法 1: 通过 GitHub（推荐）

1. 将代码推送到 GitHub 仓库
2. 在 Railway 中连接 GitHub 仓库
3. Railway 会自动检测 Procfile 并部署
4. 添加 PostgreSQL 数据库服务
5. 设置环境变量（BOT_TOKEN, ADMIN_IDS）
6. 部署完成后 Bot 会自动启动

### 方法 2: 通过 Railway CLI

```bash
# 安装 Railway CLI
npm install -g @railway/cli

# 登录
railway login

# 初始化项目
railway init

# 添加 PostgreSQL
railway add

# 部署
railway up
```

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export BOT_TOKEN="your_bot_token"
export ADMIN_IDS="your_admin_id"
export DATABASE_URL="postgresql://localhost/x2c_bot"

# 运行 Bot
python3 bot.py
```

## 管理员命令

管理员可以通过以下方式添加任务：

1. 直接在数据库中插入任务记录
2. 通过管理面板（待开发）
3. 通过 Bot 命令（待开发）

### 手动添加任务示例

```sql
INSERT INTO drama_tasks (title, description, video_file_id, duration, node_power_reward, platform_requirements)
VALUES (
    '霸道总裁爱上我 EP01',
    '都市爱情短剧第一集，时长15秒',
    'BAACAgIAAxkBAAIBCGZxxx...',  -- Telegram 视频文件 ID
    15,
    10,
    'TikTok,YouTube,Instagram'
);
```

## 支持的平台

- TikTok
- YouTube
- Instagram
- Facebook
- Twitter/X
- 其他平台

## 链接验证规则

Bot 会验证提交的链接格式：

- **TikTok**: `https://tiktok.com/@username/video/123456`
- **YouTube**: `https://youtube.com/watch?v=xxxxx` 或 `https://youtu.be/xxxxx`
- **Instagram**: `https://instagram.com/p/xxxxx` 或 `https://instagram.com/reel/xxxxx`
- **其他平台**: 任何有效的 HTTPS URL

## 钱包地址验证

- 必须是有效的 EVM 钱包地址
- 格式: `0x` 开头 + 40 位十六进制字符
- 示例: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`

## 空投规则

- 最低要求: 100 Node Power
- 快照时间: 每月 1 号
- 奖励分配: 根据算力占比分配
- 钱包要求: 必须绑定有效的 EVM 钱包地址

## 常见问题

### Q: 如何获取视频的 file_id？
A: 将视频发送给 Bot，Bot 会返回 file_id，管理员可以使用这个 ID 创建任务。

### Q: 用户可以重复提交同一个任务吗？
A: 不可以，每个任务每个用户只能提交一次。

### Q: 链接提交后会立即验证吗？
A: 目前是自动通过，未来版本会添加人工审核功能。

### Q: 如何修改奖励点数？
A: 管理员可以在数据库中修改 `drama_tasks` 表的 `node_power_reward` 字段。

## 更新日志

### v2.0.0 (2025-11-25)
- ✅ 完全重写 Bot 功能
- ✅ 实现完整的短剧分发工作流
- ✅ 添加 Node Power 算力系统
- ✅ 添加排行榜功能
- ✅ 添加空投状态跟踪
- ✅ 添加钱包绑定功能
- ✅ 双语支持（中文/英文）
- ✅ 优化数据库结构

### v1.0.0 (2025-11-24)
- ✅ 基础文件上传功能
- ✅ Token 奖励系统

## 许可证

MIT License

## 联系方式

- Telegram: @DramaRelayBot
- GitHub: https://github.com/rogerwu188/telegram-bot-dramarelay

---

**X2C - 构建全球短剧分发网络**
