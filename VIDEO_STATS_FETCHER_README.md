# 视频统计数据抓取器使用文档

## 📋 概述

`video_stats_fetcher.py` 是一个统一的视频数据抓取工具，支持以下平台：

- ✅ **TikTok** - 使用 TikTok oEmbed API
- ✅ **YouTube** - 使用 YouTube Data API v3
- ✅ **抖音 (Douyin)** - 使用 TikHub API

---

## 🔧 配置

### 1. 环境变量配置

在 `.env` 文件或环境变量中设置：

```bash
# TikHub API Key（用于抖音）
TIKHUB_API_KEY=your_tikhub_api_key

# YouTube Data API v3 Key
YOUTUBE_API_KEY=your_youtube_api_key
```

### 2. 已测试的API Keys

```python
# TikHub API Key
TIKHUB_API_KEY = "0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA=="

# YouTube API Key
YOUTUBE_API_KEY = "AIzaSyByw_ZPNgSCxkkvHCzmHx8R0wZ_8bc0Yi0"
```

---

## 📦 依赖安装

```bash
# 安装必要的依赖
sudo pip3 install aiohttp google-api-python-client
```

---

## 🚀 使用方法

### 方法1：使用便捷函数

```python
import asyncio
from video_stats_fetcher import get_video_stats

async def main():
    # 自动识别平台
    result = await get_video_stats("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    if result['success']:
        print(f"播放量: {result['view_count']:,}")
        print(f"点赞数: {result['like_count']:,}")
        print(f"评论数: {result['comment_count']:,}")
    else:
        print(f"错误: {result['error']}")

asyncio.run(main())
```

### 方法2：使用类实例

```python
import asyncio
from video_stats_fetcher import VideoStatsFetcher

async def main():
    # 创建抓取器实例
    fetcher = VideoStatsFetcher(
        tikhub_api_key="your_tikhub_key",
        youtube_api_key="your_youtube_key"
    )
    
    # 抓取数据
    result = await fetcher.fetch_video_stats("https://v.douyin.com/xxx/")
    
    if result['success']:
        print(f"平台: {result['platform']}")
        print(f"标题: {result['title']}")
        print(f"作者: {result['author']}")
        print(f"播放量: {result['view_count']:,}")

asyncio.run(main())
```

### 方法3：指定平台

```python
import asyncio
from video_stats_fetcher import get_video_stats

async def main():
    # 手动指定平台
    result = await get_video_stats(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        platform="youtube"
    )

asyncio.run(main())
```

---

## 📊 返回数据格式

### 成功时返回

```python
{
    'success': True,
    'platform': 'YouTube',  # 或 'TikTok', '抖音'
    'video_id': 'dQw4w9WgXcQ',
    'title': '视频标题',
    'author': '作者名称',
    'view_count': 1721119540,      # 播放量
    'like_count': 18672287,        # 点赞数
    'comment_count': 2408547,      # 评论数
    'share_count': 0,              # 分享数（部分平台）
    'collect_count': 0,            # 收藏数（抖音）
    'error': None
}
```

### 失败时返回

```python
{
    'success': False,
    'platform': 'YouTube',
    'video_id': '',
    'title': '',
    'author': '',
    'view_count': 0,
    'like_count': 0,
    'comment_count': 0,
    'share_count': 0,
    'error': '错误信息'
}
```

---

## 🎯 平台特性

### TikTok

- **API**: TikTok oEmbed API
- **优点**: 免费，无需API Key
- **缺点**: **不提供播放量数据**
- **可获取**: 标题、作者
- **示例链接**: `https://www.tiktok.com/@user/video/123456`

### YouTube

- **API**: YouTube Data API v3
- **优点**: 官方API，数据完整
- **缺点**: 需要API Key，有配额限制（每天10,000）
- **可获取**: 标题、作者、播放量、点赞数、评论数
- **示例链接**: 
  - `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
  - `https://youtu.be/dQw4w9WgXcQ`

### 抖音 (Douyin)

- **API**: TikHub API
- **优点**: 数据完整，支持播放量
- **缺点**: 需要API Key，按调用计费
- **可获取**: 标题、作者、播放量、点赞数、评论数、分享数、收藏数
- **示例链接**: `https://v.douyin.com/xxx/`

---

## 🧪 测试结果

### YouTube API 测试 ✅

```
视频: Rick Astley - Never Gonna Give You Up
播放量: 1,721,119,540
点赞数: 18,672,287
评论数: 2,408,547
```

### 抖音 API 测试 ✅

```
视频: 用"高启强"视角打开"鱼贩"的逆袭人生
点赞数: 418,725
评论数: 11,648
分享数: 30,876
收藏数: 71,610
播放量: 0 (未公开)
```

---

## 🔄 管理后台刷新按钮

