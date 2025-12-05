#!/usr/bin/env python3
"""
测试 TikTok oEmbed API
"""
import asyncio
import aiohttp
from urllib.parse import quote

async def test_oembed(url):
    """测试 oEmbed API"""
    print(f"🔍 测试链接: {url}")
    
    # 构建 oEmbed API URL
    oembed_url = f"https://www.tiktok.com/oembed?url={quote(url)}"
    print(f"📡 API URL: {oembed_url}")
    
    # 添加完整的 HTTP 头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.tiktok.com/'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"\n📥 响应状态码: {response.status}")
                print(f"📋 响应头: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ 成功获取数据!")
                    print(f"📝 标题: {data.get('title', 'N/A')}")
                    print(f"👤 作者: {data.get('author_name', 'N/A')}")
                    print(f"\n完整数据:")
                    import json
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    error_text = await response.text()
                    print(f"\n❌ 请求失败!")
                    print(f"错误详情: {error_text}")
                    
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    url = "https://www.tiktok.com/@wu.roger7/video/7579119977337294093"
    asyncio.run(test_oembed(url))
