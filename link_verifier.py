#!/usr/bin/env python3
"""
链接验证模块
使用 Playwright 浏览器自动化验证视频链接的描述和标签（异步版本）
"""
import os
import re
import logging
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

class LinkVerifier:
    """视频链接验证器（使用 Playwright 异步 API）"""
    
    def __init__(self, screenshots_dir="/tmp/screenshots"):
        """初始化验证器"""
        self.screenshots_dir = screenshots_dir
        os.makedirs(screenshots_dir, exist_ok=True)
    
    async def verify_link(self, url: str, task_title: str, task_description: str, timeout: int = 30000) -> dict:
        """
        验证视频链接 - 检查描述和标签是否包含任务关键词
        
        Args:
            url: 用户提交的视频链接
            task_title: 任务标题（用于关键词匹配）
            task_description: 任务描述（用于关键词匹配）
            timeout: 页面加载超时时间（毫秒）
        
        Returns:
            dict: {
                'success': bool,  # 验证是否成功
                'matched': bool,  # 是否匹配任务关键词
                'screenshot_path': str,  # 截图路径
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
            
            async with async_playwright() as p:
                # 启动浏览器（使用 chromium）
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # 访问链接
                logger.info(f"📱 正在访问页面...")
                try:
                    await page.goto(url, timeout=timeout, wait_until='domcontentloaded')
                except PlaywrightTimeout:
                    logger.warning("⚠️ 页面加载超时，继续尝试提取内容...")
                
                # 等待页面渲染（TikTok 需要时间加载动态内容）
                await page.wait_for_timeout(5000)
                
                # 获取页面标题
                result['page_title'] = await page.title()
                logger.info(f"📄 页面标题: {result['page_title']}")
                
                # 提取视频描述和标签
                result['page_text'] = await self._extract_description_and_tags(page, url)
                logger.info(f"📝 提取到的描述和标签: {result['page_text'][:300]}...")
                
                # 截图保存
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_filename = f"verify_{timestamp}.png"
                screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
                
                await page.screenshot(path=screenshot_path, full_page=False)
                result['screenshot_path'] = screenshot_path
                logger.info(f"📸 截图已保存: {screenshot_path}")
                
                await browser.close()
                
                # 验证关键词匹配（只检查描述和标签）
                result['matched'] = self._check_keywords_match(
                    result['page_text'],
                    task_title,
                    task_description
                )
                
                result['success'] = True
                logger.info(f"✅ 验证完成，匹配结果: {result['matched']}")
                
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}", exc_info=True)
            result['error'] = str(e)
        
        return result
    
    async def _extract_description_and_tags(self, page, url: str) -> str:
        """
        提取视频描述和标签
        
        Args:
            page: Playwright page 对象
            url: 视频链接
        
        Returns:
            str: 描述和标签的合并文本
        """
        text_parts = []
        
        # 判断平台
        if 'tiktok.com' in url.lower():
            # TikTok 特定选择器
            selectors = [
                # 视频描述
                '[data-e2e="browse-video-desc"]',
                '[data-e2e="video-desc"]',
                'h1[data-e2e="browse-video-title"]',
                # Meta 标签
                'meta[property="og:description"]',
                'meta[name="description"]',
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith('meta'):
                        content = await page.get_attribute(selector, 'content', timeout=2000)
                        if content:
                            text_parts.append(content)
                            logger.info(f"✓ 提取到 meta 内容: {content[:100]}")
                    else:
                        element = page.locator(selector).first
                        if await element.is_visible(timeout=2000):
                            text = await element.inner_text()
                            if text:
                                text_parts.append(text)
                                logger.info(f"✓ 提取到描述: {text[:100]}")
                except Exception as e:
                    logger.debug(f"选择器 {selector} 未找到: {e}")
                    continue
            
            # 提取标签（hashtags）
            try:
                hashtag_elements = await page.locator('a[href*="/tag/"]').all()
                hashtags = []
                for elem in hashtag_elements[:20]:  # 限制最多20个标签
                    try:
                        tag_text = await elem.inner_text()
                        if tag_text.startswith('#'):
                            hashtags.append(tag_text)
                    except:
                        continue
                
                if hashtags:
                    hashtag_text = ' '.join(hashtags)
                    text_parts.append(hashtag_text)
                    logger.info(f"✓ 提取到标签: {hashtag_text}")
            except Exception as e:
                logger.debug(f"提取标签失败: {e}")
        
        elif 'youtube.com' in url.lower() or 'youtu.be' in url.lower():
            # YouTube 特定选择器
            selectors = [
                '#title h1',
                'yt-formatted-string.ytd-video-primary-info-renderer',
                'meta[property="og:title"]',
                'meta[property="og:description"]',
                'meta[name="description"]',
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith('meta'):
                        content = await page.get_attribute(selector, 'content', timeout=2000)
                        if content:
                            text_parts.append(content)
                    else:
                        element = page.locator(selector).first
                        text = await element.inner_text(timeout=2000)
                        if text:
                            text_parts.append(text)
                except:
                    continue
        
        elif 'instagram.com' in url.lower():
            # Instagram 特定选择器
            selectors = [
                'h1',
                'article h2',
                'meta[property="og:title"]',
                'meta[property="og:description"]',
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith('meta'):
                        content = await page.get_attribute(selector, 'content', timeout=2000)
                        if content:
                            text_parts.append(content)
                    else:
                        element = page.locator(selector).first
                        text = await element.inner_text(timeout=2000)
                        if text:
                            text_parts.append(text)
                except:
                    continue
        
        return ' '.join(text_parts)
    
    def _check_keywords_match(self, page_text: str, task_title: str, task_description: str) -> bool:
        """
        检查描述和标签是否包含任务关键词
        
        Args:
            page_text: 页面文本（描述+标签）
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            bool: 是否匹配
        """
        # 转换为小写
        page_content = page_text.lower()
        
        # 从任务标题和描述中提取关键词
        keywords = set()
        
        # 提取任务标题中的关键词（去除标点符号）
        title_words = re.findall(r'[\w\u4e00-\u9fff]+', task_title)
        # 过滤掉单字和常见词
        keywords.update([w.lower() for w in title_words if len(w) > 1])
        
        # 提取任务描述中的关键词
        if task_description:
            desc_words = re.findall(r'[\w\u4e00-\u9fff]+', task_description)
            keywords.update([w.lower() for w in desc_words if len(w) > 1])
        
        # 移除常见停用词
        stopwords = {'的', '了', '是', '在', '和', '有', '我', '你', '他', '她', '它', '这', '那',
                     'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'to',
                     '推荐', '观看', '这部', '精彩', '短剧', '片段', '剧情', '跌宕起伏', '不容错过'}
        keywords = keywords - stopwords
        
        logger.info(f"🔑 关键词列表: {keywords}")
        
        # 检查至少匹配 30% 的关键词
        if not keywords:
            logger.warning("⚠️ 没有提取到关键词，默认通过")
            return True
        
        matched_count = sum(1 for keyword in keywords if keyword in page_content)
        match_rate = matched_count / len(keywords)
        
        logger.info(f"📊 匹配率: {match_rate:.2%} ({matched_count}/{len(keywords)})")
        logger.info(f"📋 匹配的关键词: {[k for k in keywords if k in page_content]}")
        logger.info(f"❌ 未匹配的关键词: {[k for k in keywords if k not in page_content]}")
        
        # 至少匹配 30% 的关键词才算通过
        return match_rate >= 0.3


# 测试代码
if __name__ == '__main__':
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        verifier = LinkVerifier()
        
        # 测试 TikTok 链接
        result = await verifier.verify_link(
            url="https://www.tiktok.com/@wu.roger7/video/7577128093949725966",
            task_title="养母胜过生母",
            task_description="推荐观看这部精彩短剧片段《养母胜过生母》，剧情跌宕起伏，不容错过！"
        )
        
        print("\n验证结果:")
        print(f"成功: {result['success']}")
        print(f"匹配: {result['matched']}")
        print(f"标题: {result['page_title']}")
        print(f"描述和标签: {result['page_text']}")
        print(f"截图: {result['screenshot_path']}")
        if result['error']:
            print(f"错误: {result['error']}")
    
    asyncio.run(test())
