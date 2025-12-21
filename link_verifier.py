#!/usr/bin/env python3
"""
链接验证模块
使用 TikTok oEmbed API 和简单 HTTP 请求验证视频链接
"""
import os
import re
import logging
import asyncio
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
        使用 TikTok oEmbed API 验证链接（带自动重试机制）
        
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
        
        # 构建 oEmbed API URL
        oembed_url = f"https://www.tiktok.com/oembed?url={quote(url)}"
        logger.info(f"📡 调用 TikTok oEmbed API: {oembed_url}")
        
        # 发送 HTTP GET 请求（添加 User-Agent 头，避免被 TikTok 拒绝）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        # 自动重试机制：最多重试 3 次，每次间隔 60 秒
        # TikTok oEmbed API 有时会随机返回 400 错误，较长的重试间隔可以提高成功率
        max_retries = 3
        retry_delay = 60
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info(f"✅ oEmbed API 返回成功 (第 {attempt + 1} 次尝试)")
                            
                            # 提取标题和作者
                            title = data.get('title', '')
                            author_name = data.get('author_name', '')
                            
                            result['page_title'] = title
                            result['page_text'] = f"{title} {author_name}"
                            
                            logger.info(f"📝 视频标题: {title}")
                            logger.info(f"👤 作者: {author_name}")
                            
                            # 验证关键词匹配（使用严格模式）
                            match_result = self._check_keywords_match_strict(
                                result['page_text'],
                                task_title,
                                task_description
                            )
                            result['matched'] = match_result['matched']
                            
                            # 如果不匹配，设置错误原因
                            if not result['matched']:
                                result['error'] = match_result.get('reason', '内容不匹配')
                            
                            result['success'] = True
                            return result  # 成功，直接返回
                        else:
                            last_error = f"API 返回错误: {response.status}"
                            logger.warning(f"⚠️ oEmbed API 返回错误: {response.status} (第 {attempt + 1}/{max_retries} 次尝试)")
                            
                            # 如果不是最后一次尝试，等待后重试
                            if attempt < max_retries - 1:
                                logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                                await asyncio.sleep(retry_delay)
                            
            except aiohttp.ClientError as e:
                last_error = f"网络请求失败: {str(e)}"
                logger.warning(f"⚠️ 网络请求失败: {e} (第 {attempt + 1}/{max_retries} 次尝试)")
                
                if attempt < max_retries - 1:
                    logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                    await asyncio.sleep(retry_delay)
                    
            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ oEmbed 验证失败: {e} (第 {attempt + 1}/{max_retries} 次尝试)", exc_info=True)
                
                if attempt < max_retries - 1:
                    logger.info(f"⏳ 等待 {retry_delay} 秒后重试...")
                    await asyncio.sleep(retry_delay)
        
        # 所有重试都失败
        logger.error(f"❌ oEmbed API 连续 {max_retries} 次失败, URL: {url}")
        result['error'] = last_error
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
    
    def _extract_drama_name(self, task_title: str) -> str:
        """
        从任务标题中提取剧名（《》中的内容）
        
        Args:
            task_title: 任务标题
        
        Returns:
            str: 剧名，如果没有则返回空字符串
        """
        match = re.search(r'《(.+?)》', task_title)
        if match:
            return match.group(1)
        return ''
    
    def _extract_core_keywords(self, task_title: str, task_description: str) -> list:
        """
        提取核心关键词（更严格的提取逻辑）
        
        Args:
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            list: 核心关键词列表
        """
        keywords = []
        
        # 1. 提取剧名（最重要的关键词）
        drama_name = self._extract_drama_name(task_title)
        if drama_name:
            keywords.append(drama_name)
            # 剧名可能有多个词，也单独添加
            drama_words = re.findall(r'[\u4e00-\u9fff]{2,}', drama_name)
            keywords.extend(drama_words)
        
        # 2. 提取标题中的中文词组（至少3个字）
        title_words = re.findall(r'[\u4e00-\u9fff]{3,}', task_title)
        keywords.extend(title_words)
        
        # 3. 提取描述中的中文词组（至少3个字）
        desc_words = re.findall(r'[\u4e00-\u9fff]{3,}', task_description)
        keywords.extend(desc_words)
        
        # 4. 提取 hashtag 标签（如果有）
        hashtags = re.findall(r'#([\w\u4e00-\u9fff]+)', task_description)
        keywords.extend([tag for tag in hashtags if len(tag) >= 2])
        
        # 去重并过滤常见词
        common_words = {'视频', '链接', '任务', '完成', '提交', '下载', '上传', '平台', '内容', '分发', '奖励', '获得', '可以', '请求', '系统', '用户'}
        keywords = list(set([kw for kw in keywords if kw not in common_words and len(kw) >= 2]))
        
        logger.info(f"🔑 提取到的核心关键词: {keywords}")
        return keywords
    
    def _check_keywords_match_strict(self, page_text: str, task_title: str, task_description: str) -> dict:
        """
        严格检查页面文本是否包含任务关键词
        
        匹配规则：
        1. 如果任务标题包含剧名（《》），则必须匹配剧名
        2. 否则，需要匹配至少2个核心关键词
        
        Args:
            page_text: 页面文本内容
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            dict: {'matched': bool, 'reason': str}
        """
        if not page_text:
            logger.warning("⚠️ 页面文本为空，默认不匹配")
            return {'matched': False, 'reason': '无法获取视频标题信息'}
        
        page_text_lower = page_text.lower()
        
        # 1. 首先检查剧名匹配（最严格的检查）
        drama_name = self._extract_drama_name(task_title)
        if drama_name:
            logger.info(f"🎬 检查剧名匹配: {drama_name}")
            if drama_name.lower() in page_text_lower:
                logger.info(f"✅ 剧名匹配成功: {drama_name}")
                return {'matched': True, 'reason': ''}
            else:
                # 剧名不匹配，检查剧名的部分词是否匹配
                drama_words = re.findall(r'[\u4e00-\u9fff]{2,}', drama_name)
                matched_drama_words = [w for w in drama_words if w.lower() in page_text_lower]
                if len(matched_drama_words) >= 2:
                    logger.info(f"✅ 剧名部分匹配成功: {matched_drama_words}")
                    return {'matched': True, 'reason': ''}
                logger.warning(f"⚠️ 剧名不匹配: 期望 '{drama_name}'，实际 '{page_text[:100]}'")
                return {
                    'matched': False, 
                    'reason': f'视频标题中未找到剧名《{drama_name}》，请确保提交的是正确的剧集视频'
                }
        
        # 2. 提取核心关键词
        keywords = self._extract_core_keywords(task_title, task_description)
        
        if not keywords:
            logger.warning("⚠️ 未提取到关键词，默认不匹配")
            return {'matched': False, 'reason': '无法提取任务关键词'}
        
        # 3. 检查关键词匹配（需要匹配至少2个）
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in page_text_lower:
                matched_keywords.append(keyword)
        
        logger.info(f"📊 匹配到的关键词: {matched_keywords} / {len(keywords)}")
        
        # 需要匹配至少1个关键词，如果有多个关键词则需要匹配至少2个
        # 使用 min(2, len(keywords)) 确保不会要求匹配比实际关键词数量更多的数量
        min_match_count = min(2, len(keywords))
        
        if len(matched_keywords) >= min_match_count:
            logger.info(f"✅ 关键词匹配成功: 匹配 {len(matched_keywords)} 个，要求 {min_match_count} 个")
            return {'matched': True, 'reason': ''}
        else:
            logger.warning(f"⚠️ 关键词匹配失败: 匹配 {len(matched_keywords)} 个，要求 {min_match_count} 个")
            return {
                'matched': False, 
                'reason': f'视频标题与任务内容不匹配，请确保提交的是正确的任务视频'
            }
    
    def _check_keywords_match(self, page_text: str, task_title: str, task_description: str) -> bool:
        """
        检查页面文本是否包含任务关键词（旧版本，保留兼容）
        现在调用严格版本
        """
        result = self._check_keywords_match_strict(page_text, task_title, task_description)
        return result['matched']
