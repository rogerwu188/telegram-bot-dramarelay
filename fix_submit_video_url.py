#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复提交任务界面，添加视频链接显示
"""

# 读取完整文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"📖 读取完成")

# ============================================================
# 修改1: 在获取任务信息后添加video_url变量
# ============================================================

old_get_task = '''    # 显示提交界面（包含完整的描述和标签）
    title = task.get('title', '')
    # 兼容不同的字段名：description 或 task_template
    description = task.get('description') or task.get('task_template', '') or ''
    # 兼容不同的字段名：keywords 或 keywords_template
    keywords_raw = task.get('keywords') or task.get('keywords_template', '') or ''
    reward = task.get('node_power_reward', 0)'''

new_get_task = '''    # 显示提交界面（包含完整的描述和标签）
    title = task.get('title', '')
    # 兼容不同的字段名：description 或 task_template
    description = task.get('description') or task.get('task_template', '') or ''
    # 兼容不同的字段名：keywords 或 keywords_template
    keywords_raw = task.get('keywords') or task.get('keywords_template', '') or ''
    reward = task.get('node_power_reward', 0)
    # 获取视频链接
    video_url = task.get('video_url', '')'''

if old_get_task in content:
    content = content.replace(old_get_task, new_get_task)
    print("✅ 修改1: 添加video_url变量 - 完成")
else:
    print("⚠️ 修改1: 添加video_url变量 - 未找到")

# ============================================================
# 修改2: 中文提交任务消息添加视频链接
# ============================================================

old_zh_submit = '''    if user_lang == 'zh':
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【一键复制内容】")
        message_parts.append("💡 请复制到 TikTok 或 YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(f"{plot_keyword} | {drama_name}")
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 请粘贴你上传的视频链接（支持 TikTok、YouTube、Instagram 等平台）")'''

new_zh_submit = '''    if user_lang == 'zh':
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        if video_url:
            message_parts.append(f"🔗 视频链接：{video_url}")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【一键复制内容】")
        message_parts.append("💡 请复制到 TikTok 或 YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(f"{plot_keyword} | {drama_name}")
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 请粘贴你上传的视频链接（支持 TikTok、YouTube、Instagram 等平台）")'''

if old_zh_submit in content:
    content = content.replace(old_zh_submit, new_zh_submit)
    print("✅ 修改2: 中文提交任务消息添加视频链接 - 完成")
else:
    print("⚠️ 修改2: 中文提交任务消息添加视频链接 - 未找到")

# ============================================================
# 修改3: 英文提交任务消息添加视频链接
# ============================================================

old_en_submit = '''    else:
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【One-Click Copy Content】")
        message_parts.append("💡 Please copy to TikTok or YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(title)
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)")'''

new_en_submit = '''    else:
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        if video_url:
            message_parts.append(f"🔗 Video Link: {video_url}")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【One-Click Copy Content】")
        message_parts.append("💡 Please copy to TikTok or YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(title)
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)")'''

if old_en_submit in content:
    content = content.replace(old_en_submit, new_en_submit)
    print("✅ 修改3: 英文提交任务消息添加视频链接 - 完成")
else:
    print("⚠️ 修改3: 英文提交任务消息添加视频链接 - 未找到")

# 完整覆盖写入
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ 文件已完整覆盖写入")
