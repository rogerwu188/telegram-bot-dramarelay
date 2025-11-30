# DramaRelay Bot - Project ID 功能实施总结

## 修复时间
2024-11-29

## 修复目标
为 DramaRelay Bot 添加 `project_id` 字段支持，实现与 X2C 任务分发平台的全链路 UUID 追踪。

---

## 问题背景

### 业务需求
X2C 平台需要通过统一的 `project_id` 追踪任务从创建到完成的全流程：
1. 一个 project 可能包含多个 tasks/episodes（如多集短剧）
2. 每个 task 独立统计，但需要关联到同一个 project
3. `project_id` 作为全链路唯一标识符，在整个数据流转过程中保持不变

### 数据流转路径
```
X2C平台 → POST /api/tasks (含project_id) → Bot存储 → 用户完成任务 → Webhook回调 (含project_id) → X2C平台
```

---

## 实施方案

### 1. 数据库表结构修改

**修改文件**: `bot.py` (数据库初始化部分)

**修改内容**:
在 `drama_tasks` 表添加 `project_id` 字段：

```sql
ALTER TABLE drama_tasks ADD COLUMN project_id VARCHAR(255);
CREATE INDEX idx_project_id ON drama_tasks(project_id);
```

**字段说明**:
- 类型：`VARCHAR(255)`
- 可为空：是（兼容旧数据）
- 索引：已添加，提高查询性能
- 用途：存储项目唯一标识符（建议使用UUID格式）

### 2. 任务接收接口修改

**修改文件**: `api_server.py`

**修改位置**: `create_task()` 函数

**修改前**:
```python
cur.execute("""
    INSERT INTO drama_tasks (
        title, description, video_file_id, thumbnail_url,
        duration, node_power_reward, platform_requirements, status,
        video_url, task_template, keywords_template, video_title,
        callback_url, callback_secret
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING task_id, title, created_at
""", (
    data.get('title'),
    data.get('description'),
    video_url,
    ...
))
```

**修改后**:
```python
cur.execute("""
    INSERT INTO drama_tasks (
        project_id, title, description, video_file_id, thumbnail_url,
        duration, node_power_reward, platform_requirements, status,
        video_url, task_template, keywords_template, video_title,
        callback_url, callback_secret
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING task_id, project_id, title, created_at
""", (
    data.get('project_id'),  # 新增：接收project_id参数
    data.get('title'),
    data.get('description'),
    video_url,
    ...
))
```

**功能说明**:
- 接收外部平台传入的 `project_id` 参数
- 存储到 `drama_tasks` 表
- 在返回数据中包含 `project_id`

### 3. 统计回调接口修改

**修改文件**: `webhook_notifier.py`

**修改位置**: `notify_task_completion()` 函数

**修改1 - 查询任务信息**:
```python
# 修改前
cur.execute("""
    SELECT task_id, title, callback_url, callback_secret, callback_retry_count
    FROM drama_tasks
    WHERE task_id = %s
""", (task_id,))

# 修改后
cur.execute("""
    SELECT task_id, project_id, title, callback_url, callback_secret, callback_retry_count
    FROM drama_tasks
    WHERE task_id = %s
""", (task_id,))
```

**修改2 - 构建回调数据**:
```python
# 修改前
payload = {
    'event': 'task.completed',
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'data': {
        'task_id': task_id,
        'task_title': task['title'],
        'user_id': user_id,
        ...
    }
}

# 修改后
payload = {
    'event': 'task.completed',
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'data': {
        'project_id': task.get('project_id'),  # 新增：包含project_id
        'task_id': task_id,
        'task_title': task['title'],
        'user_id': user_id,
        ...
    }
}
```

**功能说明**:
- 从数据库查询任务时获取 `project_id` 字段
- 在回调数据的 `data` 对象中添加 `project_id` 字段
- 确保回调数据中的 `project_id` 与创建任务时传入的一致

---

## 代码提交

### Git 提交信息
```
feat: 添加project_id字段支持全链路追踪

- 在drama_tasks表添加project_id字段(VARCHAR 255)
- 修改api_server.py任务接收接口，支持接收和存储project_id
- 修改webhook_notifier.py统计回调接口，在回调数据中包含project_id
- 实现外部平台→Bot→统计回调的project_id全链路传递
```

### 提交哈希
`bd737b5`

### 推送状态
✅ 已成功推送到 GitHub `main` 分支

---

## 数据结构文档

已生成完整的数据结构文档：`project_id_数据结构文档.md`

**文档内容包括**:
1. 任务创建接口（X2C → Bot）
   - 请求数据结构
   - 响应数据结构
   - 字段说明

2. 任务完成回调接口（Bot → X2C）
   - 回调数据结构
   - 签名验证方法
   - 字段说明

3. 数据库表结构
   - `drama_tasks` 表定义
   - 索引说明

