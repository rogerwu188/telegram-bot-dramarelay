# TG Bot 数据库表结构文档

## 📊 数据库概览

系统使用 **PostgreSQL** 数据库，包含以下核心表：

1. **users** - TG Bot 用户管理表
2. **drama_tasks** - 短剧任务表
3. **user_tasks** - 用户任务关联表
4. **user_invitations** - 用户邀请关系表
5. **referral_rewards** - 推荐奖励记录表
6. **withdrawals** - 提现记录表
7. **airdrop_snapshots** - 空投快照表

---

## 1️⃣ users 表 - TG Bot 用户管理

**作用**: 管理所有使用 TG Bot 的用户信息

**表名**: `users`

### 表结构

```sql
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,                      -- Telegram 用户ID（主键）
    username VARCHAR(255),                           -- Telegram 用户名
    first_name VARCHAR(255),                         -- Telegram 名字
    display_name VARCHAR(255),                       -- 显示名称
    language VARCHAR(10) DEFAULT 'zh',               -- 语言偏好（zh/en）
    wallet_address VARCHAR(42),                      -- 钱包地址
    sol_wallet VARCHAR(44),                          -- Solana 钱包地址
    total_node_power INTEGER DEFAULT 0,              -- 总算力（X2C）
    completed_tasks INTEGER DEFAULT 0,               -- 完成任务数
    invited_by BIGINT,                               -- 邀请人ID
    invitation_reward_received BOOLEAN DEFAULT FALSE,-- 是否已领取邀请奖励
    invitation_reward_received_at TIMESTAMP,         -- 邀请奖励领取时间
    last_submission_time TIMESTAMP,                  -- 最后提交时间（反刷量）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 更新时间
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `user_id` | BIGINT | Telegram用户ID（主键） | 5156570084 |
| `username` | VARCHAR(255) | Telegram用户名 | @john_doe |
| `first_name` | VARCHAR(255) | Telegram名字 | John |
| `display_name` | VARCHAR(255) | 显示名称 | John Doe |
| `language` | VARCHAR(10) | 语言偏好 | zh, en |
| `wallet_address` | VARCHAR(42) | 以太坊钱包地址 | 0x742d35... |
| `sol_wallet` | VARCHAR(44) | Solana钱包地址 | 7xKXtg2... |
| `total_node_power` | INTEGER | 总算力（X2C） | 150 |
| `completed_tasks` | INTEGER | 完成任务数 | 15 |
| `invited_by` | BIGINT | 邀请人的user_id | 1234567890 |
| `invitation_reward_received` | BOOLEAN | 是否已领取邀请奖励 | true/false |
| `invitation_reward_received_at` | TIMESTAMP | 邀请奖励领取时间 | 2025-12-03 10:30:00 |
| `last_submission_time` | TIMESTAMP | 最后提交时间 | 2025-12-03 15:45:00 |
| `created_at` | TIMESTAMP | 用户注册时间 | 2025-11-01 08:00:00 |
| `updated_at` | TIMESTAMP | 最后更新时间 | 2025-12-03 15:45:00 |

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_users_last_submit ON users(last_submission_time);
```

---

## 2️⃣ drama_tasks 表 - 短剧任务

**作用**: 存储所有短剧推广任务信息

**表名**: `drama_tasks`

### 表结构

