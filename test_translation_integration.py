#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
测试翻译功能集成
"""

import sys
sys.path.insert(0, '/home/ubuntu/telegram-bot-dramarelay')

# 模拟任务数据
task = {
    'task_id': 1,
    'title': '南洋当大佬 - 第06集',
    'description': '太像现实中的我们了... 《南洋当大佬》。回南洋当大佬，是希望还是绝望？都市男女的甜宠生活，背后又藏着怎样的波澜？',
    'title_en': None,
    'description_en': None
}

# 导入函数
from bot import get_task_title, get_task_description

print("=" * 60)
print("测试翻译功能")
print("=" * 60)

print("\n1. 测试中文用户（不翻译）：")
title_zh = get_task_title(task, 'zh', auto_translate=False)
print(f"   标题: {title_zh}")

print("\n2. 测试英文用户（自动翻译）：")
title_en = get_task_title(task, 'en', auto_translate=True)
print(f"   标题: {title_en}")

print("\n3. 测试描述翻译：")
desc_en = get_task_description(task, 'en', auto_translate=True)
print(f"   描述: {desc_en}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