4. 使用场景示例
   - 单集短剧任务
   - 多集短剧项目

5. 注意事项
   - 字段兼容性
   - 回调重试机制
   - 签名验证
   - project_id 格式建议
   - 统计查询示例

---

## 测试验证

### 数据库迁移
由于 Railway 部署会自动执行 `auto_migrate.py`，数据库表结构会自动更新，无需手动操作。

### 功能测试建议

#### 1. 测试任务创建（含 project_id）
```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "测试任务 - 霸道总裁爱上我 第1集",
    "video_url": "https://example.com/test.mp4",
    "callback_url": "https://webhook.site/your-unique-url",
    "callback_secret": "test_secret_123"
  }'
```

**预期结果**:
```json
{
  "success": true,
  "data": {
    "task_id": 123,
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "测试任务 - 霸道总裁爱上我 第1集",
    "created_at": "2024-11-29T..."
  }
}
```

#### 2. 测试任务创建（不含 project_id）
```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试任务 - 无project_id",
    "video_url": "https://example.com/test.mp4"
  }'
```

**预期结果**:
任务创建成功，`project_id` 为 `null`（兼容旧逻辑）

#### 3. 测试回调数据
用户完成任务后，检查回调数据是否包含 `project_id`：

**预期回调数据**:
```json
{
  "event": "task.completed",
  "timestamp": "2024-11-29T...",
  "data": {
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": 123,
    "user_id": 123456789,
    ...
  }
}
```

#### 4. 测试多集短剧场景
使用相同的 `project_id` 创建多个任务（不同集数），验证：
- 每个任务独立存储
- 每个任务的回调都包含相同的 `project_id`
- 可以通过 `project_id` 查询所有相关任务

---

## 兼容性说明

### 向后兼容
✅ 完全兼容旧数据和旧接口：
- `project_id` 字段可为空，不影响现有任务
- 创建任务时不传 `project_id` 参数仍然正常工作
- 旧任务的回调数据中 `project_id` 为 `null`

### 数据迁移
✅ 无需手动迁移：
- 新字段添加时使用 `ALTER TABLE ADD COLUMN`
- 旧数据的 `project_id` 自动为 `NULL`
- 不影响现有功能

---

## 注意事项

### 1. project_id 格式建议
- 推荐使用标准 UUID 格式（如 `550e8400-e29b-41d4-a716-446655440000`）
- 最大长度 255 字符
- 可以为空（null），但建议所有新任务都提供 `project_id`

### 2. 统计查询
如需按项目统计所有任务的完成情况，可以使用以下 SQL：

```sql
SELECT 
    dt.project_id,
    COUNT(DISTINCT dt.task_id) as total_tasks,
    COUNT(ut.user_id) as total_submissions,
    COUNT(CASE WHEN ut.status = 'verified' THEN 1 END) as verified_submissions,
    COUNT(DISTINCT ut.user_id) as unique_users
FROM drama_tasks dt
LEFT JOIN user_tasks ut ON dt.task_id = ut.task_id
WHERE dt.project_id = '550e8400-e29b-41d4-a716-446655440000'
GROUP BY dt.project_id;
```

### 3. 回调重试
- Bot 会自动重试失败的回调（最多3次）
- X2C 平台应实现幂等性处理，避免重复回调导致数据问题

### 4. 签名验证
X2C 平台接收回调时，务必验证 `X-Webhook-Signature` 签名，确保数据安全。

---

## 相关文件

### 修改的代码文件
1. `bot.py` - 数据库表结构定义
2. `api_server.py` - 任务接收接口
3. `webhook_notifier.py` - 统计回调接口

### 生成的文档文件
1. `project_id_数据结构文档.md` - 完整的数据接口规范文档
2. `修复总结_project_id功能_2024-11-29.md` - 本文档

---

## 部署信息

### GitHub 仓库
https://github.com/rogerwu188/telegram-bot-dramarelay

### Railway 部署地址
https://web-production-b95cb.up.railway.app

### 部署状态
✅ 代码已推送到 GitHub，Railway 会自动部署

---

## 总结

### 实施成果
✅ 成功添加 `project_id` 字段支持  
✅ 实现全链路数据追踪  
✅ 保持向后兼容性  
✅ 生成完整的数据结构文档  
✅ 代码已提交并推送到 GitHub  

### 数据流转验证
```
外部平台 → POST /api/tasks (含project_id)
         ↓
    Bot存储到数据库
         ↓
    用户完成任务
         ↓
Webhook回调 (含project_id) → 外部平台
```

### 后续建议
1. 在 X2C 平台测试完整的任务创建和回调流程
2. 验证 `project_id` 在整个流程中的一致性
3. 实现基于 `project_id` 的统计分析功能
4. 考虑在管理后台添加按 `project_id` 查询的功能

---

**修复完成时间**: 2024-11-29  
**修复人员**: Manus AI Agent  
**文档版本**: 1.0
