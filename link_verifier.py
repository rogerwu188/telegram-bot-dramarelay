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
    
    async def verify_link(self, url: str, task_title: str, task_description: str, timeout: int = 20000) -> dict:
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
            logger.info("🎭 Step 1: 启动 Playwright...")
            
            async with async_playwright() as p:
                logger.info("✅ Playwright 已启动")
                # 启动浏览器（使用 chromium）
                logger.info("🎭 Step 2: 启动 Chromium 浏览器...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                logger.info("✅ Chromium 浏览器已启动")
                
                logger.info("🎭 Step 3: 创建浏览器上下文...")
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                logger.info("✅ 上下文已创建")
                
                logger.info("🎭 Step 4: 创建新页面...")
                page = await context.new_page()
                logger.info("✅ 页面已创建")
                
                # 访问链接
                logger.info(f"🎭 Step 5: 访问页面 {url}...")
                try:
                    await page.goto(url, timeout=15000, wait_until='networkidle')
                    logger.info("✅ 页面加载完成")
                except PlaywrightTimeout:
                    logger.warning("⚠️ 页面加载超时，尝试使用 domcontentloaded...")
                    try:
                        await page.goto(url, timeout=10000, wait_until='domcontentloaded')
                    except Exception as e2:
                        logger.error(f"页面加载失败: {e2}")
                        result['error'] = f"无法访问链接: {str(e2)}"
                        return result
                except Exception as e:
                    logger.error(f"访问页面失败: {e}")
                    result['error'] = f"无法访问链接: {str(e)}"
                    return result
                
                # 等待页面渲染（TikTok 需要时间加载动态内容）
                logger.info("🎭 Step 6: 等待页面渲染...")
                try:
                    await page.wait_for_timeout(3000)
                    logger.info("✅ 页面渲染完成")
                except Exception as e:
                    logger.warning(f"等待超时: {e}")
                
                # 获取页面标题
                logger.info("🎭 Step 7: 获取页面标题...")
                result['page_title'] = await page.title()
                logger.info(f"✅ 页面标题: {result['page_title']}")
                
                # 提取视频描述和标签
                logger.info("🎭 Step 8: 提取描述和标签...")
                try:
                    result['page_text'] = await self._extract_description_and_tags(page, url)
                    logger.info(f"📝 提取到的描述和标签: {result['page_text'][:300] if result['page_text'] else '(空)'}...")
                except Exception as e:
                    logger.error(f"提取内容失败: {e}")
                    result['page_text'] = ''
                
                # 截图保存
                logger.info("🎭 Step 9: 截图...")
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_filename = f"verify_{timestamp}.png"
                screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
                
                try:
                    await page.screenshot(path=screenshot_path, full_page=False, timeout=10000)
                    result['screenshot_path'] = screenshot_path
                    logger.info(f"📸 截图已保存: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"截图失败: {e}")
                
                logger.info("🎭 Step 10: 关闭浏览器...")
                try:
                    await browser.close()
                    logger.info("✅ 浏览器已关闭")
                except Exception as e:
                    logger.warning(f"关闭浏览器失败: {e}")
                
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
        
        # 如果没有提取到任何内容，尝试使用页面标题
        if not text_parts:
            try:
                page_title = await page.title()
                if page_title:
                    logger.warning(f"⚠️ 未提取到描述和标签，使用页面标题: {page_title}")
                    text_parts.append(page_title)
            except Exception as e:
                logger.error(f"获取页面标题失败: {e}")
        
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
        
        # 从任务标题中提取关键词（不使用描述）
        keywords = set()
        
        # 提取任务标题中的关键词（去除标点符号）
        title_words = re.findall(r'[\w\u4e00-\u9fff]+', task_title)
        # 过滤掉单字、纯数字、包含数字的词和常见词
        for w in title_words:
            if len(w) <= 1:  # 过滤单字
                continue
            if w.isdigit():  # 过滤纯数字
                continue
            if re.search(r'\d', w):  # 过滤包含数字的词（如"第5集"、"觉醒2"）
                continue
            keywords.add(w.lower())
        
        # 不再从描述中提取关键词，因为描述包含大量营销性词语
        
        # 移除常见停用词和营销词语
        stopwords = {
            # 基础停用词
            '的', '了', '是', '在', '和', '有', '我', '你', '他', '她', '它', '这', '那', '一', '二', '三', '四', '五',
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but', 'in', 'to', 'of', 'for',
            # 单个营销词
            '推荐', '观看', '这部', '精彩', '短剧', '片段', '剧情', '跌宕起伏', '不容错过',
            '精选', '热门', '好看', '必看', '强烈推荐', '热播', '爆款', '热剧',
            '女主', '男主', '角色', '觉醒', '逆袭', '复仇', '重生', '穿越',
            '第', '集', 'ep', 'episode',
            # 组合营销词
            '精选短剧', '热门短剧', '女主觉醒', '男主逆袭', '女主逆袭', '女主复仇', '男主复仇',
            '女主重生', '男主重生', '女主穿越', '男主穿越', '女强男强',
            # 其他常见词
            '中', '上', '下', '左', '右', '前', '后'
        }
        keywords = keywords - stopwords
        
        # 再次过滤：删除包含停用词的组合词
        keywords_to_remove = set()
        for keyword in keywords:
            # 如果关键词包含任何停用词，删除它
            for stopword in ['短剧', '精选', '热门', '女主', '男主', '觉醒', '逆袭', '复仇', '重生', '穿越']:
                if stopword in keyword:
                    keywords_to_remove.add(keyword)
                    break
        keywords = keywords - keywords_to_remove
        
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
        
        # 至少匹配 20% 的关键词才算通过（降低阈值因为只使用标题关键词）
        return match_rate >= 0.2


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
