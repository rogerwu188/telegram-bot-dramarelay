# 抖音数据处理说明文档

## 📋 文档信息

- **版本**: 1.0
- **更新日期**: 2024-12-10
- **适用范围**: DramaRelay Bot 抖音平台数据处理

---

## 🎯 处理策略

### 核心原则

**抖音数据只在本地展现，但计入回传总量**

具体实现：
1. ✅ **本地存储完整数据**：抖音的所有数据（播放量、点赞数、评论数、分享数、收藏数）都保存在本地数据库
2. ✅ **管理后台展现**：管理后台可以查看抖音的详细数据统计
3. ✅ **回传计入总量**：向X2C Pool回传时，抖音数据计入YouTube字段（`yt_*`）
4. ✅ **不修改X2C接口**：保持与X2C Pool现有数据结构完全一致

---

## 📊 数据流转

### 1. 用户完成任务（抖音平台）

```
用户提交抖音链接
    ↓
VideoStatsFetcher 抓取抖音数据
    ↓
保存到 user_tasks.verification_details
    {
        "view_count": 2500,
        "like_count": 120,
        "comment_count": 15,
        "share_count": 8,
        "collect_count": 22
    }
    ↓
立即回传到 X2C Pool（计入yt_*字段）
    {
        "yt_account_count": 1,
        "yt_view_count": 2500,
        "yt_like_count": 120
    }
```

### 2. 每日汇总扫描

```
DailyStatsScanner 扫描前一天数据
    ↓
聚合所有平台数据
    - YouTube: 5个账号, 1200播放, 80点赞
    - TikTok: 6个账号
    - 抖音: 4个账号, 8000播放, 320点赞
    ↓
保存到 task_daily_stats 表（完整数据）
    yt_account_count: 5
    yt_view_count: 1200
    yt_like_count: 80
    tt_account_count: 6
    dy_account_count: 4
    dy_view_count: 8000
    dy_like_count: 320
    dy_comment_count: 45
    dy_share_count: 28
    dy_collect_count: 62
    ↓
回传到 X2C Pool（抖音计入yt_*）
    {
        "account_count": 15,
        "yt_account_count": 9,      // 5 + 4
        "yt_view_count": 9200,       // 1200 + 8000
        "yt_like_count": 400,        // 80 + 320
        "tt_account_count": 6
    }
```

---

## 🔧 技术实现

### 1. 实时回传（webhook_notifier.py）

**修改位置**: `webhook_notifier.py` 第213-220行

```python
elif 'douyin' in platform_lower or 'dy' in platform_lower:
    # 抖音平台统计：计入YouTube总量，不单独回传dy_*字段
    # 抖音数据只在本地展现，但播放量和点赞数计入yt_*总量
    if view_count > 0:
        stats_data['yt_view_count'] = view_count
    if like_count > 0:
        stats_data['yt_like_count'] = like_count
    stats_data['yt_account_count'] = 1
```

**效果**:
- 用户在抖音平台完成任务
- 回传数据使用 `yt_*` 字段
- X2C Pool接收到的数据格式与YouTube完成一致

### 2. 每日汇总回传（daily_stats_scanner.py）

**修改位置**: `daily_stats_scanner.py` 第403-421行

```python
# 抖音数据：计入YouTube总量，不单独回传dy_*字段
if stats['dy_account_count'] > 0:
    # 将抖音账号数计入YouTube账号数
    if 'yt_account_count' not in stat_item:
        stat_item['yt_account_count'] = 0
    stat_item['yt_account_count'] += stats['dy_account_count']
    
    # 将抖音播放量计入YouTube播放量
    if stats['dy_view_count'] > 0:
        if 'yt_view_count' not in stat_item:
            stat_item['yt_view_count'] = 0
        stat_item['yt_view_count'] += stats['dy_view_count']
    
    # 将抖音点赞数计入YouTube点赞数
    if stats['dy_like_count'] > 0:
        if 'yt_like_count' not in stat_item:
            stat_item['yt_like_count'] = 0
        stat_item['yt_like_count'] += stats['dy_like_count']
```

**效果**:
- 聚合时将抖音数据累加到YouTube字段
- 回传数据中 `yt_*` 字段包含YouTube + 抖音的总量
- X2C Pool无需修改接收逻辑

---

## 📤 回传数据格式

### X2C Pool接收到的数据格式（保持不变）

**实时回传示例**（抖音平台）:

