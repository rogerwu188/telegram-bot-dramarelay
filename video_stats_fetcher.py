#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频统计数据抓取器
支持 TikTok、YouTube、抖音 三个平台
"""

import os
import re
import logging
import aiohttp
from typing import Optional, Dict
from urllib.parse import quote, urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class VideoStatsFetcher:
    """统一的视频统计数据抓取器"""
    
    def __init__(self, 
                 tikhub_api_key: Optional[str] = None,
                 youtube_api_key: Optional[str] = None):
        """
        初始化抓取器
        
        Args:
            tikhub_api_key: TikHub API Key（用于抖音）
            youtube_api_key: YouTube Data API v3 Key
        """
        self.tikhub_api_key = tikhub_api_key or os.getenv('TIKHUB_API_KEY')
        self.youtube_api_key = youtube_api_key or os.getenv('YOUTUBE_API_KEY')
        
        # TikHub配置
        self.tikhub_base_url = "https://api.tikhub.io/api/v1"
        self.tikhub_headers = {
            "Authorization": f"Bearer {self.tikhub_api_key}",
            "Content-Type": "application/json"
        } if self.tikhub_api_key else None
        
        # YouTube配置
        self.youtube = None
        if self.youtube_api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.youtube_api_key)
            except Exception as e:
                logger.error(f"YouTube API 初始化失败: {e}")
    
    async def fetch_video_stats(self, url: str, platform: Optional[str] = None) -> Dict:
        """
        统一接口：获取视频统计数据
        
        Args:
            url: 视频链接
            platform: 平台名称（可选，会自动识别）
        
        Returns:
            dict: {
                'success': bool,
                'platform': str,
                'video_id': str,
                'title': str,
                'author': str,
                'view_count': int,
                'like_count': int,
                'comment_count': int,
                'share_count': int,
                'error': str (if failed)
            }
        """
        # 自动识别平台
        if not platform:
            platform = self._detect_platform(url)
        
        if not platform:
            return {
                'success': False,
                'error': '无法识别平台'
            }
        
        platform_lower = platform.lower()
        
        try:
            if platform_lower in ['tiktok', 'tt']:
                return await self._fetch_tiktok_stats(url)
            elif platform_lower in ['youtube', 'yt']:
                return await self._fetch_youtube_stats(url)
            elif platform_lower in ['douyin', 'dy']:
                return await self._fetch_douyin_stats(url)
            else:
                return {
                    'success': False,
                    'error': f'不支持的平台: {platform}'
                }
        except Exception as e:
            logger.error(f"获取视频数据失败: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_platform(self, url: str) -> Optional[str]:
        """自动识别平台"""
        url_lower = url.lower()
        
        if 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'douyin.com' in url_lower or 'v.douyin.com' in url_lower:
            return 'douyin'
        
        return None
    
    async def _fetch_tiktok_stats(self, url: str) -> Dict:
        """
        获取TikTok视频数据（使用oEmbed API）
        
        注意：TikTok oEmbed API 不提供播放量数据
        """
        result = {
            'success': False,
            'platform': 'TikTok',
            'video_id': '',
            'title': '',
            'author': '',
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'error': None
        }
        
        try:
            # 构建 oEmbed API URL
            oembed_url = f"https://www.tiktok.com/oembed?url={quote(url)}"
            logger.info(f"📡 调用 TikTok oEmbed API: {oembed_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result['title'] = data.get('title', '')
                        result['author'] = data.get('author_name', '')
                        result['video_id'] = self._extract_tiktok_id(url)
                        result['success'] = True
                        
                        logger.info(f"✅ TikTok 数据获取成功: {result['title']}")
                    else:
                        result['error'] = f"API 返回错误: {response.status}"
                        logger.error(f"❌ TikTok oEmbed API 错误: {response.status}")
                        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ TikTok 数据获取失败: {e}")
        
        return result
    
    async def _fetch_youtube_stats(self, url: str) -> Dict:
        """
        获取YouTube视频数据（使用YouTube Data API v3）
        """
        result = {
            'success': False,
            'platform': 'YouTube',
            'video_id': '',
            'title': '',
            'author': '',
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'error': None
        }
        
        if not self.youtube:
            result['error'] = 'YouTube API 未配置'
            logger.error("❌ YouTube API Key 未设置")
            return result
        
        try:
            # 提取视频ID
            video_id = self._extract_youtube_id(url)
            if not video_id:
                result['error'] = '无法提取YouTube视频ID'
                return result
            
            result['video_id'] = video_id
            logger.info(f"📡 调用 YouTube Data API: video_id={video_id}")
            
            # 调用YouTube API
            request = self.youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                result['error'] = '视频不存在或已删除'
                logger.error(f"❌ YouTube 视频不存在: {video_id}")
                return result
            
            # 提取数据
            video_data = response['items'][0]
            snippet = video_data.get('snippet', {})
            statistics = video_data.get('statistics', {})
            
            result['title'] = snippet.get('title', '')
            result['author'] = snippet.get('channelTitle', '')
            result['view_count'] = int(statistics.get('viewCount', 0))
            result['like_count'] = int(statistics.get('likeCount', 0))
            result['comment_count'] = int(statistics.get('commentCount', 0))
            result['success'] = True
            
            logger.info(f"✅ YouTube 数据获取成功: {result['title']} (播放量: {result['view_count']:,})")
            
        except HttpError as e:
            result['error'] = f"YouTube API 错误: {e.resp.status}"
            logger.error(f"❌ YouTube API 错误: {e}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ YouTube 数据获取失败: {e}")
        
        return result
    
    async def _fetch_douyin_stats(self, url: str) -> Dict:
        """
        获取抖音视频数据（使用TikHub API）
        """
        result = {
            'success': False,
            'platform': '抖音',
            'video_id': '',
            'title': '',
            'author': '',
            'view_count': 0,
            'like_count': 0,
            'comment_count': 0,
            'share_count': 0,
            'collect_count': 0,
            'error': None
        }
        
        if not self.tikhub_api_key:
            result['error'] = 'TikHub API Key 未配置'
            logger.error("❌ TikHub API Key 未设置")
            return result
        
        try:
            # 提取视频ID
            video_id = await self._extract_douyin_id(url)
            if not video_id:
                result['error'] = '无法提取抖音视频ID'
                return result
            
            result['video_id'] = video_id
            logger.info(f"📡 调用 TikHub API: video_id={video_id}")
            
            # 调用TikHub API
            endpoint = f"{self.tikhub_base_url}/douyin/web/fetch_one_video"
            params = {"aweme_id": video_id}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers=self.tikhub_headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        result['error'] = f"API 返回错误: {response.status}"
                        logger.error(f"❌ TikHub API 错误: {response.status}")
                        return result
                    
                    data = await response.json()
                    
                    if 'data' not in data or not data['data']:
                        result['error'] = 'API 返回数据为空'
                        logger.error("❌ TikHub API 返回数据为空")
                        return result
                    
                    # 提取数据
                    aweme_detail = data['data'].get('aweme_detail', data['data'])
                    statistics = aweme_detail.get('statistics', {})
                    author = aweme_detail.get('author', {})
                    
                    result['title'] = aweme_detail.get('desc', '')
                    result['author'] = author.get('nickname', '')
                    result['view_count'] = statistics.get('play_count', 0)
                    result['like_count'] = statistics.get('digg_count', 0)
                    result['comment_count'] = statistics.get('comment_count', 0)
                    result['share_count'] = statistics.get('share_count', 0)
                    result['collect_count'] = statistics.get('collect_count', 0)
                    result['success'] = True
                    
                    logger.info(f"✅ 抖音数据获取成功: {result['title']} (点赞: {result['like_count']:,})")
                    
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ 抖音数据获取失败: {e}")
        
        return result
    
    def _extract_tiktok_id(self, url: str) -> str:
        """提取TikTok视频ID"""
        match = re.search(r'/video/(\d+)', url)
        return match.group(1) if match else ''
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """提取YouTube视频ID"""
        # 解析URL
        parsed_url = urlparse(url)
        
        # youtube.com/watch?v=VIDEO_ID
        if 'youtube.com' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params:
                return query_params['v'][0]
            
            # youtube.com/shorts/VIDEO_ID
            match = re.search(r'/shorts/([a-zA-Z0-9_-]+)', url)
            if match:
                return match.group(1)
        
        # youtu.be/VIDEO_ID
        elif 'youtu.be' in parsed_url.netloc:
            return parsed_url.path.strip('/')
        
        return None
    
    async def _extract_douyin_id(self, url: str) -> Optional[str]:
        """提取抖音视频ID（支持短链接跳转）"""
        try:
            # 如果是短链接，先跳转获取真实URL
            if 'v.douyin.com' in url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        url = str(response.url)
            
            # 从URL中提取视频ID
            match = re.search(r'/video/(\d+)', url)
            return match.group(1) if match else None
            
        except Exception as e:
            logger.error(f"提取抖音视频ID失败: {e}")
            return None


# 便捷函数
async def get_video_stats(url: str, 
                         platform: Optional[str] = None,
                         tikhub_api_key: Optional[str] = None,
                         youtube_api_key: Optional[str] = None) -> Dict:
    """
    便捷函数：获取视频统计数据
    
    Args:
        url: 视频链接
        platform: 平台名称（可选）
        tikhub_api_key: TikHub API Key（可选）
        youtube_api_key: YouTube API Key（可选）
    
    Returns:
        dict: 视频统计数据
    
    Example:
        >>> result = await get_video_stats("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        >>> print(f"播放量: {result['view_count']:,}")
    """
    fetcher = VideoStatsFetcher(
        tikhub_api_key=tikhub_api_key,
        youtube_api_key=youtube_api_key
    )
    return await fetcher.fetch_video_stats(url, platform)


if __name__ == "__main__":
    import asyncio
    
    async def test():
        """测试函数"""
        # 配置API Keys
        tikhub_key = os.getenv('TIKHUB_API_KEY', '0qgoA8oN63S7oWnMPpmXzhnWH2SlYZlE2jDzjEWuT6Tmh0ydLHaxSTW7aA==')
        youtube_key = os.getenv('YOUTUBE_API_KEY', '')  # 需要配置
        
        fetcher = VideoStatsFetcher(
            tikhub_api_key=tikhub_key,
            youtube_api_key=youtube_key
        )
        
        # 测试链接
        test_urls = [
            "https://www.tiktok.com/@zachking/video/7377841390736166186",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://v.douyin.com/BhhWB8WvKJQ/"
        ]
        
        for url in test_urls:
            print(f"\n{'='*70}")
            print(f"测试链接: {url}")
            print('-'*70)
            
            result = await fetcher.fetch_video_stats(url)
            
            if result['success']:
                print(f"✅ 平台: {result['platform']}")
                print(f"📝 标题: {result['title']}")
                print(f"👤 作者: {result['author']}")
                print(f"👁️  播放量: {result['view_count']:,}")
                print(f"❤️  点赞数: {result['like_count']:,}")
                print(f"💬 评论数: {result['comment_count']:,}")
            else:
                print(f"❌ 失败: {result['error']}")
    
    asyncio.run(test())
