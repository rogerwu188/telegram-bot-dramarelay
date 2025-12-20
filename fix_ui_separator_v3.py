#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复UI体验：在提交任务消息开头添加分隔线
"""

# 读取完整文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"📖 读取完成")

# ============================================================
# 修改1: 中文提交任务消息开头添加分隔
# ============================================================

old_zh_submit = '''    if user_lang == 'zh':
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        if video_url:
            message_parts.append(f"🔗 视频链接：{video_url}")'''

new_zh_submit = '''    if user_lang == 'zh':
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("🆕 <b>【新任务】</b>")
        message_parts.append("")
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        if video_url:
            message_parts.append(f"🔗 视频链接：{video_url}")'''

if old_zh_submit in content:
    content = content.replace(old_zh_submit, new_zh_submit)
    print("✅ 修改1: 中文提交任务消息开头添加分隔 - 完成")
else:
    print("⚠️ 修改1: 中文提交任务消息 - 未找到")

# ============================================================
# 修改2: 英文提交任务消息开头添加分隔
# ============================================================

old_en_submit = '''    else:
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        if video_url:
            message_parts.append(f"🔗 Video Link: {video_url}")'''

new_en_submit = '''    else:
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("🆕 <b>【New Task】</b>")
        message_parts.append("")
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        if video_url:
            message_parts.append(f"🔗 Video Link: {video_url}")'''

if old_en_submit in content:
    content = content.replace(old_en_submit, new_en_submit)
    print("✅ 修改2: 英文提交任务消息开头添加分隔 - 完成")
else:
    print("⚠️ 修改2: 英文提交任务消息 - 未找到")

# 完整覆盖写入
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已完整覆盖写入")
