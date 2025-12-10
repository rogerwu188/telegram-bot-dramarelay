# 数据库迁移执行指南

## 🎯 Migration 006: users → TG_Bot_User

### 快速开始

1. **备份数据库**（必须！）
2. **执行迁移脚本**
3. **验证结果**
4. **重启应用**

---

## 📋 详细步骤

### 步骤 1: 备份数据库

在执行迁移前，**必须**先备份数据库！

#### 方式1: 使用 Railway CLI

```bash
# 连接到 Railway 数据库
railway connect <database_service_name>

# 导出备份
pg_dump > backup_before_migration_006_$(date +%Y%m%d_%H%M%S).sql
```

#### 方式2: 使用 Railway 控制台

1. 打开 Railway 项目
2. 进入 Database 服务
3. 点击 "Data" 标签
4. 点击 "Backup" 按钮

---

### 步骤 2: 执行迁移脚本

#### 方式1: Railway 控制台（推荐）

1. 打开 Railway 项目
2. 进入 PostgreSQL 服务
3. 点击 "Query" 标签
4. 复制 `migrations/006_rename_users_to_tg_bot_user.sql` 的内容
5. 粘贴到查询编辑器
6. 点击 "Run Query" 执行

#### 方式2: 本地 psql 命令

```bash
# 设置数据库连接信息
export PGHOST=<railway_host>
export PGPORT=<railway_port>
export PGUSER=<railway_user>
export PGPASSWORD=<railway_password>
export PGDATABASE=<railway_database>

# 执行迁移
psql -f migrations/006_rename_users_to_tg_bot_user.sql
```

#### 方式3: Python 脚本

```python
import psycopg2
import os

# 连接数据库
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# 读取迁移脚本
with open('migrations/006_rename_users_to_tg_bot_user.sql', 'r') as f:
    migration_sql = f.read()

# 执行迁移
cur.execute(migration_sql)
conn.commit()

print("✅ 迁移完成！")
```

---

### 步骤 3: 验证迁移结果

执行以下 SQL 验证迁移是否成功：

```sql
-- 1. 检查表和视图是否存在
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_name IN ('TG_Bot_User', 'users')
ORDER BY table_type, table_name;

-- 期望结果:
-- TG_Bot_User | BASE TABLE
-- users       | VIEW

-- 2. 检查记录数是否一致
SELECT 
    (SELECT COUNT(*) FROM "TG_Bot_User") as tg_bot_user_count,
    (SELECT COUNT(*) FROM users) as users_view_count;

-- 期望结果: 两个数字应该相同

-- 3. 检查触发器
SELECT trigger_name, event_manipulation
FROM information_schema.triggers
WHERE event_object_table = 'users'
ORDER BY trigger_name;

-- 期望结果:
-- users_delete | DELETE
-- users_insert | INSERT
-- users_update | UPDATE

-- 4. 检查外键约束
SELECT 
    tc.table_name, 
    tc.constraint_name,
    ccu.table_name AS foreign_table_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND ccu.table_name = 'TG_Bot_User'
ORDER BY tc.table_name;

-- 期望结果: 应该看到所有外键都指向 TG_Bot_User

-- 5. 测试 INSERT 操作
BEGIN;
INSERT INTO users (user_id, username, first_name) 
VALUES (999999999, 'test_user', 'Test');
SELECT * FROM "TG_Bot_User" WHERE user_id = 999999999;
ROLLBACK;

-- 期望结果: 应该能看到插入的测试数据

-- 6. 测试 UPDATE 操作
BEGIN;
UPDATE users SET username = 'updated_test' WHERE user_id = (SELECT MIN(user_id) FROM users);
SELECT username FROM "TG_Bot_User" WHERE user_id = (SELECT MIN(user_id) FROM "TG_Bot_User");
ROLLBACK;

-- 期望结果: username 应该被更新
```

---

### 步骤 4: 重启应用

#### Railway 自动部署

如果您的项目设置了自动部署，迁移完成后应用会自动重启。

#### 手动重启

1. 打开 Railway 项目
2. 进入 Bot 服务
3. 点击 "Settings"
4. 点击 "Restart" 按钮

