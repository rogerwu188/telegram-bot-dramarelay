#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复中英文正常任务消息（点击任务后发送视频的消息）
"""

# 读取文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 修改1: 中文正常任务消息（旧格式还未修改）
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
💡 请复制到 TikTok 或 YouTube

{plot_keyword} | {drama_name}
{description}
{hashtags}

━━━━━━━━━━━━━━━━━━
💰【奖励说明】

完成以上任务，点击下方的"提交链接"按钮，机器人验证通过你发布后的视频链接  
即可获得 🎉 {reward} X2C\"\"\''''

if old_zh_normal in content:
    content = content.replace(old_zh_normal, new_zh_normal)
    print("✅ 修改1: 中文正常任务消息 - 完成")
else:
    print("⚠️ 修改1: 中文正常任务消息 - 未找到匹配内容")

# ============================================================
# 修改2: 英文正常任务消息（移除```符号，因为parse_mode=None）
# ============================================================

old_en_normal = '''            else:
                final_msg = f"""🔗 Video Link: {video_url}

📥 Please download the video and upload to any platform to receive rewards:

━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】
💡 Please copy to TikTok or YouTube

```
{title}
{description}
{hashtags}
```

━━━━━━━━━━━━━━━━━━
💰【Reward】

Complete the task above and submit your published video link in this bot  
to receive 🎉 {reward} X2C\"\"\''''

new_en_normal = '''            else:
                final_msg = f"""🔗 Video Link: {video_url}

📥 Please download the video and upload to any platform to receive rewards:

━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】
💡 Please copy to TikTok or YouTube

{title}
{description}
{hashtags}

━━━━━━━━━━━━━━━━━━
💰【Reward】

Complete the task above and submit your published video link in this bot  
to receive 🎉 {reward} X2C\"\"\''''

if old_en_normal in content:
    content = content.replace(old_en_normal, new_en_normal)
    print("✅ 修改2: 英文正常任务消息 - 完成")
else:
    print("⚠️ 修改2: 英文正常任务消息 - 未找到匹配内容")

# 写入文件
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ 修改完成！")
