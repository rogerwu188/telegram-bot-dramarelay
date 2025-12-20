#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复：禁用视频链接预览，避免显示大的视频预览窗口
"""

# 读取完整文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"📖 读取完成")

# ============================================================
# 修改1: 大文件下载链接消息禁用预览
# ============================================================

old_large_file = '''            # 发送消息
            hint_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=download_msg,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=False
            )'''

new_large_file = '''            # 发送消息
            hint_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=download_msg,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )'''

if old_large_file in content:
    content = content.replace(old_large_file, new_large_file)
    print("✅ 修改1: 大文件下载链接消息禁用预览 - 完成")
else:
    print("⚠️ 修改1: 大文件下载链接消息 - 未找到")

# ============================================================
# 修改2: 正常任务消息添加禁用预览
# ============================================================

old_normal_msg = '''            # 发送新的提示消息（在视频之后）
            hint_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=final_msg,
                reply_markup=reply_markup,
                parse_mode=None
            )'''

new_normal_msg = '''            # 发送新的提示消息（在视频之后）
            hint_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=final_msg,
                reply_markup=reply_markup,
                parse_mode=None,
                disable_web_page_preview=True
            )'''

if old_normal_msg in content:
    content = content.replace(old_normal_msg, new_normal_msg)
    print("✅ 修改2: 正常任务消息添加禁用预览 - 完成")
else:
    print("⚠️ 修改2: 正常任务消息 - 未找到")

# 完整覆盖写入
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已完整覆盖写入")