---

### 步骤 5: 测试应用功能

迁移完成后，测试以下关键功能：

#### 1. 用户注册

```
/start
```

期望：能够正常注册新用户

#### 2. 任务领取

```
/tasks
点击任意任务的"领取任务"按钮
```

期望：能够正常领取任务

#### 3. 任务提交

```
提交任务链接
```

期望：能够正常提交并验证

#### 4. 邀请系统

```
/invite
```

期望：能够生成邀请链接

#### 5. 排行榜

```
/leaderboard
```

期望：能够正常显示排行榜

#### 6. 管理后台

访问：https://worker-production-d960.up.railway.app/admin

期望：
- 统计数据正常显示
- 任务列表正常显示
- Webhook 日志正常显示

---

## ⚠️ 故障排查

### 问题 1: 迁移脚本执行失败

**症状**: SQL 执行报错

**解决方案**:
1. 检查错误信息
2. 确认数据库版本（需要 PostgreSQL 9.1+）
3. 检查是否有足够的权限
4. 尝试分段执行迁移脚本

### 问题 2: 视图无法 INSERT/UPDATE

**症状**: `cannot insert into view "users"`

**原因**: 触发器未正确创建

**解决方案**:
```sql
-- 检查触发器
SELECT * FROM information_schema.triggers WHERE event_object_table = 'users';

-- 如果触发器不存在，重新执行迁移脚本的第3步
```

### 问题 3: 外键约束错误

**症状**: `foreign key constraint fails`

**原因**: 外键仍然指向旧表名

**解决方案**:
```sql
-- 检查外键
SELECT * FROM information_schema.table_constraints 
WHERE constraint_type = 'FOREIGN KEY';

-- 重新执行迁移脚本的第5步
```

### 问题 4: 应用启动失败

**症状**: Bot 无法启动

**解决方案**:
1. 检查 Railway 日志
2. 确认数据库连接正常
3. 验证迁移是否完全成功
4. 如果问题严重，执行回滚

---

## 🔄 回滚步骤

如果迁移出现严重问题，可以回滚：

### 1. 恢复数据库备份

```bash
# 使用备份文件恢复
psql < backup_before_migration_006_YYYYMMDD_HHMMSS.sql
```

### 2. 或执行回滚脚本

```sql
-- 删除触发器
DROP TRIGGER IF EXISTS users_insert ON users;
DROP TRIGGER IF EXISTS users_update ON users;
DROP TRIGGER IF EXISTS users_delete ON users;

-- 删除触发器函数
DROP FUNCTION IF EXISTS users_insert_trigger();
DROP FUNCTION IF EXISTS users_update_trigger();
DROP FUNCTION IF EXISTS users_delete_trigger();

-- 删除视图
DROP VIEW IF EXISTS users;

-- 重命名表
ALTER TABLE "TG_Bot_User" RENAME TO users;

-- 重命名索引
ALTER INDEX "TG_Bot_User_pkey" RENAME TO users_pkey;
ALTER INDEX "idx_TG_Bot_User_last_submit" RENAME TO idx_users_last_submit;
```

### 3. 重启应用

---

## 📊 迁移检查清单

执行迁移前，请确认：

- [ ] 已备份数据库
- [ ] 已阅读迁移文档
- [ ] 已准备回滚方案
- [ ] 已通知团队成员
- [ ] 选择低峰时段执行

执行迁移后，请验证：

- [ ] 表 `TG_Bot_User` 存在
- [ ] 视图 `users` 存在
- [ ] 触发器已创建（3个）
- [ ] 外键约束已更新
- [ ] 记录数一致
- [ ] INSERT/UPDATE/DELETE 测试通过
- [ ] 应用正常启动
- [ ] 关键功能测试通过

---

## 📞 支持

如果遇到问题：

1. 查看 `migrations/README_006.md` 详细文档
2. 检查 Railway 日志
3. 查看数据库错误日志
4. 如有需要，执行回滚

---

**最后更新**: 2025-12-03  
**迁移版本**: 006  
**预计执行时间**: 5-10分钟