```sql
CREATE TABLE drama_tasks (
    task_id SERIAL PRIMARY KEY,                      -- 任务ID（自增主键）
    external_task_id INTEGER,                        -- 外部任务ID（X2C平台）
    project_id VARCHAR(255),                         -- 项目ID（X2C平台）
    title VARCHAR(255) NOT NULL,                     -- 任务标题
    title_en TEXT,                                   -- 任务标题（英文）
    description TEXT,                                -- 任务描述
    description_en TEXT,                             -- 任务描述（英文）
    category VARCHAR(50),                            -- 任务分类
    video_file_id TEXT,                              -- Telegram视频文件ID
    video_url TEXT,                                  -- 视频URL
    thumbnail_url TEXT,                              -- 缩略图URL
    duration INTEGER DEFAULT 15,                     -- 视频时长（秒）
    node_power_reward INTEGER DEFAULT 10,            -- 奖励算力（X2C）
    platform_requirements TEXT DEFAULT 'TikTok,YouTube,Instagram', -- 平台要求
    task_template TEXT,                              -- 任务模板
    keywords_template TEXT,                          -- 关键词模板
    video_title TEXT,                                -- 视频标题
    status VARCHAR(20) DEFAULT 'active',             -- 任务状态
    
    -- Webhook 回调相关字段
    callback_url TEXT,                               -- 回调URL
    callback_secret TEXT,                            -- 回调密钥
    callback_status TEXT DEFAULT 'pending',          -- 回调状态
    callback_retry_count INTEGER DEFAULT 0,          -- 回调重试次数
    callback_last_attempt_at TIMESTAMP,              -- 最后回调尝试时间
    callback_response_status INTEGER,                -- 回调响应状态码
    callback_error_message TEXT,                     -- 回调错误信息
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 创建时间
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `task_id` | SERIAL | 内部任务ID（主键） | 75 |
| `external_task_id` | INTEGER | X2C平台任务ID | 123456 |
| `project_id` | VARCHAR(255) | X2C项目ID | 09918fc2-ce97-4cf4-8... |
| `title` | VARCHAR(255) | 任务标题 | 南洋当大佬 - 第01集 |
| `title_en` | TEXT | 任务标题（英文） | Nanyang Boss - EP01 |
| `description` | TEXT | 任务描述 | 都市爱情短剧第一集... |
| `description_en` | TEXT | 任务描述（英文） | Urban romance drama... |
| `category` | VARCHAR(50) | 任务分类 | revenge, rebirth, sweet_romance |
| `video_file_id` | TEXT | TG视频文件ID | BAACAgIAAxkBAAI... |
| `video_url` | TEXT | 视频URL | https://example.com/video.mp4 |
| `thumbnail_url` | TEXT | 缩略图URL | https://example.com/thumb.jpg |
| `duration` | INTEGER | 视频时长（秒） | 15 |
| `node_power_reward` | INTEGER | 奖励算力（X2C） | 10 |
| `platform_requirements` | TEXT | 平台要求 | TikTok,YouTube,Instagram |
| `task_template` | TEXT | 任务模板 | 观看视频并分享到... |
| `keywords_template` | TEXT | 关键词模板 | #短剧 #霸道总裁 |
| `video_title` | TEXT | 视频标题 | 霸道总裁爱上我 |
| `status` | VARCHAR(20) | 任务状态 | active, paused, completed |
| **callback_url** | TEXT | **回调URL** | https://rxkcgquecleofqhyfchx.supabase.co/... |
| **callback_secret** | TEXT | **回调密钥** | secret_key_123 |
| **callback_status** | TEXT | **回调状态** | pending, success, failed |
| **callback_retry_count** | INTEGER | **回调重试次数** | 0, 1, 2, 3 |
| **callback_last_attempt_at** | TIMESTAMP | **最后回调尝试时间** | 2025-12-03 03:38:18 |
| **callback_response_status** | INTEGER | **回调响应状态码** | 200, 500, 404 |
| **callback_error_message** | TEXT | **回调错误信息** | Connection timeout |
| `created_at` | TIMESTAMP | 创建时间 | 2025-12-03 00:00:00 |

### 任务分类 (category)

```python
CATEGORY_NAMES_ZH = {
    'revenge': '霸道总裁/豪门虐恋',
    'rebirth': '穿越重生/逆天改命',
    'revenge_slap': '复仇爽文/打脸反杀',
    'marriage': '婚恋错配/先婚后爱',
    'sweet_romance': '甜宠小白花/治愈爱情',
    'family': '家庭伦理/婆媳大战',
    'detective': '破案刑侦/悬疑推理',
    'medical': '医疗法庭/职场权谋',
    'career_woman': '女强成长/职场逆袭',
    'campus': '校园青春/青涩暗恋',
    'horror': '恐怖灵异/民俗悬疑',
    'scifi': '赛博/未来科幻',
    'survival': '末日生存/丧尸灾难',
    'costume': '宫斗宅斗/古装权谋',
    'business': '商战博弈/资本智斗',
    'rural': '乡村/人生治愈系',
    'superpower': '超能力变异/英雄觉醒',
    'triangle': '三角恋/修罗场',
    'underdog': '小人物大机缘',
    'dark': '反社会性人格/黑暗系'
}
```

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_external_task_id ON drama_tasks(external_task_id);
CREATE INDEX IF NOT EXISTS idx_drama_tasks_callback_status ON drama_tasks(callback_status);
```

---

## 3️⃣ user_tasks 表 - 用户任务关联

**作用**: 记录用户领取和完成任务的关系

**表名**: `user_tasks`

### 表结构