### 按钮功能

从截图中可以看到管理后台有两个刷新按钮：

1. **🔄 刷新数据** - 手动刷新
2. **⏱️ 自动刷新 (30s)** - 自动定时刷新

### 调用方法

#### 1. 手动刷新数据

```javascript
// 在浏览器控制台或HTML中调用
refreshData();
```

**功能说明**：
- 刷新统计数据
- 刷新Webhook日志
- 刷新任务完成记录
- 刷新任务列表

**代码位置**: `/home/ubuntu/telegram-bot-dramarelay/templates/admin.html` 第862行

```javascript
function refreshData() {
    loadStats();
    loadWebhooks();
    loadCompletions();
    loadTasks();
}
```

#### 2. 自动刷新

```javascript
// 在浏览器控制台或HTML中调用
autoRefresh();
```

**功能说明**：
- 第一次点击：启动自动刷新（每30秒）
- 第二次点击：停止自动刷新

**代码位置**: `/home/ubuntu/telegram-bot-dramarelay/templates/admin.html` 第870行

```javascript
function autoRefresh() {
    if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
        alert('已停止自动刷新');
    } else {
        autoRefreshTimer = setInterval(refreshData, 30000);
        alert('已启动自动刷新 (每 30 秒)');
        refreshData();
    }
}
```

#### 3. HTML按钮绑定

```html
<!-- 手动刷新按钮 -->
<button onclick="refreshData()">🔄 刷新数据</button>

<!-- 自动刷新按钮 -->
<button onclick="autoRefresh()">⏱️ 自动刷新 (30s)</button>
```

**代码位置**: `/home/ubuntu/telegram-bot-dramarelay/templates/admin.html` 第515-516行

---

## 💡 使用建议

### 1. API配额管理

**YouTube API**:
- 每天有10,000配额
- 每次查询消耗约1-50配额
- 建议缓存结果，避免重复查询

**TikHub API**:
- 按调用次数计费
- 提供24小时缓存
- 建议使用缓存URL避免重复计费

### 2. 错误处理

```python
result = await get_video_stats(url)

if not result['success']:
    if 'API Key' in result['error']:
        print("请检查API Key配置")
    elif '404' in result['error']:
        print("视频不存在或已删除")
    else:
        print(f"其他错误: {result['error']}")
```

### 3. 批量处理

```python
async def batch_fetch(urls):
    fetcher = VideoStatsFetcher(
        tikhub_api_key="xxx",
        youtube_api_key="xxx"
    )
    
    results = []
    for url in urls:
        result = await fetcher.fetch_video_stats(url)
        results.append(result)
        
        # 避免频率限制
        await asyncio.sleep(1)
    
    return results
```

---

## 🐛 常见问题

### Q1: YouTube API返回403错误？
**A**: 检查API Key是否正确，是否超出配额限制

### Q2: 抖音返回502错误？
**A**: TikHub服务可能临时不可用，稍后重试

### Q3: TikTok无法获取播放量？
**A**: TikTok oEmbed API不提供播放量数据，这是正常的

### Q4: 如何获取更多平台的数据？
**A**: 可以扩展 `VideoStatsFetcher` 类，添加新的平台支持

---

## 📝 完整示例

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整使用示例"""

import asyncio
from video_stats_fetcher import VideoStatsFetcher

async def main():
    # 初始化
    fetcher = VideoStatsFetcher(
        tikhub_api_key="0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA==",
        youtube_api_key="AIzaSyByw_ZPNgSCxkkvHCzmHx8R0wZ_8bc0Yi0"
    )
    
    # 测试不同平台
    urls = {
        'YouTube': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'TikTok': 'https://www.tiktok.com/@user/video/123',
        '抖音': 'https://v.douyin.com/BhhWB8WvKJQ/'
    }
    
    for platform, url in urls.items():
        print(f"\n{'='*60}")
        print(f"平台: {platform}")
        print(f"链接: {url}")
        print('-'*60)
        
        result = await fetcher.fetch_video_stats(url)
        
        if result['success']:
            print(f"✅ 成功")
            print(f"标题: {result['title'][:50]}...")
            print(f"作者: {result['author']}")
            print(f"播放量: {result['view_count']:,}")
            print(f"点赞数: {result['like_count']:,}")
        else:
            print(f"❌ 失败: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📞 技术支持

如有问题，请查看：
1. API Key是否正确配置
2. 依赖是否正确安装
3. 网络连接是否正常
4. API配额是否充足

---

## 🔗 相关链接

- **TikHub官网**: https://tikhub.io/
- **YouTube Data API**: https://developers.google.com/youtube/v3
- **TikTok oEmbed**: https://www.tiktok.com/oembed

---

## 📄 许可证

本项目遵循项目主许可证。
