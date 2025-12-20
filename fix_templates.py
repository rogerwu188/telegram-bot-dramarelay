#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改bot.py中的所有6处消息模板，将多个代码块合并为单个代码块
"""

import re

# 读取文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 修改1: 中文大文件下载消息 (已经修改过，跳过)
# ============================================================

# ============================================================
# 修改2: 英文大文件下载消息 (已经修改过，跳过)
# ============================================================

# ============================================================
# 修改3: 中文正常任务消息
# ============================================================

old_zh_normal = '''            if user_lang == 'zh':
                final_msg = f"""🔗 视频链接：{video_url}

📥 视频已下载，请选择任意平台发布内容，即可获得对应奖励：

━━━━━━━━━━━━━━━━━━
🎬【YouTube 上传内容】

▶️ 视频文件名称（右键直接另存，或直接拖拽）：
{plot_keyword} · {drama_name_with_brackets}

▶️ 复制到 YouTube Title栏：
{plot_keyword} | {drama_name}

▶️ 复制到 YouTube Description栏：
{description}

（YouTube 不需要填写标签，保持空白即可）

━━━━━━━━━━━━━━━━━━
🎬【TikTok 上传内容】

▶️ TikTok 视频描述（请完整复制以下内容）：
{description}

{hashtags}

━━━━━━━━━━━━━━━━━━
💰【奖励说明】

完成以上任务，点击下方的"提交链接"按钮，机器人验证通过你发布后的视频链接  
即可获得 🎉 {reward} X2C\"\"\''''

new_zh_normal = '''            if user_lang == 'zh':
                final_msg = f"""🔗 视频链接：{video_url}

📥 视频已下载，请选择任意平台发布内容，即可获得对应奖励：

━━━━━━━━━━━━━━━━━━
📋【一键复制内容】

```
【YouTube】
标题: {plot_keyword} | {drama_name}
描述: {description}

【TikTok】
描述: {description}

{hashtags}
```

━━━━━━━━━━━━━━━━━━
💰【奖励说明】

完成以上任务，点击下方的"提交链接"按钮，机器人验证通过你发布后的视频链接  
即可获得 🎉 {reward} X2C\"\"\''''

content = content.replace(old_zh_normal, new_zh_normal)
print("✅ 修改3: 中文正常任务消息 - 完成")

# ============================================================
# 修改4: 英文正常任务消息
# ============================================================

old_en_normal = '''            else:
                final_msg = f"""🔗 Video Link: {video_url}

📥 Please download the video and upload to any platform to receive rewards:

━━━━━━━━━━━━━━━━━━
🎬【YouTube Upload Content】

▶ Video Title (copy directly):
```
{title}
```

▶ Video Description (paste in YouTube description):
```
{description}
```

(YouTube does not require tags, leave blank)

━━━━━━━━━━━━━━━━━━
🎬【TikTok Upload Content】

▶ TikTok Description (copy completely):
```
{description}
```

▶ TikTok Hashtags (paste below description):
```
{hashtags}
```

━━━━━━━━━━━━━━━━━━
💰【Reward】

Complete the task above and submit your published video link in this bot  
to receive 🎉 {reward} X2C\"\"\"
                
                # 创建 inline keyboard 按钮
                keyboard = [
                    [InlineKeyboardButton("📎 Submit Link", callback_data=f"submit_link_{task_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)'''

new_en_normal = '''            else:
                final_msg = f"""🔗 Video Link: {video_url}

📥 Please download the video and upload to any platform to receive rewards:

━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】

```
【YouTube】
Title: {title}
Description: {description}

【TikTok】
Description: {description}

{hashtags}
```

━━━━━━━━━━━━━━━━━━
💰【Reward】

Complete the task above and submit your published video link in this bot  
to receive 🎉 {reward} X2C\"\"\"
                
                # 创建 inline keyboard 按钮
                keyboard = [
                    [InlineKeyboardButton("📎 Submit Link", callback_data=f"submit_link_{task_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)'''

content = content.replace(old_en_normal, new_en_normal)
print("✅ 修改4: 英文正常任务消息 - 完成")

# ============================================================
# 修改5: 中文提交任务消息 (message_parts)
# ============================================================

old_zh_submit = '''    if user_lang == 'zh':
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("🎬【YouTube 上传内容】")
        message_parts.append("")
        message_parts.append(f"▶️ 视频文件名称：")
        message_parts.append(f"{plot_keyword} · {drama_name_with_brackets}")
        message_parts.append("")
        message_parts.append(f"▶️ 复制到 YouTube Title栏：")
        message_parts.append(f"{plot_keyword} | {drama_name}")
        message_parts.append("")
        message_parts.append(f"▶️ 复制到 YouTube Description栏：")
        message_parts.append(description)
        message_parts.append("")
        message_parts.append("（YouTube 不需要填写标签，保持空白即可）")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("🎬【TikTok 上传内容】")
        message_parts.append("")
        message_parts.append("▶️ TikTok 视频描述（请完整复制以下内容）：")
        message_parts.append(description)
        message_parts.append("")
        message_parts.append(hashtags)
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 请粘贴你上传的视频链接（支持 TikTok、YouTube、Instagram 等平台）")'''

new_zh_submit = '''    if user_lang == 'zh':
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【一键复制内容】")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append("【YouTube】")
        message_parts.append(f"标题: {plot_keyword} | {drama_name}")
        message_parts.append(f"描述: {description}")
        message_parts.append("")
        message_parts.append("【TikTok】")
        message_parts.append(f"描述: {description}")
        message_parts.append("")
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 请粘贴你上传的视频链接（支持 TikTok、YouTube、Instagram 等平台）")'''

content = content.replace(old_zh_submit, new_zh_submit)
print("✅ 修改5: 中文提交任务消息 - 完成")

# ============================================================
# 修改6: 英文提交任务消息 (message_parts)
# ============================================================

old_en_submit = '''    else:
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("🎬【YouTube Upload Content】")
        message_parts.append("")
        message_parts.append("▶ Video Title (copy directly):")
        message_parts.append("```")
        message_parts.append(title)
        message_parts.append("```")
        message_parts.append("")
        message_parts.append("▶ Video Description (paste in YouTube description):")
        message_parts.append("```")
        message_parts.append(description)
        message_parts.append("```")
        message_parts.append("")
        message_parts.append("(YouTube does not require tags, leave blank)")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("🎬【TikTok Upload Content】")
        message_parts.append("")
        message_parts.append("▶ TikTok Description (copy completely):")
        message_parts.append("```")
        message_parts.append(description)
        message_parts.append("```")
        message_parts.append("")
        message_parts.append("▶ TikTok Hashtags (paste below description):")
        message_parts.append("```")
        message_parts.append(hashtags)
        message_parts.append("```")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)")'''

new_en_submit = '''    else:
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【One-Click Copy Content】")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append("【YouTube】")
        message_parts.append(f"Title: {title}")
        message_parts.append(f"Description: {description}")
        message_parts.append("")
        message_parts.append("【TikTok】")
        message_parts.append(f"Description: {description}")
        message_parts.append("")
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)")'''

content = content.replace(old_en_submit, new_en_submit)
print("✅ 修改6: 英文提交任务消息 - 完成")

# 写入文件
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ 所有6处消息模板修改完成！")
print("📁 已保存到 bot.py")