```json
{
  "site_name": "DramaRelayBot",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 1,
      "yt_account_count": 1,
      "yt_view_count": 2500,
      "yt_like_count": 120
    }
  ]
}
```

**每日汇总示例**（混合平台）:

```json
{
  "site_name": "DramaRelayBot",
  "stats": [
    {
      "project_id": "550e8400-e29b-41d4-a716-446655440000",
      "task_id": 42,
      "duration": 30,
      "account_count": 15,
      "yt_account_count": 9,
      "yt_view_count": 9200,
      "yt_like_count": 400,
      "tt_account_count": 6
    }
  ]
}
```

**说明**:
- `yt_account_count = 9`: YouTube 5个 + 抖音 4个
- `yt_view_count = 9200`: YouTube 1200 + 抖音 8000
- `yt_like_count = 400`: YouTube 80 + 抖音 320

---

## 💾 本地数据存储

### 1. user_tasks表

**verification_details字段**（JSON格式）:

```json
{
  "view_count": 2500,
  "like_count": 120,
  "comment_count": 15,
  "share_count": 8,
  "collect_count": 22,
  "platform": "douyin"
}
```

**用途**: 存储用户完成任务时的原始数据

### 2. task_daily_stats表

**抖音相关字段**:

```sql
dy_account_count INTEGER DEFAULT 0,
dy_view_count BIGINT DEFAULT 0,
dy_like_count BIGINT DEFAULT 0,
dy_comment_count BIGINT DEFAULT 0,
dy_share_count BIGINT DEFAULT 0,
dy_collect_count BIGINT DEFAULT 0
```

**用途**: 存储每日汇总的抖音统计数据，用于管理后台展示

---

## 📊 管理后台展示

### 数据查询示例

```sql
-- 查询某个任务的抖音统计
SELECT 
    task_id,
    stats_date,
    dy_account_count AS "抖音账号数",
    dy_view_count AS "抖音播放量",
    dy_like_count AS "抖音点赞数",
    dy_comment_count AS "抖音评论数",
    dy_share_count AS "抖音分享数",
    dy_collect_count AS "抖音收藏数"
FROM task_daily_stats
WHERE task_id = 42
ORDER BY stats_date DESC;
```

### 管理后台展示建议

在管理后台可以展示：

1. **分平台统计**
   - YouTube: X个账号, X播放, X点赞
   - TikTok: X个账号
   - 抖音: X个账号, X播放, X点赞, X评论, X分享, X收藏

2. **总计统计**
   - 总账号数: X
   - 总播放量: X（YouTube + 抖音）
   - 总点赞数: X（YouTube + 抖音）

3. **回传统计**（与X2C Pool一致）
   - yt_account_count: X（YouTube + 抖音）
   - yt_view_count: X（YouTube + 抖音）
   - yt_like_count: X（YouTube + 抖音）
   - tt_account_count: X

---

## ✅ 优势分析

### 1. 对X2C Pool平台

- ✅ **无需修改接口**：完全兼容现有数据结构
- ✅ **无需修改代码**：接收逻辑保持不变
- ✅ **无需修改数据库**：不需要增加dy_*字段
- ✅ **平滑过渡**：立即可用，无需升级

### 2. 对DramaRelay Bot

- ✅ **完整数据保留**：本地保存所有抖音数据
- ✅ **灵活展示**：管理后台可以详细展示抖音数据
- ✅ **准确统计**：回传数据包含抖音贡献
- ✅ **易于维护**：逻辑清晰，代码简洁

### 3. 对用户

- ✅ **支持抖音平台**：可以在抖音完成任务
- ✅ **数据准确统计**：抖音数据计入总量
- ✅ **正常分账**：抖音完成的任务正常获得奖励

---

## 🔍 数据验证

### 验证方法1：查看回传日志

```bash
# 查看webhook发送日志
tail -f /home/ubuntu/telegram-bot-dramarelay/daily_stats.log | grep "📤"
```

**预期输出**:
```
📤 发送每日汇总Webhook: https://x2c.pool/api/callback
📊 数据: {"site_name":"DramaRelayBot","stats":[{"project_id":"...","task_id":42,"duration":30,"account_count":15,"yt_account_count":9,"yt_view_count":9200,"yt_like_count":400}]}
```

### 验证方法2：查询数据库

