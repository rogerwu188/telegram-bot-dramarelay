# Webhook 回调功能测试指南

## 📋 概述

本文档介绍如何测试 X2C Drama Relay Bot 的 Webhook 回调功能。

## 🎯 测试目标

1. 验证数据库迁移是否成功
2. 验证 API 端点是否正确接收 callback_url 参数
3. 验证任务完成后是否正确发送 Webhook 回调
4. 验证重试机制是否正常工作
5. 验证签名验证是否正确

## 🔧 测试环境准备

### 1. 数据库迁移

已完成 ✅ 数据库字段已成功添加:
- `callback_url` - Webhook 回调 URL
- `callback_secret` - 回调密钥
- `callback_retry_count` - 重试次数
- `callback_last_attempt` - 最后尝试时间
- `callback_status` - 回调状态 (pending/success/failed)

### 2. 依赖安装

确保已安装 `aiohttp` 库:
```bash
pip install aiohttp==3.9.1
```

## 🧪 测试方法

### 方法 1: 使用本地测试服务器 (推荐)

#### 步骤 1: 启动 Webhook 接收端

在终端 1 中运行:
```bash
cd /home/ubuntu/telegram-bot-dramarelay
python test_webhook_receiver.py
```

服务器将在 `http://localhost:5001` 启动。

#### 步骤 2: 配置测试任务

在数据库中为测试任务配置回调 URL:
```sql
UPDATE drama_tasks 
SET callback_url = 'http://localhost:5001/webhook',
    callback_secret = 'test_secret_key_2024'
WHERE task_id = 1;
```

#### 步骤 3: 运行测试脚本

在终端 2 中运行:
```bash
cd /home/ubuntu/telegram-bot-dramarelay
python test_webhook.py
```

#### 步骤 4: 观察结果

- 终端 1 (接收端) 应该显示收到的 Webhook 请求详情
- 终端 2 (发送端) 应该显示发送成功的消息

### 方法 2: 使用 Webhook.site (在线测试)

#### 步骤 1: 获取测试 URL

1. 访问 https://webhook.site
2. 复制页面上显示的唯一 URL (例如: `https://webhook.site/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

#### 步骤 2: 配置测试任务

```sql
UPDATE drama_tasks 
SET callback_url = 'https://webhook.site/your-unique-id',
    callback_secret = 'test_secret_key_2024'
WHERE task_id = 1;
```

#### 步骤 3: 运行测试脚本

```bash
python test_webhook.py
```

#### 步骤 4: 查看结果

在 webhook.site 页面上查看收到的请求详情。

### 方法 3: 通过 API 创建带回调的任务

使用 API 创建新任务并配置回调:

```bash
curl -X POST https://web-production-b95cb.up.railway.app/api/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: x2c_admin_secret_key_2024" \
  -d '{
    "title": "测试任务 - Webhook 回调",
    "description": "用于测试 Webhook 回调功能的任务",
    "video_url": "https://example.com/video.mp4",
    "node_power_reward": 10,
    "callback_url": "https://webhook.site/your-unique-id",
    "callback_secret": "test_secret_key_2024"
  }'
