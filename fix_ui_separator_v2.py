#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复UI体验：使用更长的分隔线、更多空行和醒目的标题
"""

# 读取完整文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"📖 读取完成")

# ============================================================
# 修改1: 中文 select_task_to_submit 消息改进分隔
# ============================================================

old_zh_select = "'select_task_to_submit': '━━━━━━━━━━━━━━━━━━\\n📋 请选择要提交的任务：',"
new_zh_select = "'select_task_to_submit': '\\n\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n🆕 【继续提交任务】\\n\\n📋 请选择要提交的任务：',"

if old_zh_select in content:
    content = content.replace(old_zh_select, new_zh_select)
    print("✅ 修改1: 中文 select_task_to_submit 改进分隔 - 完成")
else:
    print("⚠️ 修改1: 中文 select_task_to_submit - 未找到")

# ============================================================
# 修改2: 英文 select_task_to_submit 消息改进分隔
# ============================================================

old_en_select = "'select_task_to_submit': '━━━━━━━━━━━━━━━━━━\\n📋 Please select the task to submit:',"
new_en_select = "'select_task_to_submit': '\\n\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n🆕 【Continue Submitting】\\n\\n📋 Please select the task to submit:',"

if old_en_select in content:
    content = content.replace(old_en_select, new_en_select)
    print("✅ 修改2: 英文 select_task_to_submit 改进分隔 - 完成")
else:
    print("⚠️ 修改2: 英文 select_task_to_submit - 未找到")

# 完整覆盖写入
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已完整覆盖写入")
