# X2C DramaRelayBot - 部署和测试指南

## 当前状态

✅ 代码已推送到 GitHub: https://github.com/rogerwu188/telegram-bot-dramarelay
✅ Railway 应该正在自动部署
✅ 数据库表结构会自动创建

## 检查部署状态

### 1. 访问 Railway 控制台
- 登录 Railway: https://railway.app
- 找到你的项目
- 查看 Deployments 标签页
- 确认最新部署状态为 "Success"

### 2. 查看日志
在 Railway 控制台中查看日志，应该看到：
```
✅ BOT_TOKEN loaded
✅ Admin IDs loaded: [5156570084]
✅ DATABASE_URL loaded
Initializing database...
✅ Database tables initialized successfully
✅ Bot is running! Press Ctrl+C to stop.
```

## 添加测试任务

### 方法 1: 使用 Railway 数据库控制台（推荐）

1. 在 Railway 项目中，点击 PostgreSQL 服务
2. 点击 "Data" 标签页
3. 点击 "Query" 按钮
4. 复制 `init_demo_tasks.sql` 文件的内容
5. 粘贴到查询框中并执行
6. 确认任务已添加成功

### 方法 2: 使用 psql 命令行

```bash
# 获取数据库连接字符串（在 Railway 环境变量中）
psql $DATABASE_URL

# 然后执行 SQL 语句
INSERT INTO drama_tasks (title, description, duration, node_power_reward, platform_requirements, status)
VALUES ('霸道总裁爱上我 EP01', '都市爱情短剧第一集', 15, 10, 'TikTok,YouTube,Instagram', 'active');
```

### 方法 3: 使用管理员工具（需要在 Railway 环境中）

```bash
# SSH 到 Railway 容器（如果支持）
python3 admin_tools.py
# 选择选项 1 添加演示任务
```

## 测试 Bot 功能

### 1. 基础测试

在 Telegram 中找到 @DramaRelayBot，发送：

```
/start
```

**预期结果：**
- 看到新的欢迎消息（包含 X2C 全球短剧分发节点介绍）
- 看到 8 个按钮的菜单：
  - 🎬 领取短剧任务
  - 📤 提交链接
  - 📊 我的算力
  - 🏆 排行榜
  - 🎁 空投状态
  - 💼 绑定钱包
  - ℹ️ 使用教程
  - 🌐 切换语言

### 2. 语言切换测试

1. 点击 "🌐 切换语言"
2. 选择 "English"
3. 确认所有文本变为英文

### 3. 领取任务测试

1. 点击 "🎬 领取短剧任务" / "Get Drama Tasks"
2. 应该看到任务列表（如果已添加任务）
3. 点击一个任务查看详情
4. 点击 "✅ 确认领取"
5. 确认收到成功消息

### 4. 提交链接测试

1. 点击 "📤 提交链接" / "Submit Link"
2. 选择已领取的任务
3. 选择平台（如 TikTok）
4. 输入测试链接：`https://tiktok.com/@test/video/123456`
5. 确认收到成功消息和 Node Power 奖励

### 5. 查看算力测试

1. 点击 "📊 我的算力" / "My Node Power"
2. 确认显示：
   - 总 Node Power
   - 已完成任务数
   - 进行中任务数
   - 排名

### 6. 排行榜测试

1. 点击 "🏆 排行榜" / "Ranking"
2. 确认显示全球用户排名
3. 确认显示你的排名和算力

### 7. 空投状态测试

1. 点击 "🎁 空投状态" / "Airdrop Status"
2. 确认显示：
   - 当前轮次
   - 空投资格（需要 100+ NP）
   - 预计空投数量
   - 下次快照时间

### 8. 绑定钱包测试

1. 点击 "💼 绑定钱包" / "Bind Wallet"
2. 输入测试钱包地址：`0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`
3. 确认绑定成功

### 9. 使用教程测试

1. 点击 "ℹ️ 使用教程" / "How It Works"
2. 确认显示完整的使用说明

## 常见问题排查

### Bot 没有响应

**检查项：**
1. Railway 部署状态是否为 Success
2. 查看 Railway 日志是否有错误
3. 确认 BOT_TOKEN 是否正确
4. 确认数据库连接是否正常

**解决方法：**
- 在 Railway 中重启服务
- 检查环境变量配置
- 查看详细日志

### 看不到任务列表

**原因：**
- 数据库中还没有添加任务

**解决方法：**
- 使用 `init_demo_tasks.sql` 添加演示任务
- 或使用管理员工具添加任务

### 提交链接失败

**可能原因：**
1. 链接格式不正确
2. 任务未领取
3. 任务已提交过

**解决方法：**
- 使用正确的链接格式
- 先领取任务再提交
- 每个任务只能提交一次

### 数据库连接错误

**检查项：**
1. DATABASE_URL 是否正确
2. PostgreSQL 服务是否运行
3. 网络连接是否正常

**解决方法：**
- 在 Railway 中检查 PostgreSQL 服务状态
- 确认环境变量已正确设置
- 重启数据库服务

## 性能监控

### 关键指标

- **响应时间**: Bot 响应用户操作的速度
- **错误率**: 错误日志的数量
- **活跃用户**: 每日/每周活跃用户数
- **任务完成率**: 领取任务 vs 完成任务的比例

### 日志监控

在 Railway 日志中关注：
- `ERROR` 级别的日志
- 数据库连接错误
- API 调用失败
- 异常堆栈跟踪

## 下一步优化

### 功能增强
- [ ] 添加任务审核机制
- [ ] 实现自动链接验证
- [ ] 添加用户等级系统
- [ ] 实现推荐奖励机制
- [ ] 添加数据统计面板

### 性能优化
- [ ] 添加 Redis 缓存
- [ ] 优化数据库查询
- [ ] 实现连接池
- [ ] 添加 CDN 加速

### 安全加固
- [ ] 添加速率限制
- [ ] 实现反作弊机制
- [ ] 加强链接验证
- [ ] 添加用户行为分析

## 联系支持

如有问题，请：
1. 查看 Railway 日志
2. 检查 GitHub Issues
3. 联系开发团队

---

**部署时间**: 2025-11-25
**版本**: v2.0.0
**状态**: ✅ 已部署
