#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧集分类器 - 使用 AI 自动识别剧集类型
"""

import os
from openai import OpenAI

# 剧集分类列表
DRAMA_CATEGORIES = {
    'latest': '最新',
    'revenge': '霸道总裁/豪门虐恋',
    'rebirth': '穿越重生/逆天改命',
    'revenge_slap': '复仇爽文/打脸反杀',
    'marriage': '婚恋错配/先婚后爱',
    'sweet_romance': '甜宠小白花/治愈爱情',
    'family': '家庭伦理/婆媳大战',
    'detective': '破案刑侦/悬疑推理',
    'medical': '医疗法庭/职场权谋',
    'career_woman': '女强成长/职场逆袭',
    'campus': '校园青春/青涩暗恋',
    'horror': '恐怖灵异/民俗悬疑',
    'scifi': '赛博/未来科幻',
    'survival': '末日生存/丧尸灾难',
    'costume': '宫斗宅斗/古装权谋',
    'business': '商战博弈/资本智斗',
    'rural': '乡村/人生治愈系',
    'superpower': '超能力变异/英雄觉醒',
    'triangle': '三角恋/修罗场',
    'underdog': '小人物大机缘(意外继承/捡宝)',
    'dark': '反社会性人格/黑暗系追德困境'
}

# 分类关键词映射
CATEGORY_KEYWORDS = {
    'revenge': ['霸道', '总裁', '豪门', '虐恋', '豪门恩怨'],
    'rebirth': ['穿越', '重生', '逆天', '改命', '回到过去'],
    'revenge_slap': ['复仇', '爽文', '打脸', '反杀', '逆袭'],
    'marriage': ['婚恋', '错配', '先婚后爱', '闪婚', '契约'],
    'sweet_romance': ['甜宠', '小白花', '治愈', '爱情', '甜蜜'],
    'family': ['家庭', '伦理', '婆媳', '大战', '家族'],
    'detective': ['破案', '刑侦', '悬疑', '推理', '侦探'],
    'medical': ['医疗', '法庭', '职场', '权谋', '医生'],
    'career_woman': ['女强', '成长', '职场逆袭', '事业'],
    'campus': ['校园', '青春', '暗恋', '学生', '大学'],
    'horror': ['恐怖', '灵异', '民俗', '悬疑', '鬼怪'],
    'scifi': ['赛博', '未来', '科幻', '太空', '机器人'],
    'survival': ['末日', '生存', '丧尸', '灾难', '废土'],
    'costume': ['宫斗', '宅斗', '古装', '权谋', '皇宫'],
    'business': ['商战', '博弈', '资本', '智斗', '商业'],
    'rural': ['乡村', '人生', '治愈', '农村', '田园'],
    'superpower': ['超能力', '变异', '英雄', '觉醒', '异能'],
    'triangle': ['三角恋', '修罗场', '多角恋'],
    'underdog': ['小人物', '大机缘', '意外继承', '捡宝', '逆袭'],
    'dark': ['反社会', '黑暗', '追德困境', '人性']
}


def classify_drama_by_keywords(title: str) -> str:
    """
    基于关键词匹配分类剧集
    """
    title_lower = title.lower()
    
    # 遍历所有分类，检查关键词
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title:
                return category
    
    # 如果没有匹配到，返回 latest
    return 'latest'


def classify_drama_by_ai(title: str, description: str = "") -> str:
    """
    使用 AI 自动分类剧集
    
    Args:
        title: 剧集标题
        description: 剧集描述（可选）
    
    Returns:
        category: 分类代码
    """
    try:
        client = OpenAI()
        
        # 构建分类列表文本
        categories_text = "\n".join([f"- {code}: {name}" for code, name in DRAMA_CATEGORIES.items() if code != 'latest'])
        
        # 构建提示词
        prompt = f"""请根据剧集标题（和描述）判断其所属的分类。

剧集标题：{title}
{f'剧集描述：{description}' if description else ''}

可选分类：
{categories_text}

请只返回分类代码（如 revenge、rebirth 等），不要返回其他内容。
如果无法确定分类，请返回 latest。"""

        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个剧集分类专家，能够准确识别短剧的类型。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=50
        )
        
        category = response.choices[0].message.content.strip().lower()
        
        # 验证分类是否有效
        if category in DRAMA_CATEGORIES:
            return category
        else:
            # 如果 AI 返回的分类无效，尝试关键词匹配
            return classify_drama_by_keywords(title)
    
    except Exception as e:
        print(f"❌ AI 分类失败: {e}")
        # 如果 AI 失败，使用关键词匹配
        return classify_drama_by_keywords(title)


def get_category_name(category_code: str, lang: str = 'zh') -> str:
    """
    获取分类名称
    
    Args:
        category_code: 分类代码
        lang: 语言（zh 或 en）
    
    Returns:
        category_name: 分类名称
    """
    if lang == 'zh' or lang.startswith('zh'):
        return DRAMA_CATEGORIES.get(category_code, '最新')
    else:
        # 英文分类名称
        en_categories = {
            'latest': 'Latest',
            'revenge': 'CEO Romance',
            'rebirth': 'Time Travel',
            'revenge_slap': 'Revenge',
            'marriage': 'Marriage',
            'sweet_romance': 'Sweet Romance',
            'family': 'Family Drama',
            'detective': 'Detective',
            'medical': 'Medical',
            'career_woman': 'Career Woman',
            'campus': 'Campus',
            'horror': 'Horror',
            'scifi': 'Sci-Fi',
            'survival': 'Survival',
            'costume': 'Costume Drama',
            'business': 'Business',
            'rural': 'Rural',
            'superpower': 'Superpower',
            'triangle': 'Love Triangle',
            'underdog': 'Underdog',
            'dark': 'Dark'
        }
        return en_categories.get(category_code, 'Latest')


def get_all_categories(lang: str = 'zh') -> dict:
    """
    获取所有分类
    
    Returns:
        dict: {category_code: category_name}
    """
    if lang == 'zh' or lang.startswith('zh'):
        return DRAMA_CATEGORIES
    else:
        return {
            'latest': 'Latest',
            'revenge': 'CEO Romance',
            'rebirth': 'Time Travel',
            'revenge_slap': 'Revenge',
            'marriage': 'Marriage',
            'sweet_romance': 'Sweet Romance',
            'family': 'Family Drama',
            'detective': 'Detective',
            'medical': 'Medical',
            'career_woman': 'Career Woman',
            'campus': 'Campus',
            'horror': 'Horror',
            'scifi': 'Sci-Fi',
            'survival': 'Survival',
            'costume': 'Costume Drama',
            'business': 'Business',
            'rural': 'Rural',
            'superpower': 'Superpower',
            'triangle': 'Love Triangle',
            'underdog': 'Underdog',
            'dark': 'Dark'
        }


if __name__ == '__main__':
    # 测试分类功能
    test_titles = [
        "南洋当大佬 - 第01集",
        "霸道总裁爱上我 - 第01集",
        "穿越之逆天改命 - 第01集",
        "复仇千金的逆袭 - 第01集",
        "先婚后爱的甜蜜生活 - 第01集",
        "恐怖灵异事件簿 - 第01集",
        "末日生存指南 - 第01集",
        "宫斗权谋录 - 第01集",
    ]
    
    print("=== 测试 AI 分类功能 ===\n")
    for title in test_titles:
        category = classify_drama_by_ai(title)
        category_name = get_category_name(category)
        print(f"标题: {title}")
        print(f"分类: {category} ({category_name})")
        print()
