#!/usr/bin/env python3
"""
链接验证模块
使用 TikTok oEmbed API 和简单 HTTP 请求验证视频链接
"""
import os
import re
import logging
import aiohttp
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

class LinkVerifier:
    """视频链接验证器（使用 API 和 HTTP 请求）"""
    
    def __init__(self, screenshots_dir="/tmp/screenshots"):
        """初始化验证器"""
        self.screenshots_dir = screenshots_dir
        os.makedirs(screenshots_dir, exist_ok=True)
    
    def validate_platform_url(self, url: str, platform: str) -> dict:
        """
        验证链接是否为指定平台的合法链接
        
        Args:
            url: 要验证的链接
            platform: 平台名称 (tiktok, youtube, instagram, facebook, twitter)
        
        Returns:
            dict: {'valid': bool, 'error_message': str}
        """
        url_lower = url.lower()
        platform_lower = platform.lower()  # 转换为小写
        
        platform_patterns = {
            'tiktok': ['tiktok.com'],
            'douyin': ['douyin.com', 'v.douyin.com'],
            'youtube': ['youtube.com', 'youtu.be'],
            'instagram': ['instagram.com'],
            'facebook': ['facebook.com', 'fb.com', 'fb.watch'],
            'twitter': ['twitter.com', 'x.com']
        }
        
        if platform_lower not in platform_patterns:
            return {
                'valid': False,
                'error_message': f'不支持的平台: {platform}'
            }
        
        patterns = platform_patterns[platform_lower]
        for pattern in patterns:
            if pattern in url_lower:
                return {'valid': True, 'error_message': ''}
        
        # 链接不匹配
        platform_names = {
            'tiktok': 'TikTok',
            'youtube': 'YouTube',
            'instagram': 'Instagram',
            'facebook': 'Facebook',
            'twitter': 'Twitter/X'
        }
        
        expected_domains = ' 或 '.join(patterns)
        return {
            'valid': False,
            'error_message': f'请提供正确的 {platform_names.get(platform, platform)} 链接（应包含 {expected_domains}）'
        }
    
    async def verify_link(self, url: str, task_title: str, task_description: str, timeout: int = 20000) -> dict:
        """
        验证视频链接 - 检查描述和标签是否包含任务关键词
        
        Args:
            url: 用户提交的视频链接
            task_title: 任务标题（用于关键词匹配）
            task_description: 任务描述（用于关键词匹配）
            timeout: 请求超时时间（毫秒）
        
        Returns:
            dict: {
                'success': bool,  # 验证是否成功
                'matched': bool,  # 是否匹配任务关键词
                'screenshot_path': str,  # 截图路径（已弃用）
                'page_title': str,  # 页面标题
                'page_text': str,  # 页面文本内容（描述+标签）
                'error': str  # 错误信息（如果有）
            }
        """
        result = {
            'success': False,
            'matched': False,
            'screenshot_path': None,
            'page_title': '',
            'page_text': '',
            'error': None
        }
        
        try:
            logger.info(f"🔍 开始验证链接: {url}")
            
            # 判断平台
            if 'tiktok.com' in url.lower():
                # 使用 TikTok oEmbed API
                result = await self._verify_tiktok_oembed(url, task_title, task_description)
            elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
                # YouTube 验证（简化版）
                result = await self._verify_youtube(url, task_title, task_description)
            else:
                # 其他平台使用通用验证
                result = await self._verify_generic(url, task_title, task_description)
            
            logger.info(f"✅ 验证完成，匹配结果: {result['matched']}")
            
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    async def _verify_tiktok_oembed(self, url: str, task_title: str, task_description: str) -> dict:
        """
        使用 TikTok oEmbed API 验证链接
        
        Args:
            url: TikTok 视频链接
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            dict: 验证结果
        """
        result = {
            'success': False,
            'matched': False,
            'screenshot_path': None,
            'page_title': '',
            'page_text': '',
            'error': None
        }
        
        try:
            # 构建 oEmbed API URL
            oembed_url = f"https://www.tiktok.com/oembed?url={quote(url)}"
            logger.info(f"📡 调用 TikTok oEmbed API: {oembed_url}")
            
            # 发送 HTTP GET 请求
            async with aiohttp.ClientSession() as session:
                async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ oEmbed API 返回成功")
                        
                        # 提取标题和作者
                        title = data.get('title', '')
                        author_name = data.get('author_name', '')
                        
                        result['page_title'] = title
                        result['page_text'] = f"{title} {author_name}"
                        
                        logger.info(f"📝 视频标题: {title}")
                        logger.info(f"👤 作者: {author_name}")
                        
                        # 验证关键词匹配
                        result['matched'] = self._check_keywords_match(
                            result['page_text'],
                            task_title,
                            task_description
                        )
                        
                        result['success'] = True
                    else:
                        logger.error(f"❌ oEmbed API 返回错误: {response.status}")
                        result['error'] = f"API 返回错误: {response.status}"
                        
        except aiohttp.ClientError as e:
            logger.error(f"❌ 网络请求失败: {e}")
            result['error'] = f"网络请求失败: {str(e)}"
        except Exception as e:
            logger.error(f"❌ oEmbed 验证失败: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    async def _verify_youtube(self, url: str, task_title: str, task_description: str) -> dict:
        """
        验证 YouTube 链接（简化版）
        
        Args:
            url: YouTube 视频链接
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            dict: 验证结果
        """
        result = {
            'success': True,
            'matched': True,  # YouTube 暂时默认通过
            'screenshot_path': None,
            'page_title': 'YouTube Video',
            'page_text': 'YouTube Video',
            'error': None
        }
        
        logger.info(f"✅ YouTube 链接验证通过（简化模式）")
        return result
    
    async def _verify_generic(self, url: str, task_title: str, task_description: str) -> dict:
        """
        通用链接验证（简化版）
        
        Args:
            url: 视频链接
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            dict: 验证结果
        """
        result = {
            'success': True,
            'matched': True,  # 其他平台暂时默认通过
            'screenshot_path': None,
            'page_title': 'Video',
            'page_text': 'Video',
            'error': None
        }
        
        logger.info(f"✅ 通用链接验证通过（简化模式）")
        return result
    
    def _check_keywords_match(self, page_text: str, task_title: str, task_description: str) -> bool:
        """
        检查页面文本是否包含任务关键词
        
        Args:
            page_text: 页面文本内容
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            bool: 是否匹配
        """
        if not page_text:
            logger.warning("⚠️ 页面文本为空，默认不匹配")
            return False
        
        # 提取关键词（从标题和描述中提取）
        keywords = []
        
        # 从标题中提取关键词（去除标点符号）
        title_words = re.findall(r'[\w\u4e00-\u9fff]+', task_title)
        keywords.extend([w for w in title_words if len(w) > 1])
        
        # 从描述中提取关键词
        desc_words = re.findall(r'[\w\u4e00-\u9fff]+', task_description)
        keywords.extend([w for w in desc_words if len(w) > 1])
        
        # 去重
        keywords = list(set(keywords))
        
        logger.info(f"🔑 提取到的关键词: {keywords}")
        
        # 检查是否有任意关键词匹配
        page_text_lower = page_text.lower()
        matched_keywords = []
        
        for keyword in keywords:
            if keyword.lower() in page_text_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            logger.info(f"✅ 匹配到关键词: {matched_keywords}")
            return True
        else:
            logger.warning(f"⚠️ 未匹配到任何关键词")
            return False
