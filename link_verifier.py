#!/usr/bin/env python3
"""
链接验证模块（轻量级版本）
使用 requests + BeautifulSoup 验证视频链接内容
"""
import logging
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class LinkVerifier:
    """视频链接验证器（轻量级）"""
    
    def __init__(self):
        """初始化验证器"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        })
    
    def verify_link(self, url: str, task_title: str, task_description: str, timeout: int = 15) -> dict:
        """
        验证视频链接
        
        Args:
            url: 用户提交的视频链接
            task_title: 任务标题（用于关键词匹配）
            task_description: 任务描述（用于关键词匹配）
            timeout: 请求超时时间（秒）
        
        Returns:
            dict: {
                'success': bool,  # 验证是否成功
                'matched': bool,  # 是否匹配任务关键词
                'page_title': str,  # 页面标题
                'page_text': str,  # 页面文本内容
                'error': str  # 错误信息（如果有）
            }
        """
        result = {
            'success': False,
            'matched': False,
            'page_title': '',
            'page_text': '',
            'error': None
        }
        
        try:
            logger.info(f"🔍 开始验证链接: {url}")
            
            # 发送 HTTP 请求
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            
            logger.info(f"✅ 成功获取页面，状态码: {response.status_code}")
            
            # 解析 HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取页面标题
            result['page_title'] = self._extract_title(soup, url)
            logger.info(f"📄 页面标题: {result['page_title']}")
            
            # 提取页面描述和内容
            result['page_text'] = self._extract_content(soup, url)
            logger.info(f"📝 提取到的文本: {result['page_text'][:200]}...")
            
            # 验证关键词匹配
            result['matched'] = self._check_keywords_match(
                result['page_title'],
                result['page_text'],
                task_title,
                task_description
            )
            
            result['success'] = True
            logger.info(f"✅ 验证完成，匹配结果: {result['matched']}")
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ 请求超时")
            result['error'] = "请求超时，无法访问链接"
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 请求失败: {e}")
            result['error'] = f"无法访问链接: {str(e)}"
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            result['error'] = str(e)
        
        return result
    
    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """提取页面标题"""
        # 优先级顺序：og:title > twitter:title > title 标签
        
        # 1. Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
        
        # 2. Twitter title
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content'].strip()
        
        # 3. 标准 title 标签
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # 4. 平台特定选择器
        domain = urlparse(url).netloc.lower()
        
        if 'tiktok.com' in domain:
            # TikTok 特定选择器
            desc = soup.find('meta', attrs={'name': 'description'})
            if desc and desc.get('content'):
                return desc['content'].strip()
        
        return ""
    
    def _extract_content(self, soup: BeautifulSoup, url: str) -> str:
        """提取页面内容"""
        content_parts = []
        
        # 1. Meta 描述
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content_parts.append(meta_desc['content'])
        
        # 2. Open Graph 描述
        og_desc = soup.find('meta', property='og:description')
        if og_desc and og_desc.get('content'):
            content_parts.append(og_desc['content'])
        
        # 3. Twitter 描述
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc and twitter_desc.get('content'):
            content_parts.append(twitter_desc['content'])
        
        # 4. 平台特定内容提取
        domain = urlparse(url).netloc.lower()
        
        if 'tiktok.com' in domain:
            # TikTok: 尝试从 JSON-LD 提取
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                content_parts.append(json_ld.string)
        
        elif 'youtube.com' in domain or 'youtu.be' in domain:
            # YouTube: 提取视频描述
            yt_desc = soup.find('meta', attrs={'name': 'description'})
            if yt_desc and yt_desc.get('content'):
                content_parts.append(yt_desc['content'])
        
        elif 'instagram.com' in domain:
            # Instagram: 提取 og:description
            pass  # 已在上面处理
        
        # 5. 提取主要文本内容（h1, h2, p 标签）
        for tag in soup.find_all(['h1', 'h2', 'p'], limit=10):
            text = tag.get_text().strip()
            if text and len(text) > 10:
                content_parts.append(text)
        
        return ' '.join(content_parts)
    
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
        title_words = re.findall(r'[\w\u4e00-\u9fff]+', task_title)
        # 过滤掉单字和常见词
        keywords.update([w.lower() for w in title_words if len(w) > 1])
        
        # 提取任务描述中的关键词
        if task_description:
            desc_words = re.findall(r'[\w\u4e00-\u9fff]+', task_description)
            keywords.update([w.lower() for w in desc_words if len(w) > 1])
        
        # 移除常见停用词
        stopwords = {'的', '了', '是', '在', '和', '有', '我', '你', '他', '她', '它', 
                     'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but'}
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
    if result['error']:
        print(f"错误: {result['error']}")
