# -*- coding: utf-8 -*-
"""
自动翻译模块
使用 Gemini API (通过 OpenAI 兼容接口) 将中文内容翻译成英文
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

# 使用 OpenAI 兼容的 Gemini API
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')

def translate_to_english(text, context="drama task"):
    """
    将中文文本翻译成英文
    
    Args:
        text: 要翻译的中文文本
        context: 上下文信息，帮助提高翻译质量
    
    Returns:
        翻译后的英文文本，如果翻译失败则返回原文
    """
    if not text or not text.strip():
        return text
    
    try:
        logger.info(f"🌐 Translating text: {text[:50]}...")
        
        # 使用 OpenAI 兼容接口
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}'
        }
        
        payload = {
            "model": "gemini-2.5-flash",
            "messages": [
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate Chinese text to English. Context: {context}. Keep the translation natural and concise."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            translated = result['choices'][0]['message']['content'].strip()
            logger.info(f"✅ Translation successful: {translated[:50]}...")
            return translated
        else:
            logger.error(f"❌ API error: {response.status_code} - {response.text}")
            return text
    
    except Exception as e:
        logger.error(f"❌ Translation failed: {e}")
        return text  # 翻译失败时返回原文


def translate_task_content(title, description):
    """
    翻译任务标题和描述
    
    Args:
        title: 任务标题（中文）
        description: 任务描述（中文）
    
    Returns:
        (title_en, description_en) 元组
    """
    title_en = translate_to_english(title, context="drama title") if title else None
    description_en = translate_to_english(description, context="drama description") if description else None
    
    return title_en, description_en
