#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改：
1. 将"我的算力"按钮改为"已完成分发任务"
2. 在"我的算力统计"消息开头添加标准化分隔
"""

# 读取完整文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"📖 读取完成")

# ============================================================
# 修改1: 中文按钮文字
# ============================================================

old_zh_menu = "'menu_my_power': '📊 我的算力',"
new_zh_menu = "'menu_my_power': '📊 已完成分发任务',"

if old_zh_menu in content:
    content = content.replace(old_zh_menu, new_zh_menu)
    print("✅ 修改1: 中文按钮文字 - 完成")
else:
    print("⚠️ 修改1: 中文按钮文字 - 未找到")

# ============================================================
# 修改2: 英文按钮文字
# ============================================================

old_en_menu = "'menu_my_power': '📊 My Power',"
new_en_menu = "'menu_my_power': '📊 Completed Tasks',"

if old_en_menu in content:
    content = content.replace(old_en_menu, new_en_menu)
    print("✅ 修改2: 英文按钮文字 - 完成")
else:
    print("⚠️ 修改2: 英文按钮文字 - 未找到")

# ============================================================
# 修改3: 中文我的算力消息添加分隔
# ============================================================

old_zh_power = """        'my_power': \"\"\"📊 我的算力统计

💰 总 X2C：{total_power}
✅ 已完成任务：{completed_tasks}
🔄 进行中任务：{in_progress_tasks}
📈 本周排名：#{rank}\"\"\","""

new_zh_power = """        'my_power': \"\"\"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 【已完成分发任务】

💰 总 X2C：{total_power}
✅ 已完成任务：{completed_tasks}
🔄 进行中任务：{in_progress_tasks}
📈 本周排名：#{rank}\"\"\","""

if old_zh_power in content:
    content = content.replace(old_zh_power, new_zh_power)
    print("✅ 修改3: 中文我的算力消息添加分隔 - 完成")
else:
    print("⚠️ 修改3: 中文我的算力消息 - 未找到")

# ============================================================
# 修改4: 英文我的算力消息添加分隔
# ============================================================

old_en_power = """        'my_power': \"\"\"📊 My X2C Stats

💰 Total X2C: {total_power}
✅ Completed Tasks: {completed_tasks}
🔄 In Progress: {in_progress_tasks}
📈 This Week Rank: #{rank}\"\"\","""

new_en_power = """        'my_power': \"\"\"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 【Completed Tasks】

💰 Total X2C: {total_power}
✅ Completed Tasks: {completed_tasks}
🔄 In Progress: {in_progress_tasks}
📈 This Week Rank: #{rank}\"\"\","""

if old_en_power in content:
    content = content.replace(old_en_power, new_en_power)
    print("✅ 修改4: 英文我的算力消息添加分隔 - 完成")
else:
    print("⚠️ 修改4: 英文我的算力消息 - 未找到")

# 完整覆盖写入
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已完整覆盖写入")
