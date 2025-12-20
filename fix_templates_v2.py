#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改bot.py中的消息模板：
1. 简化复制框内容，不区分YouTube/TikTok
2. 移除Title/Description标签，只保留实际内容
3. 在复制框标题后添加提示语
"""

# 读取文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 修改1: 中文大文件下载消息
# ============================================================

old_zh_large = '''━━━━━━━━━━━━━━━━━━
📋【一键复制内容】

<pre>
【YouTube】
标题: {plot_keyword} | {drama_name}
描述: {description}

【TikTok】
描述: {description}

{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━
💰【奖励说明】'''

new_zh_large = '''━━━━━━━━━━━━━━━━━━
📋【一键复制内容】
💡 请复制到 TikTok 或 YouTube

<pre>
{plot_keyword} | {drama_name}
{description}
{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━
💰【奖励说明】'''

content = content.replace(old_zh_large, new_zh_large)
print("✅ 修改1: 中文大文件下载消息 - 完成")

# ============================================================
# 修改2: 英文大文件下载消息
# ============================================================

old_en_large = '''━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】

<pre>
【YouTube】
Title: {title}
Description: {description}

【TikTok】
Description: {description}

{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━
💰【Reward】'''

new_en_large = '''━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】
💡 Please copy to TikTok or YouTube

<pre>
{title}
{description}
{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━
💰【Reward】'''

content = content.replace(old_en_large, new_en_large)
print("✅ 修改2: 英文大文件下载消息 - 完成")

# ============================================================
# 修改3: 中文正常任务消息
# ============================================================

old_zh_normal = '''━━━━━━━━━━━━━━━━━━
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
💰【奖励说明】'''

new_zh_normal = '''━━━━━━━━━━━━━━━━━━
📋【一键复制内容】
💡 请复制到 TikTok 或 YouTube

```
{plot_keyword} | {drama_name}
{description}
{hashtags}
```

━━━━━━━━━━━━━━━━━━
💰【奖励说明】'''

content = content.replace(old_zh_normal, new_zh_normal)
print("✅ 修改3: 中文正常任务消息 - 完成")

# ============================================================
# 修改4: 英文正常任务消息
# ============================================================

old_en_normal = '''━━━━━━━━━━━━━━━━━━
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
💰【Reward】'''

new_en_normal = '''━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】
💡 Please copy to TikTok or YouTube

```
{title}
{description}
{hashtags}
```

━━━━━━━━━━━━━━━━━━
💰【Reward】'''

content = content.replace(old_en_normal, new_en_normal)
print("✅ 修改4: 英文正常任务消息 - 完成")

# ============================================================
# 修改5: 中文提交任务消息 (message_parts)
# ============================================================

old_zh_submit = '''        message_parts.append("📋【一键复制内容】")
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
        message_parts.append("</pre>")'''

new_zh_submit = '''        message_parts.append("📋【一键复制内容】")
        message_parts.append("💡 请复制到 TikTok 或 YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(f"{plot_keyword} | {drama_name}")
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")'''

content = content.replace(old_zh_submit, new_zh_submit)
print("✅ 修改5: 中文提交任务消息 - 完成")

# ============================================================
# 修改6: 英文提交任务消息 (message_parts)
# ============================================================

old_en_submit = '''        message_parts.append("📋【One-Click Copy Content】")
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
        message_parts.append("</pre>")'''

new_en_submit = '''        message_parts.append("📋【One-Click Copy Content】")
        message_parts.append("💡 Please copy to TikTok or YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(title)
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")'''

content = content.replace(old_en_submit, new_en_submit)
print("✅ 修改6: 英文提交任务消息 - 完成")

# 写入文件
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ 所有消息模板修改完成！")
print("📁 已保存到 bot.py")
