# Migration 006: 重命名 users 表为 TG_Bot_User

## 📋 迁移概述

**目的**: 将 `users` 表重命名为 `TG_Bot_User`，以便更清晰地区分 TG Bot 用户和其他可能的用户表。

**策略**: 使用 PostgreSQL 视图（VIEW）+ 触发器（TRIGGER）实现向后兼容，无需修改任何现有代码。

**影响范围**: 
- ✅ 数据库表结构
- ✅ 外键约束
- ❌ 应用代码（无需修改）

---

## 🎯 迁移方案

### 方案选择

我们选择了**视图方案**而不是直接修改代码，原因：

| 方案 | 优点 | 缺点 |
|------|------|------|
| **视图方案** ✅ | 1. 无需修改代码<br>2. 向后兼容<br>3. 可逐步迁移<br>4. 回滚简单 | 1. 轻微性能开销<br>2. 需要触发器支持写操作 |
| 直接修改代码 | 1. 性能最优<br>2. 代码更清晰 | 1. 需要修改81处代码<br>2. 测试工作量大<br>3. 回滚困难 |

### 技术实现

```
users 表 (旧)
    ↓ 重命名
TG_Bot_User 表 (新)
    ↓ 创建视图
users 视图 → TG_Bot_User 表
    ↓ 创建触发器
支持 INSERT/UPDATE/DELETE
```

---

## 🚀 执行步骤

### 1. 备份数据库（重要！）

```bash
# 在 Railway 控制台或本地执行
pg_dump -h <host> -U <user> -d <database> > backup_before_migration_006.sql
```

### 2. 执行迁移脚本

在 Railway 数据库控制台中执行：

```bash
# 方式1: 直接在 Railway 控制台粘贴执行
cat migrations/006_rename_users_to_tg_bot_user.sql

# 方式2: 使用 psql 命令行
psql -h <host> -U <user> -d <database> -f migrations/006_rename_users_to_tg_bot_user.sql
```

### 3. 验证迁移结果

```sql
-- 检查表是否存在
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_name IN ('TG_Bot_User', 'users');

-- 应该看到:
-- TG_Bot_User | BASE TABLE
-- users       | VIEW

-- 检查视图定义
\d+ users

-- 检查触发器
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE event_object_table = 'users';

-- 应该看到:
-- users_insert | INSERT | users
-- users_update | UPDATE | users
-- users_delete | DELETE | users

-- 测试查询
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM "TG_Bot_User";
-- 两个结果应该相同
```

### 4. 测试应用功能

```bash
# 重启应用
# 在 Railway 控制台重新部署或重启服务

# 测试关键功能:
# 1. 用户注册
# 2. 任务领取
# 3. 任务提交
# 4. 邀请系统
# 5. 提现功能
```

---

## 📊 迁移详情

### 重命名的对象

| 对象类型 | 旧名称 | 新名称 |
|---------|--------|--------|
| 表 | `users` | `"TG_Bot_User"` |
| 主键 | `users_pkey` | `"TG_Bot_User_pkey"` |
| 索引 | `idx_users_last_submit` | `"idx_TG_Bot_User_last_submit"` |

### 创建的新对象

| 对象类型 | 名称 | 说明 |
|---------|------|------|
| 视图 | `users` | 指向 `TG_Bot_User` 表 |
| 触发器 | `users_insert` | 支持 INSERT 操作 |
| 触发器 | `users_update` | 支持 UPDATE 操作 |
| 触发器 | `users_delete` | 支持 DELETE 操作 |
| 函数 | `users_insert_trigger()` | INSERT 触发器函数 |
| 函数 | `users_update_trigger()` | UPDATE 触发器函数 |
| 函数 | `users_delete_trigger()` | DELETE 触发器函数 |

### 更新的外键约束

所有引用 `users` 表的外键都已更新为引用 `"TG_Bot_User"` 表：

- `user_tasks.user_id` → `"TG_Bot_User".user_id`
- `user_invitations.inviter_id` → `"TG_Bot_User".user_id`
- `user_invitations.invitee_id` → `"TG_Bot_User".user_id`
- `referral_rewards.inviter_id` → `"TG_Bot_User".user_id`
- `referral_rewards.invitee_id` → `"TG_Bot_User".user_id`
- `withdrawals.user_id` → `"TG_Bot_User".user_id`
- `airdrop_snapshots.user_id` → `"TG_Bot_User".user_id`

---

## ✅ 向后兼容性

### 代码兼容性

✅ **所有现有代码无需修改**

