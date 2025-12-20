#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化所有消息之间的视觉区隔
"""

# 读取完整文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"📖 读取完成")

# 定义标准分隔线
SEPARATOR = "━" * 30

# ============================================================
# 修改1: 中文欢迎消息开头添加分隔
# ============================================================

old_zh_welcome = """        'welcome': \"\"\"🎬 X2C 流量节点 (Traffic Node) 已连接
欢迎回来，节点 @{username}。"""

new_zh_welcome = """        'welcome': \"\"\"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 【主菜单】

🎬 X2C 流量节点 (Traffic Node) 已连接
欢迎回来，节点 @{username}。"""

if old_zh_welcome in content:
    content = content.replace(old_zh_welcome, new_zh_welcome)
    print("✅ 修改1: 中文欢迎消息开头添加分隔 - 完成")
else:
    print("⚠️ 修改1: 中文欢迎消息 - 未找到")

# ============================================================
# 修改2: 英文欢迎消息开头添加分隔
# ============================================================

old_en_welcome = """        'welcome': \"\"\"🎬 X2C Traffic Node Connected
Welcome back, Node @{username}."""

new_en_welcome = """        'welcome': \"\"\"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 【Main Menu】

🎬 X2C Traffic Node Connected
Welcome back, Node @{username}."""

if old_en_welcome in content:
    content = content.replace(old_en_welcome, new_en_welcome)
    print("✅ 修改2: 英文欢迎消息开头添加分隔 - 完成")
else:
    print("⚠️ 修改2: 英文欢迎消息 - 未找到")

# ============================================================
# 修改3: 中文任务领取成功消息添加分隔
# ============================================================

old_zh_claimed = "'task_claimed': '✅ 任务领取成功！\\n\\n正在下载视频，下载完成后请上传到你选择的平台，然后回来提交链接。',"

new_zh_claimed = "'task_claimed': '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n📥 【任务已领取】\\n\\n✅ 任务领取成功！\\n\\n正在下载视频，下载完成后请上传到你选择的平台，然后回来提交链接。',"

if old_zh_claimed in content:
    content = content.replace(old_zh_claimed, new_zh_claimed)
    print("✅ 修改3: 中文任务领取成功消息添加分隔 - 完成")
else:
    print("⚠️ 修改3: 中文任务领取成功消息 - 未找到")

# ============================================================
# 修改4: 英文任务领取成功消息添加分隔
# ============================================================

old_en_claimed = "'task_claimed': '✅ Task claimed successfully!\\n\\nDownloading video, please upload to your chosen platform after download, then come back to submit the link.',"

new_en_claimed = "'task_claimed': '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n\\n📥 【Task Claimed】\\n\\n✅ Task claimed successfully!\\n\\nDownloading video, please upload to your chosen platform after download, then come back to submit the link.',"

if old_en_claimed in content:
    content = content.replace(old_en_claimed, new_en_claimed)
    print("✅ 修改4: 英文任务领取成功消息添加分隔 - 完成")
else:
    print("⚠️ 修改4: 英文任务领取成功消息 - 未找到")

# 完整覆盖写入
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已完整覆盖写入")
