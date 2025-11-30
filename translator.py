# -*- coding: utf-8 -*-
"""
自动翻译模块
使用 Gemini API 将中文内容翻译成英文
"""

import os
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

# 配置 Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBpzsVO-MM1Ur_KzNtnwcFHA4nYKClYqw8')
genai.configure(api_key=GEMINI_API_KEY)

# 创建模型实例
model = genai.GenerativeModel('gemini-2.0-flash-exp')

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
        
        # 构建翻译提示
        prompt = f"""Translate the following Chinese text to English. 
Context: {context}
Keep the translation natural, concise, and professional.
Only return the translated text, no explanations.

Chinese text:
{text}

English translation:"""
        
        # 调用 Gemini API
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=500,
            )
        )
        
        if response and response.text:
            translated = response.text.strip()
            logger.info(f"✅ Translation successful: {translated[:50]}...")
            return translated
        else:
            logger.error(f"❌ API returned empty response")
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