```python
# 这些代码都可以继续正常工作:

# SELECT
cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))

# INSERT
cur.execute("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user_id, username))

# UPDATE
cur.execute("UPDATE users SET total_node_power = %s WHERE user_id = %s", (power, user_id))

# DELETE
cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

# JOIN
cur.execute("""
    SELECT * FROM users u
    JOIN user_tasks ut ON u.user_id = ut.user_id
""")
```

### 工作原理

```
应用代码
    ↓
SELECT * FROM users
    ↓
PostgreSQL 视图系统
    ↓
SELECT * FROM "TG_Bot_User"
    ↓
返回结果
```

对于写操作（INSERT/UPDATE/DELETE），触发器会自动将操作转发到实际的 `TG_Bot_User` 表。

---

## 🔄 回滚方案

如果迁移出现问题，可以执行以下步骤回滚：

```sql
-- 1. 删除触发器
DROP TRIGGER IF EXISTS users_insert ON users;
DROP TRIGGER IF EXISTS users_update ON users;
DROP TRIGGER IF EXISTS users_delete ON users;

-- 2. 删除触发器函数
DROP FUNCTION IF EXISTS users_insert_trigger();
DROP FUNCTION IF EXISTS users_update_trigger();
DROP FUNCTION IF EXISTS users_delete_trigger();

-- 3. 删除视图
DROP VIEW IF EXISTS users;

-- 4. 重命名表
ALTER TABLE "TG_Bot_User" RENAME TO users;

-- 5. 重命名索引
ALTER INDEX "TG_Bot_User_pkey" RENAME TO users_pkey;
ALTER INDEX "idx_TG_Bot_User_last_submit" RENAME TO idx_users_last_submit;

-- 6. 更新外键约束
-- (需要重新创建所有外键，指向 users 表)
```

---

## 📝 注意事项

### 1. 性能影响

- ✅ SELECT 操作：几乎无性能影响（视图是零成本抽象）
- ⚠️ INSERT/UPDATE/DELETE 操作：轻微性能开销（触发器执行）
- 💡 建议：将来逐步迁移代码直接使用 `"TG_Bot_User"` 表名

### 2. 表名大小写

- `"TG_Bot_User"` 使用双引号，保留大小写
- 在 SQL 中必须使用双引号：`SELECT * FROM "TG_Bot_User"`
- 视图 `users` 不需要双引号：`SELECT * FROM users`

### 3. 将来的迁移

可以逐步将代码中的 `users` 替换为 `"TG_Bot_User"`：

```python
# 旧代码（继续工作）
cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))

# 新代码（推荐）
from db_config import TG_BOT_USER_TABLE
cur.execute(f"SELECT * FROM {TG_BOT_USER_TABLE} WHERE user_id = %s", (user_id,))
```

---

## 🎯 下一步计划

### 短期（可选）

1. ✅ 监控应用性能，确保无异常
2. ✅ 更新数据库文档
3. ✅ 通知团队成员表名变更

### 长期（推荐）

1. 逐步迁移代码使用 `db_config.py` 中的表名常量
2. 在所有代码迁移完成后，可以考虑删除视图和触发器
3. 统一使用 `"TG_Bot_User"` 表名

---

## 📚 相关文件

- **迁移脚本**: `migrations/006_rename_users_to_tg_bot_user.sql`
- **表名配置**: `db_config.py`
- **数据库文档**: `DATABASE_SCHEMA.md`

---

## ❓ 常见问题

### Q1: 为什么使用视图而不是直接修改代码？

**A**: 视图方案的优势：
- 无需修改81处代码引用
- 向后兼容，降低风险
- 可以逐步迁移
- 回滚简单

### Q2: 视图会影响性能吗？

**A**: 
- SELECT 操作：几乎无影响（PostgreSQL 会优化视图查询）
- INSERT/UPDATE/DELETE：轻微影响（触发器开销）
- 实际影响：对于 TG Bot 的使用场景，性能影响可以忽略不计

### Q3: 如何直接访问 TG_Bot_User 表？

**A**:
```sql
-- 使用双引号
SELECT * FROM "TG_Bot_User";

-- 或使用配置文件
from db_config import TG_BOT_USER_TABLE
cur.execute(f"SELECT * FROM {TG_BOT_USER_TABLE}")
```

### Q4: 可以删除 users 视图吗？

**A**: 
- 不建议立即删除
- 建议先迁移所有代码使用新表名
- 确认无代码引用 `users` 后再删除视图

---

**迁移版本**: v006  
**创建日期**: 2025-12-03  
**状态**: ✅ 已测试，可执行
