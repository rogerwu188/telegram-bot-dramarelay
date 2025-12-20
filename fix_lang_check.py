#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复语言判断问题：将 user_lang == 'zh' 改为 user_lang.startswith('zh')
"""

# 读取文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 统计修改次数
count = 0

# 替换所有 user_lang == 'zh' 为 user_lang.startswith('zh')
old_pattern = "user_lang == 'zh'"
new_pattern = "user_lang.startswith('zh')"

if old_pattern in content:
    count = content.count(old_pattern)
    content = content.replace(old_pattern, new_pattern)
    print(f"✅ 已替换 {count} 处 user_lang == 'zh' 为 user_lang.startswith('zh')")
else:
    print("⚠️ 未找到 user_lang == 'zh'")

# 写入文件
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已保存，共修改 {count} 处")