```

### 方法 4: 端到端测试 (完整流程)

1. 使用 API 创建带回调的任务
2. 在 Telegram Bot 中领取任务
3. 下载视频并上传到 TikTok/YouTube
4. 提交链接进行验证
5. 验证通过后,观察 Webhook 是否被触发

## 📊 预期结果

### 成功的 Webhook 回调应包含:

```json
{
  "event": "task.completed",
  "timestamp": "2025-11-27T10:30:00Z",
  "data": {
    "task_id": 1,
    "task_title": "测试任务",
    "user_id": 123456789,
    "username": "test_user",
    "platform": "tiktok",
    "submission_link": "https://www.tiktok.com/@test/video/123456",
    "submitted_at": "2025-11-27T10:25:00Z",
    "verified_at": "2025-11-27T10:30:00Z",
    "node_power_earned": 10,
    "verification_status": "verified",
    "verification_details": {
      "matched": true,
      "match_rate": 100,
      "matched_keywords": ["关键词1", "关键词2"]
    }
  }
}
```

### 请求头应包含:

```
Content-Type: application/json
X-Webhook-Event: task.completed
X-Webhook-Timestamp: 1732704600
X-Webhook-Secret: test_secret_key_2024
X-Webhook-Signature: sha256=abc123...
User-Agent: X2C-Bot-Webhook/1.0
```

## 🔄 重试机制测试

### 测试重试功能:

1. 配置一个无效的回调 URL:
```sql
UPDATE drama_tasks 
SET callback_url = 'http://invalid-url-that-does-not-exist.com/webhook',
    callback_secret = 'test_secret'
WHERE task_id = 1;
```

2. 运行测试脚本

3. 观察日志,应该看到:
   - 第 1 次尝试失败,5 秒后重试
   - 第 2 次尝试失败,25 秒后重试
   - 第 3 次尝试失败,标记为 failed

4. 检查数据库:
```sql
SELECT task_id, callback_status, callback_retry_count, callback_last_attempt
FROM drama_tasks
WHERE task_id = 1;
```

应该看到:
- `callback_status` = 'failed'
- `callback_retry_count` = 3
- `callback_last_attempt` = 最后一次尝试的时间

## 🔐 签名验证测试

### 在接收端验证签名:

```python
import hmac
import hashlib

def verify_signature(payload_str: str, signature: str, secret: str) -> bool:
    """验证 HMAC-SHA256 签名"""
    expected_signature = 'sha256=' + hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)

# 使用示例
payload_str = request.get_data(as_text=True)
signature = request.headers.get('X-Webhook-Signature')
secret = 'test_secret_key_2024'

if verify_signature(payload_str, signature, secret):
    print("✅ 签名验证成功")
else:
    print("❌ 签名验证失败")
```

## 📝 测试清单

- [ ] 数据库迁移成功
- [ ] API 端点接受 callback_url 和 callback_secret 参数
- [ ] 任务完成后触发 Webhook 回调
- [ ] Webhook 请求包含正确的数据格式
- [ ] Webhook 请求包含正确的签名
- [ ] 回调失败时正确重试 (3次)
- [ ] 重试使用指数退避策略 (5s, 25s, 125s)
- [ ] 达到最大重试次数后标记为 failed
- [ ] 回调成功后更新数据库状态
- [ ] 回调失败不影响任务提交成功

## 🐛 故障排查

### 问题 1: Webhook 未发送

**检查项:**
1. 任务是否配置了 callback_url?
2. bot.py 是否正确导入 webhook_notifier?
3. 查看日志是否有错误信息

### 问题 2: 接收端收不到请求

**检查项:**
1. callback_url 是否正确?
2. 接收端服务是否正在运行?
3. 防火墙是否阻止了请求?
4. 如果使用 localhost,确保发送端和接收端在同一台机器

### 问题 3: 签名验证失败

**检查项:**
1. 发送端和接收端使用的 secret 是否一致?
2. 签名算法是否正确 (HMAC-SHA256)?
3. payload 字符串是否完全一致 (包括空格、换行)?

### 问题 4: 重试不工作

**检查项:**
1. 查看数据库中的 callback_retry_count 字段
2. 查看日志中的重试信息
3. 确认 asyncio.create_task() 正常工作

## 📚 相关文档

- [X2C API 文档](./X2C_API_Documentation.md)
- [Webhook 外部接口规范](./WEBHOOK_INTEGRATION_GUIDE.md)
- [Bot 部署指南](./README.md)

## 🆘 获取帮助

如果测试过程中遇到问题,请:
1. 查看日志文件
2. 检查数据库状态
3. 参考故障排查部分
4. 联系开发团队
