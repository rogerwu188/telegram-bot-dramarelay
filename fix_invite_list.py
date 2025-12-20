#!/usr/bin/env python3
"""修改邀请好友功能，添加被邀请人列表和翻页"""

# 读取bot.py
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的invite_friends_callback函数
old_func = '''async def invite_friends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理邀请好友"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 生成邀请链接
    invite_link = f"https://t.me/{BOT_USERNAME}?start=invite_{user_id}"
    
    # 获取邀请统计
    from invitation_system import get_invitation_stats
    stats = get_invitation_stats(user_id)
    
    message = get_message(user_lang, 'invite_friends',
        invite_link=invite_link,
        invited_count=stats['invited_count'],
        active_count=stats['active_count'],
        total_rewards=stats['total_rewards']
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_message(user_lang, 'share_link'), url=f"https://t.me/share/url?url={invite_link}")],
        [InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')]
    ])
    
    await query.edit_message_text(message, reply_markup=keyboard, disable_web_page_preview=True)'''

# 新的invite_friends_callback函数（支持翻页）
new_func = '''async def invite_friends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    """处理邀请好友"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 生成邀请链接
    invite_link = f"https://t.me/{BOT_USERNAME}?start=invite_{user_id}"
    
    # 获取邀请统计
    from invitation_system import get_invitation_stats, get_active_invitees
    stats = get_invitation_stats(user_id)
    
    # 获取有效被邀请人列表
    invitees_data = get_active_invitees(user_id, page=page, per_page=10)
    
    message = get_message(user_lang, 'invite_friends',
        invite_link=invite_link,
        invited_count=stats['invited_count'],
        active_count=stats['active_count'],
        total_rewards=stats['total_rewards']
    )
    
    # 添加有效被邀请人列表
    if invitees_data['invitees']:
        if user_lang == 'zh':
            message += "\\n\\n👥 有效邀请列表："
        else:
            message += "\\n\\n👥 Active Invitees:"
        
        for inv in invitees_data['invitees']:
            username = inv.get('username') or inv.get('first_name') or f"User_{inv['user_id']}"
            if inv.get('username'):
                message += f"\\n• @{username}"
            else:
                message += f"\\n• {username}"
        
        # 显示分页信息
        if invitees_data['total_pages'] > 1:
            if user_lang == 'zh':
                message += f"\\n\\n📄 第 {page}/{invitees_data['total_pages']} 页"
            else:
                message += f"\\n\\n📄 Page {page}/{invitees_data['total_pages']}"
    
    # 构建键盘
    keyboard_rows = []
    
    # 分页按钮
    if invitees_data['total_pages'] > 1:
        pagination_row = []
        if page > 1:
            if user_lang == 'zh':
                pagination_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f'invite_page_{page-1}'))
            else:
                pagination_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'invite_page_{page-1}'))
        if page < invitees_data['total_pages']:
            if user_lang == 'zh':
                pagination_row.append(InlineKeyboardButton("下一页 ➡️", callback_data=f'invite_page_{page+1}'))
            else:
                pagination_row.append(InlineKeyboardButton("Next ➡️", callback_data=f'invite_page_{page+1}'))
        if pagination_row:
            keyboard_rows.append(pagination_row)
    
    # 分享按钮
    keyboard_rows.append([InlineKeyboardButton(get_message(user_lang, 'share_link'), url=f"https://t.me/share/url?url={invite_link}")])
    # 返回按钮
    keyboard_rows.append([InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')])
    
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    
    await query.edit_message_text(message, reply_markup=keyboard, disable_web_page_preview=True)


async def invite_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理邀请列表翻页"""
    query = update.callback_query
    
    # 从callback_data中提取页码
    page = int(query.data.split('_')[-1])
    
    # 调用invite_friends_callback并传入页码
    await invite_friends_callback(update, context, page=page)'''

if old_func in content:
    content = content.replace(old_func, new_func)
    print("✅ 已修改 invite_friends_callback 函数")
else:
    print("❌ 未找到 invite_friends_callback 函数")

# 添加翻页回调处理器
old_handler = "application.add_handler(CallbackQueryHandler(invite_friends_callback, pattern='^invite_friends$'))"
new_handler = """application.add_handler(CallbackQueryHandler(invite_friends_callback, pattern='^invite_friends$'))
    application.add_handler(CallbackQueryHandler(invite_page_callback, pattern='^invite_page_'))"""

if old_handler in content:
    content = content.replace(old_handler, new_handler)
    print("✅ 已添加翻页回调处理器")
else:
    print("❌ 未找到处理器注册位置")

# 写回文件
with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修改完成")