```sql
-- 查看本地存储的完整数据
SELECT 
    task_id,
    stats_date,
    total_account_count,
    yt_account_count,
    yt_view_count,
    yt_like_count,
    dy_account_count,
    dy_view_count,
    dy_like_count
FROM task_daily_stats
WHERE task_id = 42
ORDER BY stats_date DESC
LIMIT 1;
```

**预期结果**:
```
task_id | stats_date | total_account_count | yt_account_count | yt_view_count | yt_like_count | dy_account_count | dy_view_count | dy_like_count
--------|------------|---------------------|------------------|---------------|---------------|------------------|---------------|---------------
42      | 2024-12-09 | 15                  | 5                | 1200          | 80            | 4                | 8000          | 320
```

**回传数据计算**:
- `yt_account_count` 回传: 5 + 4 = 9
- `yt_view_count` 回传: 1200 + 8000 = 9200
- `yt_like_count` 回传: 80 + 320 = 400

---

## 📝 注意事项

### 1. 数据一致性

- 本地存储的 `dy_*` 字段是**原始数据**
- 回传的 `yt_*` 字段是**合并数据**（YouTube + 抖音）
- 两者不冲突，各有用途

### 2. 平台识别

抖音平台识别关键词：
- `douyin`
- `dy`

用户提交时选择的平台字段包含以上关键词即识别为抖音。

### 3. 数据抓取

抖音数据通过TikHub API抓取，需要配置：
```bash
TIKHUB_API_KEY=your_tikhub_api_key
```

### 4. 向后兼容

如果未来X2C Pool支持抖音字段（`dy_*`），可以轻松修改回传逻辑：
1. 移除 `daily_stats_scanner.py` 第403-421行的累加逻辑
2. 恢复单独回传 `dy_*` 字段
3. 本地数据已完整保存，无需重新抓取

---

## 🔄 未来扩展

### 如果X2C Pool支持dy_*字段

**只需修改回传逻辑**，无需修改数据存储：

```python
# 恢复单独回传抖音字段
if stats['dy_account_count'] > 0:
    stat_item['dy_account_count'] = stats['dy_account_count']
    if stats['dy_view_count'] > 0:
        stat_item['dy_view_count'] = stats['dy_view_count']
    if stats['dy_like_count'] > 0:
        stat_item['dy_like_count'] = stats['dy_like_count']
    # 抖音特有字段
    if stats['dy_comment_count'] > 0:
        stat_item['dy_comment_count'] = stats['dy_comment_count']
    if stats['dy_share_count'] > 0:
        stat_item['dy_share_count'] = stats['dy_share_count']
    if stats['dy_collect_count'] > 0:
        stat_item['dy_collect_count'] = stats['dy_collect_count']
```

**优势**:
- 本地数据已完整保存
- 历史数据可以重新回传
- 无需重新抓取视频数据

---

## 📞 技术支持

### 相关文档

- **每日汇总功能**: `DAILY_STATS_README.md`
- **视频数据抓取**: `VIDEO_STATS_FETCHER_README.md`
- **X2C平台对接**: `X2C平台对接文档_最终版.md`
- **项目交接**: `HANDOVER.md`

### 调试命令

```bash
# 查看实时回传日志
tail -f /var/log/dramarelay_bot.log | grep "webhook"

# 查看每日汇总日志
tail -f /home/ubuntu/telegram-bot-dramarelay/daily_stats.log

# 查询抖音完成记录
psql $DATABASE_URL -c "SELECT user_id, platform, verification_details FROM user_tasks WHERE platform LIKE '%douyin%' LIMIT 10;"

# 查询抖音每日统计
psql $DATABASE_URL -c "SELECT * FROM task_daily_stats WHERE dy_account_count > 0 ORDER BY stats_date DESC LIMIT 10;"
```

---

## 📋 总结

### 核心策略

**抖音数据 = 本地完整存储 + 回传计入总量**

### 实现方式

1. **本地**: 完整保存抖音数据到 `verification_details` 和 `task_daily_stats`
2. **回传**: 抖音数据计入 `yt_*` 字段回传给X2C Pool
3. **展示**: 管理后台可以查看抖音详细数据

### 优势

- ✅ X2C Pool无需任何修改
- ✅ 本地数据完整保留
- ✅ 回传数据准确统计
- ✅ 未来易于扩展

---

**文档版本**: 1.0  
**最后更新**: 2024-12-10  
**维护者**: DramaRelay Bot Team