```sql
CREATE TABLE user_tasks (
    id SERIAL PRIMARY KEY,                           -- 记录ID（自增主键）
    user_id BIGINT NOT NULL,                         -- 用户ID
    task_id INTEGER NOT NULL,                        -- 任务ID
    status VARCHAR(20) DEFAULT 'in_progress',        -- 任务状态
    platform VARCHAR(50),                            -- 提交平台
    submission_link TEXT,                            -- 提交链接
    accepted_at TIMESTAMP,                           -- 领取时间
    submitted_at TIMESTAMP,                          -- 提交时间
    verified_at TIMESTAMP,                           -- 验证时间
    node_power_earned INTEGER DEFAULT 0,             -- 获得算力
    link_verified BOOLEAN DEFAULT FALSE,             -- 链接是否已验证
    verification_time TIMESTAMP,                     -- 验证时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id)
);
```

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `id` | SERIAL | 记录ID（主键） | 1001 |
| `user_id` | BIGINT | 用户ID（外键） | 5156570084 |
| `task_id` | INTEGER | 任务ID（外键） | 75 |
| `status` | VARCHAR(20) | 任务状态 | accepted, in_progress, submitted |
| `platform` | VARCHAR(50) | 提交平台 | TikTok, YouTube, Instagram |
| `submission_link` | TEXT | 提交链接 | https://www.youtube.com/watch?v=xxx |
| `accepted_at` | TIMESTAMP | 领取时间 | 2025-12-03 10:00:00 |
| `submitted_at` | TIMESTAMP | 提交时间 | 2025-12-03 10:15:00 |
| `verified_at` | TIMESTAMP | 验证时间 | 2025-12-03 10:16:00 |
| `node_power_earned` | INTEGER | 获得算力 | 10 |
| `link_verified` | BOOLEAN | 链接是否已验证 | true/false |
| `verification_time` | TIMESTAMP | 验证时间 | 2025-12-03 10:16:00 |
| `created_at` | TIMESTAMP | 创建时间 | 2025-12-03 10:00:00 |

### 任务状态 (status)

