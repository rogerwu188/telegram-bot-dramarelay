# DramaRelay Bot 管理页面

## 功能说明

管理页面提供实时监控功能，包括：

### 📊 统计数据
- 总任务数
- 参与用户数
- 完成用户数
- 成功回调数
- 失败回调数

### 📤 Webhook 回调日志
显示所有配置了回调的任务，包括：
- 任务ID和标题
- Project ID
- 完成数量
- 回调状态（成功/失败/重试中/待回调）
- 重试次数
- 最后尝试时间
- 回调URL

### ✅ 任务完成日志
显示用户完成任务的详细记录：
- 用户信息（用户名、ID）
- 任务标题
- 平台要求
- 奖励金额
- 完成时间
- 用时
- 提交链接

### 📥 任务接收日志
显示从 X2C 平台接收的任务：
- 内部任务ID
- 外部任务ID（X2C）
- Project ID
- 任务标题
- 平台要求
- 奖励金额
- 分发用户数
- 完成用户数
- 创建时间

## 本地测试

### 1. 安装依赖
```bash
cd /home/ubuntu/telegram-bot-dramarelay
pip3 install -r requirements.txt
```

### 2. 配置环境变量
```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
export ADMIN_PORT=5001
```

### 3. 启动服务
```bash
./start_admin.sh
```

或者直接运行：
```bash
python3 admin_api.py
```

### 4. 访问页面
打开浏览器访问：http://localhost:5001

## Railway 部署

### 方法1：添加到现有服务

在 `api_server.py` 中添加管理页面路由：

```python
from admin_api import app as admin_app

# 注册管理页面路由
@app.route('/admin')
def admin_index():
    return admin_app.view_functions['index']()

@app.route('/api/logs/<path:path>')
def admin_api(path):
    return admin_app.view_functions[f'get_{path}']()
```

### 方法2：独立服务部署

1. 在 Railway 中创建新服务
2. 连接到同一个 GitHub 仓库
3. 设置启动命令：`python3 admin_api.py`
4. 配置环境变量：
   - `DATABASE_URL`: PostgreSQL 连接字符串
   - `ADMIN_PORT`: 5001（或其他端口）
5. 暴露端口：5001

### 方法3：修改 Procfile

如果项目使用 Procfile，添加：

```
web: python3 api_server.py
admin: python3 admin_api.py
```

## API 接口文档

### GET /api/logs/stats
获取统计数据

**参数：**
- `hours`: 时间范围（小时），默认 24

**返回：**
```json
{
  "success": true,
  "data": {
    "total_tasks": 10,
    "total_users": 50,
    "completed_users": 30,
    "successful_callbacks": 8,
    "failed_callbacks": 2
  }
}
```

### GET /api/logs/webhooks
获取 Webhook 回调日志

**参数：**
- `hours`: 时间范围（小时），默认 24
- `limit`: 返回条数，默认 50

**返回：**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "task_id": 1,
      "external_task_id": 123,
      "project_id": "uuid-string",
      "title": "任务标题",
      "callback_url": "https://...",
      "callback_status": "success",
      "callback_retry_count": 0,
      "callback_last_attempt": "2024-11-30T12:00:00",
      "completed_count": 5,
      "status_label": "✅ 成功",
      "status_class": "success"
    }
  ]
}
```

### GET /api/logs/completions
获取任务完成日志

**参数：**
- `hours`: 时间范围（小时），默认 24
- `limit`: 返回条数，默认 50

**返回：**
```json
{
  "success": true,
  "count": 20,
  "data": [
    {
      "user_id": 123456,
      "username": "user123",
      "display_name": "John Doe",
      "task_id": 1,
      "external_task_id": 123,
      "project_id": "uuid-string",
      "title": "任务标题",
      "platform_requirements": "YouTube",
      "node_power_reward": 10,
      "status": "completed",
      "assigned_at": "2024-11-30T11:00:00",
      "completed_at": "2024-11-30T12:00:00",
      "submission_link": "https://youtube.com/...",
      "duration_seconds": 3600
    }
  ]
}
```

### GET /api/logs/tasks
获取任务接收日志

**参数：**
- `hours`: 时间范围（小时），默认 24
- `limit`: 返回条数，默认 50

**返回：**
```json
{
  "success": true,
  "count": 10,
  "data": [
    {
      "task_id": 1,
      "external_task_id": 123,
      "project_id": "uuid-string",
      "title": "任务标题",
      "platform_requirements": "YouTube",
      "node_power_reward": 10,
      "task_status": "active",
      "created_at": "2024-11-30T10:00:00",
      "assigned_users": 10,
      "completed_users": 5,
      "last_completed_at": "2024-11-30T12:00:00"
    }
  ]
}
```

## 功能特性

### 🔄 自动刷新
点击"自动刷新"按钮，每 30 秒自动更新数据

### 🕐 时间范围
支持查询：
- 最近 1 小时
- 最近 6 小时
- 最近 24 小时（默认）
- 最近 3 天
- 最近 7 天

### 📊 显示条数
支持显示：
- 20 条
- 50 条（默认）
- 100 条
- 200 条

### 📱 响应式设计
支持桌面和移动设备访问

## 安全建议

### 生产环境部署建议：

1. **添加身份验证**
   - 使用 HTTP Basic Auth
   - 或集成 OAuth2

2. **限制访问IP**
   - 在 Railway 中配置防火墙规则
   - 只允许特定IP访问

3. **使用 HTTPS**
   - Railway 自动提供 HTTPS

4. **添加访问日志**
   - 记录所有访问请求
   - 监控异常访问

## 故障排查

### 页面无法访问
1. 检查服务是否启动：`ps aux | grep admin_api`
2. 检查端口是否监听：`netstat -tulpn | grep 5001`
3. 检查防火墙规则

### 数据加载失败
1. 检查 DATABASE_URL 环境变量
2. 检查数据库连接
3. 查看浏览器控制台错误
4. 查看服务器日志

### 回调数据不显示
1. 确认任务配置了 `callback_url`
2. 检查 `drama_tasks` 表的 `callback_status` 字段
3. 查看 Bot 日志中的 Webhook 相关信息

## 更新日志

### v1.0.0 (2024-11-30)
- ✅ 初始版本
- ✅ 统计数据展示
- ✅ Webhook 回调日志
- ✅ 任务完成日志
- ✅ 任务接收日志
- ✅ 自动刷新功能
- ✅ 响应式设计
