#!/usr/bin/env python3
"""
链接验证模块
自动访问用户提交的视频链接，截图并验证标题/描述是否包含任务关键词
"""
import os
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

class LinkVerifier:
    """视频链接验证器"""
    
    def __init__(self, screenshots_dir="/tmp/screenshots"):
        """初始化验证器"""
        self.screenshots_dir = screenshots_dir
        os.makedirs(screenshots_dir, exist_ok=True)
    
    def verify_link(self, url: str, task_title: str, task_description: str, timeout: int = 30000) -> dict:
        """
        验证视频链接
        
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
                'page_text': str,  # 页面文本内容
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
            
            with sync_playwright() as p:
                # 启动浏览器（使用 chromium）
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                
                page = context.new_page()
                
                # 访问链接
                logger.info(f"📱 正在访问页面...")
                try:
                    page.goto(url, timeout=timeout, wait_until='networkidle')
                except PlaywrightTimeout:
                    logger.warning("页面加载超时，继续尝试提取内容...")
                
                # 等待页面渲染
                page.wait_for_timeout(3000)
                
                # 获取页面标题
                result['page_title'] = page.title()
                logger.info(f"📄 页面标题: {result['page_title']}")
                
                # 获取页面文本内容
                try:
                    # 尝试提取视频描述（不同平台的选择器）
                    selectors = [
                        # TikTok
                        '[data-e2e="browse-video-desc"]',
                        '[data-e2e="video-desc"]',
                        'h1',
                        # YouTube
                        '#title h1',
                        'yt-formatted-string.ytd-video-primary-info-renderer',
                        // Instagram
                        'h1',
                        'article h2',
                        // 通用
                        'meta[property="og:title"]',
                        'meta[property="og:description"]',
                        'meta[name="description"]'
                    ]
                    
                    text_parts = []
                    
                    for selector in selectors:
                        try:
                            if selector.startswith('meta'):
                                # 提取 meta 标签内容
                                content = page.get_attribute(selector, 'content', timeout=1000)
                                if content:
                                    text_parts.append(content)
                            else:
                                # 提取可见文本
                                element = page.locator(selector).first
                                if element.is_visible(timeout=1000):
                                    text = element.inner_text()
                                    if text:
                                        text_parts.append(text)
                        except:
                            continue
                    
                    result['page_text'] = ' '.join(text_parts)
                    logger.info(f"📝 提取到的文本: {result['page_text'][:200]}...")
                    
                except Exception as e:
                    logger.warning(f"提取页面文本失败: {e}")
                    result['page_text'] = page.inner_text('body')[:500]
                
                # 截图保存
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_filename = f"verify_{timestamp}.png"
                screenshot_path = os.path.join(self.screenshots_dir, screenshot_filename)
                
                page.screenshot(path=screenshot_path, full_page=False)
                result['screenshot_path'] = screenshot_path
                logger.info(f"📸 截图已保存: {screenshot_path}")
                
                browser.close()
                
                # 验证关键词匹配
                result['matched'] = self._check_keywords_match(
                    result['page_title'],
                    result['page_text'],
                    task_title,
                    task_description
                )
                
                result['success'] = True
                logger.info(f"✅ 验证完成，匹配结果: {result['matched']}")
                
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            result['error'] = str(e)
        
        return result
    
    def _check_keywords_match(self, page_title: str, page_text: str, task_title: str, task_description: str) -> bool:
        """
        检查页面内容是否包含任务关键词
        
        Args:
            page_title: 页面标题
            page_text: 页面文本
            task_title: 任务标题
            task_description: 任务描述
        
        Returns:
            bool: 是否匹配
        """
        # 合并页面内容
        page_content = f"{page_title} {page_text}".lower()
        
        # 从任务标题和描述中提取关键词
        keywords = set()
        
        # 提取任务标题中的关键词（去除标点符号）
        import re
        title_words = re.findall(r'[\w\u4e00-\u9fff]+', task_title)
        keywords.update([w.lower() for w in title_words if len(w) > 1])
        
        # 提取任务描述中的关键词
        if task_description:
            desc_words = re.findall(r'[\w\u4e00-\u9fff]+', task_description)
            keywords.update([w.lower() for w in desc_words if len(w) > 1])
        
        logger.info(f"🔑 关键词列表: {keywords}")
        
        # 检查至少匹配 30% 的关键词
        if not keywords:
            logger.warning("⚠️ 没有提取到关键词，默认通过")
            return True
        
        matched_count = sum(1 for keyword in keywords if keyword in page_content)
        match_rate = matched_count / len(keywords)
        
        logger.info(f"📊 匹配率: {match_rate:.2%} ({matched_count}/{len(keywords)})")
        
        # 至少匹配 30% 的关键词才算通过
        return match_rate >= 0.3


# 测试代码
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    verifier = LinkVerifier()
    
    # 测试 TikTok 链接
    result = verifier.verify_link(
        url="https://www.tiktok.com/@wu.roger7/video/7576774823712394551",
        task_title="养母胜过生母",
        task_description="分享短剧《养母胜过生母》真情反转片段"
    )
    
    print("\n验证结果:")
    print(f"成功: {result['success']}")
    print(f"匹配: {result['matched']}")
    print(f"标题: {result['page_title']}")
    print(f"截图: {result['screenshot_path']}")
    if result['error']:
        print(f"错误: {result['error']}")