- `accepted` - 已领取
- `in_progress` - 进行中
- `submitted` - 已提交
- `verified` - 已验证
- `completed` - 已完成

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_user_tasks_user_created ON user_tasks(user_id, created_at);
```

---

## 4️⃣ user_invitations 表 - 用户邀请关系

**作用**: 记录用户之间的邀请关系

**表名**: `user_invitations`

### 表结构

```sql
CREATE TABLE user_invitations (
    invitation_id SERIAL PRIMARY KEY,                -- 邀请记录ID
    inviter_id BIGINT NOT NULL,                      -- 邀请人ID
    invitee_id BIGINT NOT NULL,                      -- 被邀请人ID
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 邀请时间
    first_task_completed BOOLEAN DEFAULT FALSE,      -- 是否完成首个任务
    first_task_completed_at TIMESTAMP,               -- 首个任务完成时间
    total_referral_rewards DECIMAL(10, 2) DEFAULT 0.00, -- 总推荐奖励
    
    FOREIGN KEY (inviter_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(invitee_id)
);
```

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_inviter_id ON user_invitations(inviter_id);
CREATE INDEX IF NOT EXISTS idx_invitee_id ON user_invitations(invitee_id);
```

---

## 5️⃣ referral_rewards 表 - 推荐奖励记录

**作用**: 记录每笔推荐奖励交易

**表名**: `referral_rewards`

### 表结构

```sql
CREATE TABLE referral_rewards (
    reward_id SERIAL PRIMARY KEY,                    -- 奖励记录ID
    inviter_id BIGINT NOT NULL,                      -- 邀请人ID
    invitee_id BIGINT NOT NULL,                      -- 被邀请人ID
    task_id INT NOT NULL,                            -- 任务ID
    original_reward DECIMAL(10, 2) NOT NULL,         -- 原始奖励
    referral_reward DECIMAL(10, 2) NOT NULL,         -- 推荐奖励
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    
    FOREIGN KEY (inviter_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (invitee_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id) ON DELETE CASCADE
);
```

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_referral_inviter ON referral_rewards(inviter_id);
CREATE INDEX IF NOT EXISTS idx_referral_invitee ON referral_rewards(invitee_id);
```

---

## 6️⃣ withdrawals 表 - 提现记录

**作用**: 记录用户的X2C提现请求

**表名**: `withdrawals`

### 表结构

```sql
CREATE TABLE withdrawals (
    withdrawal_id SERIAL PRIMARY KEY,                -- 提现记录ID
    user_id BIGINT NOT NULL,                         -- 用户ID
    sol_address VARCHAR(44) NOT NULL,                -- Solana地址
    amount DECIMAL(10, 2) NOT NULL,                  -- 提现金额
    status VARCHAR(20) DEFAULT 'pending',            -- 提现状态
    tx_hash VARCHAR(128),                            -- 交易哈希
    error_message TEXT,                              -- 错误信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    processed_at TIMESTAMP,                          -- 处理时间
    
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
```

### 提现状态 (status)

- `pending` - 待处理
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败

### 索引

```sql
CREATE INDEX IF NOT EXISTS idx_withdrawal_user ON withdrawals(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON withdrawals(status);
```

---

## 7️⃣ airdrop_snapshots 表 - 空投快照

**作用**: 记录空投快照数据

**表名**: `airdrop_snapshots`

### 表结构

```sql
CREATE TABLE airdrop_snapshots (
    id SERIAL PRIMARY KEY,                           -- 快照ID
    round_number INTEGER NOT NULL,                   -- 轮次
    user_id BIGINT NOT NULL,                         -- 用户ID
    node_power INTEGER NOT NULL,                     -- 算力
    rank INTEGER,                                    -- 排名
    estimated_airdrop DECIMAL(18, 6),                -- 预估空投
    snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 快照时间
    
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

---

## 📊 表关系图

```
users (TG Bot用户)
  ├─→ user_tasks (用户任务关联)
  │     └─→ drama_tasks (短剧任务)
  │           └─→ callback_* (Webhook回调字段)
  │
  ├─→ user_invitations (邀请关系)
  │     ├─→ inviter_id → users
  │     └─→ invitee_id → users
  │
  ├─→ referral_rewards (推荐奖励)
  │     ├─→ inviter_id → users
  │     ├─→ invitee_id → users
  │     └─→ task_id → drama_tasks
  │
  ├─→ withdrawals (提现记录)
  │
  └─→ airdrop_snapshots (空投快照)
```

---

## 🔑 核心业务流程

### 1. 用户注册流程

```
用户首次使用Bot
    ↓
创建 users 记录
    ↓
如果有邀请码
    ↓
创建 user_invitations 记录
```

### 2. 任务完成流程

```
X2C平台创建任务
    ↓
创建 drama_tasks 记录（包含callback_url）
    ↓
用户领取任务
    ↓
创建 user_tasks 记录（status='accepted'）
    ↓
用户提交链接
    ↓
更新 user_tasks（status='submitted', submission_link）
    ↓
Bot验证链接
    ↓
更新 user_tasks（status='verified'）
    ↓
Bot发送Webhook回调到X2C
    ↓
更新 drama_tasks 的 callback_* 字段
    ↓
更新 users 的 total_node_power 和 completed_tasks
```

### 3. Webhook回调流程

```
用户完成任务
    ↓
Bot向 drama_tasks.callback_url 发送POST请求
    ↓
记录回调结果到 drama_tasks:
  - callback_status (success/failed)
  - callback_retry_count
  - callback_last_attempt_at
  - callback_response_status
  - callback_error_message
    ↓
如果失败，自动重试（最多3次）
```

---

## 💡 关键点总结

### users 表
- ✅ 管理所有 TG Bot 用户
- ✅ 存储用户的 Telegram 信息
- ✅ 记录用户的算力和完成任务数
- ✅ 支持邀请系统

### drama_tasks 表
- ✅ 存储所有短剧推广任务
- ✅ 包含完整的 Webhook 回调字段
- ✅ 支持多语言（中英文）
- ✅ 记录回调状态和重试信息

### user_tasks 表
- ✅ 连接用户和任务
- ✅ 记录任务完成状态
- ✅ 存储提交链接和验证结果
- ✅ 支持反刷量验证

---

## 🔧 常用查询

### 查询用户完成的任务

```sql
SELECT 
    u.user_id,
    u.first_name,
    t.title,
    ut.submission_link,
    ut.submitted_at
FROM user_tasks ut
JOIN users u ON ut.user_id = u.user_id
JOIN drama_tasks t ON ut.task_id = t.task_id
WHERE ut.status = 'submitted'
ORDER BY ut.submitted_at DESC;
```

### 查询Webhook回调失败的任务

```sql
SELECT 
    task_id,
    title,
    callback_status,
    callback_retry_count,
    callback_error_message
FROM drama_tasks
WHERE callback_status = 'failed'
ORDER BY callback_last_attempt_at DESC;
```

### 查询用户邀请统计

```sql
SELECT 
    u.user_id,
    u.first_name,
    COUNT(ui.invitee_id) as total_invites,
    SUM(ui.total_referral_rewards) as total_rewards
FROM users u
LEFT JOIN user_invitations ui ON u.user_id = ui.inviter_id
GROUP BY u.user_id, u.first_name
ORDER BY total_invites DESC;
```

---

## 📝 数据库维护

### 备份建议

```bash
# 备份整个数据库
pg_dump -h hostname -U username -d database_name > backup.sql

# 只备份核心表
pg_dump -h hostname -U username -d database_name \
  -t users -t drama_tasks -t user_tasks > core_tables_backup.sql
```

### 性能优化

1. 定期分析表统计信息
```sql
ANALYZE users;
ANALYZE drama_tasks;
ANALYZE user_tasks;
```

2. 清理旧数据（可选）
```sql
-- 删除6个月前的空投快照
DELETE FROM airdrop_snapshots 
WHERE snapshot_date < NOW() - INTERVAL '6 months';
```

---

**文档版本**: v1.0  
**最后更新**: 2025-12-03  
**数据库类型**: PostgreSQL
