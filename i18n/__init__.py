#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
国际化（i18n）模块
支持多语言翻译功能
"""

import json
import os
from typing import Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh-CN': '简体中文',
    'zh-TW': '繁體中文',
    'en': 'English',
    'ja': '日本語',
    'ko': '한국어',
    'es': 'Español'
}

# 默认语言
DEFAULT_LANGUAGE = 'zh-CN'

# 翻译数据缓存
_translations: Dict[str, Dict] = {}

# 数据库连接配置
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'


def load_translations():
    """加载所有语言的翻译文件"""
    global _translations
    
    locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
    
    for lang_code in SUPPORTED_LANGUAGES.keys():
        file_path = os.path.join(locales_dir, f'{lang_code}.json')
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    _translations[lang_code] = json.load(f)
                print(f"✅ Loaded translations for {lang_code}")
            except Exception as e:
                print(f"❌ Failed to load {lang_code}.json: {e}")
                _translations[lang_code] = {}
        else:
            print(f"⚠️ Translation file not found: {file_path}")
            _translations[lang_code] = {}


def get_user_language(user_id: int) -> str:
    """从数据库获取用户的语言设置"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute(
            "SELECT language FROM users WHERE user_id = %s",
            (user_id,)
        )
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result['language']:
            return result['language']
        
    except Exception as e:
        print(f"❌ Failed to get user language: {e}")
    
    return DEFAULT_LANGUAGE


def set_user_language(user_id: int, language: str) -> bool:
    """设置用户的语言偏好"""
    if language not in SUPPORTED_LANGUAGES:
        return False
    
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        cur.execute(
            "UPDATE users SET language = %s WHERE user_id = %s",
            (language, user_id)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to set user language: {e}")
        return False


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """
    翻译函数
    
    Args:
        key: 翻译键（支持嵌套，如 'welcome.title'）
        lang: 语言代码，如果为 None 则使用默认语言
        **kwargs: 格式化参数
    
    Returns:
        翻译后的文本
    """
    if lang is None:
        lang = DEFAULT_LANGUAGE
    
    # 如果语言不支持，回退到默认语言
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
    
    # 如果翻译数据未加载，先加载
    if not _translations:
        load_translations()
    
    # 获取对应语言的翻译数据
    translations = _translations.get(lang, {})
    
    # 支持嵌套键（如 'welcome.title'）
    keys = key.split('.')
    value = translations
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            value = None
            break
    
    # 如果找不到翻译，尝试使用默认语言
    if value is None and lang != DEFAULT_LANGUAGE:
        default_translations = _translations.get(DEFAULT_LANGUAGE, {})
        value = default_translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                value = None
                break
    
    # 如果还是找不到，返回键本身
    if value is None:
        return key
    
    # 如果是字符串，进行格式化
    if isinstance(value, str) and kwargs:
        try:
            return value.format(**kwargs)
        except KeyError:
            return value
    
    return str(value)


# 初始化时加载翻译
load_translations()
