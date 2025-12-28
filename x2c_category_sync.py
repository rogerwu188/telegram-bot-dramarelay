#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2C 分类同步模块
从 X2C API 获取分类列表并同步到本地
"""

import requests
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# X2C API 配置
X2C_API_URL = "https://eumfmgwxwjyagsvqloac.supabase.co/functions/v1/get-categories"
X2C_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV1bWZtZ3d4d2p5YWdzdnFsb2FjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMzMjQzNTMsImV4cCI6MjA3ODkwMDM1M30.sw32WDIv6BFQG2eu4u9BjBS_Ehrg4IZ_zGUzXRiOsAU"

# 本地缓存的分类数据
_cached_categories = None
_last_sync_time = None


def fetch_categories_from_x2c() -> Optional[List[Dict]]:
    """
    从 X2C API 获取分类列表
    
    Returns:
        List[Dict]: 分类列表，每个分类包含 id, name, name_key, display_order, target_language
    """
    try:
        headers = {
            "apikey": X2C_API_KEY,
            "Authorization": f"Bearer {X2C_API_KEY}"
        }
        
        response = requests.get(X2C_API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        categories = data.get('categories', [])
        
        logger.info(f"✅ 从 X2C API 获取到 {len(categories)} 个分类")
        return categories
        
    except Exception as e:
        logger.error(f"❌ 获取 X2C 分类失败: {e}")
        return None


def build_category_mapping(categories: List[Dict]) -> Dict[str, Dict]:
    """
    构建分类映射表
    将 X2C 的 project_style (带#的name) 映射到 name_key
    
    Args:
        categories: X2C API 返回的分类列表
        
    Returns:
        Dict: {
            "#Female Revenge Arc": {
                "code": "werewolfVampire",
                "name_zh": "Female Revenge Arc",
                "name_en": "Female Revenge Arc",
                "language": "en"
            },
            ...
        }
    """
    mapping = {}
    
    # 添加默认的"最新"分类
    mapping["#latest"] = {
        "code": "latest",
        "name_zh": "最新",
        "name_en": "Latest",
        "language": "all"
    }
    
    for cat in categories:
        name = cat.get('name', '')
        name_key = cat.get('name_key')
        language = cat.get('target_language', 'en')
        
        # X2C 发送的 project_style 格式是 "#Female Revenge Arc"
        project_style_key = f"#{name}"
        
        # 直接使用原始分类名称，不进行转换
        # 中文分类保持中文，英文分类保持英文
        code = name
        
        mapping[project_style_key] = {
            "code": code,
            "name_zh": name if language == 'zh' else name,
            "name_en": name if language == 'en' else name,
            "language": language
        }
    
    logger.info(f"📊 构建了 {len(mapping)} 个分类映射")
    return mapping


def sync_categories() -> bool:
    """
    同步分类数据
    从 X2C API 获取最新分类并更新本地缓存
    
    Returns:
        bool: 同步是否成功
    """
    global _cached_categories, _last_sync_time
    
    categories = fetch_categories_from_x2c()
    if not categories:
        logger.warning("⚠️ 分类同步失败，使用缓存数据")
        return False
    
    # 构建映射表
    mapping = build_category_mapping(categories)
    
    # 更新缓存
    _cached_categories = mapping
    _last_sync_time = datetime.now()
    
    logger.info(f"✅ 分类同步成功，共 {len(mapping)} 个分类，时间: {_last_sync_time}")
    return True


def get_category_code(project_style: str) -> Optional[str]:
    """
    根据 X2C 的 project_style 或 category 获取 Bot 的分类代码
    
    Args:
        project_style: X2C 发送的分类值，如 "#Female Revenge Arc" 或 "综合其他"
        
    Returns:
        str: Bot 的分类代码，如 "werewolfVampire"，如果未找到返回 None
    """
    global _cached_categories
    
    if not project_style:
        return None
    
    # 如果缓存为空，先同步一次
    if _cached_categories is None:
        sync_categories()
    
    # 如果还是为空，返回 None
    if _cached_categories is None:
        return None
    
    # 尝试直接查找（带#号的格式）
    category_info = _cached_categories.get(project_style)
    if category_info:
        return category_info['code']
    
    # 尝试添加#号后查找（X2C可能发送不带#的分类名）
    if not project_style.startswith('#'):
        category_info = _cached_categories.get(f"#{project_style}")
        if category_info:
            logger.info(f"✅ 分类映射: {project_style} -> #{project_style} -> {category_info['code']}")
            return category_info['code']
    
    # 尝试遍历所有分类，模糊匹配名称
    for key, info in _cached_categories.items():
        # 匹配 name_zh 或 name_en
        if info.get('name_zh') == project_style or info.get('name_en') == project_style:
            logger.info(f"✅ 分类模糊匹配: {project_style} -> {info['code']}")
            return info['code']
        # 匹配 key 去掉#号后的值
        if key.startswith('#') and key[1:] == project_style:
            logger.info(f"✅ 分类匹配: {project_style} -> {info['code']}")
            return info['code']
    
    # 未找到映射
    logger.warning(f"⚠️ 未找到 project_style/category 的映射: {project_style}")
    return None


def get_all_categories_for_bot(language: str = 'zh') -> Dict[str, str]:
    """
    获取所有分类，供 Bot 显示使用
    
    Args:
        language: 语言代码，'zh' 或 'en'
        
    Returns:
        Dict: {code: display_name}，如 {"werewolfVampire": "Female Revenge Arc"}
    """
    global _cached_categories
    
    # 如果缓存为空，先同步一次
    if _cached_categories is None:
        sync_categories()
    
    # 如果还是为空，返回空字典
    if _cached_categories is None:
        return {}
    
    # 构建返回数据
    result = {}
    for project_style, info in _cached_categories.items():
        code = info['code']
        
        # 使用原始名称（不翻译）
        # X2C API 返回的 name 已经是对应语言的名称
        display_name = info['name_zh'] if info['language'] == 'zh' else info['name_en']
        
        # 返回所有分类（不过滤语言）
        result[code] = display_name
    
    return result


def get_last_sync_time() -> Optional[datetime]:
    """
    获取最后同步时间
    
    Returns:
        datetime: 最后同步时间，如果未同步过返回 None
    """
    return _last_sync_time


if __name__ == '__main__':
    # 测试同步功能
    logging.basicConfig(level=logging.INFO)
    
    print("测试分类同步...")
    success = sync_categories()
    
    if success:
        print("\n分类映射表:")
        for project_style, info in _cached_categories.items():
            print(f"  {project_style} -> {info['code']} ({info['name_zh']})")
        
        print("\n测试获取分类代码:")
        test_styles = ["#Female Revenge Arc", "#霸总甜宠", "#latest"]
        for style in test_styles:
            code = get_category_code(style)
            print(f"  {style} -> {code}")
        
        print("\nBot 中文分类列表:")
        zh_categories = get_all_categories_for_bot('zh')
        for code, name in zh_categories.items():
            print(f"  {code}: {name}")
