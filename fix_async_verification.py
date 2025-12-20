#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改 link_input_handler 为异步验证模式
"""

# 读取文件
with open('bot.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 定义新的 link_input_handler 函数
new_link_input_handler = '''async def link_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理链接输入（异步验证模式：立即返回，后台验证）"""
    user_id = update.effective_user.id
    user_lang = get_user_language(user_id)
    
    link = update.message.text.strip()
    task_id = context.user_data.get('submit_task_id')
    
    logger.info(f"🔗 link_input_handler called: user_id={user_id}, task_id={task_id}, link={link[:50]}...")
    
    # 获取任务卡片消息 ID
    task_card_message_id = context.user_data.get('task_card_message_id')
    task_card_chat_id = context.user_data.get('task_card_chat_id')
    
    # 立即删除用户的消息
    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"⚠️ 无法删除用户消息: {e}")
    
    # 自动识别平台
    platform = detect_platform(link)
    logger.info(f"🔍 平台识别结果: platform={platform}")
    
    # 验证链接格式
    validation_passed = validate_link(platform, link)
    logger.info(f"🔍 validate_link 结果: platform={platform}, validation_passed={validation_passed}")
    
    if not validation_passed:
        error_msg = (
            "❌ **链接验证失败**\\n\\n"
            "🔍 请检查：\\n"
            "• 链接是否完整（包含 https://）\\n"
            "• 链接是否指向具体的视频页面\\n"
            "• 支持的平台：TikTok、YouTube、Instagram、Facebook、Twitter\\n\\n"
            "🔁 请重新发送正确的链接"
        ) if user_lang.startswith('zh') else (
            "❌ **Link Validation Failed**\\n\\n"
            "🔍 Please check:\\n"
            "• Link is complete (includes https://)\\n"
            "• Link points to a specific video page\\n"
            "• Supported platforms: TikTok, YouTube, Instagram, Facebook, Twitter\\n\\n"
            "🔁 Please resend the correct link"
        )
        
        # 编辑任务卡片显示错误
        if task_card_message_id and task_card_chat_id:
            retry_button = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 重试" if user_lang.startswith('zh') else "🔁 Retry", callback_data=f'submit_task_{task_id}'),
                InlineKeyboardButton("« 返回" if user_lang.startswith('zh') else "« Back", callback_data='back_to_menu')
            ]])
            
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=error_msg,
                reply_markup=retry_button,
                parse_mode='HTML'
            )
        return SUBMIT_LINK
    
    # 反刷量检查
    conn = get_db_connection()
    allowed, error_msg = check_all_limits(conn, user_id, link)
    
    if not allowed:
        # 显示限制错误
        if task_card_message_id and task_card_chat_id:
            retry_button = InlineKeyboardMarkup([[
                InlineKeyboardButton("« 返回" if user_lang.startswith('zh') else "« Back", callback_data='back_to_menu')
            ]])
            
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=error_msg,
                reply_markup=retry_button,
                parse_mode='HTML'
            )
        conn.close()
        return SUBMIT_LINK
    
    # 获取任务信息
    cur = conn.cursor()
    cur.execute("SELECT title, description, node_power_reward FROM drama_tasks WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    cur.close()
    conn.close()
    
    if not task:
        if task_card_message_id and task_card_chat_id:
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text="❌ 任务不存在" if user_lang.startswith('zh') else "❌ Task not found"
            )
        return ConversationHandler.END
    
    # 先验证链接格式（快速检查）
    logger.info(f"🔍 验证链接格式: platform={platform}, url={link[:50]}...")
    validation_result = link_verifier.validate_platform_url(link, platform)
    
    if not validation_result['valid']:
        logger.warning(f"⚠️ 链接格式不合法: {validation_result['error_message']}")
        
        error_text = (
            f"❌ **链接格式错误**\\n\\n"
            f"📝 {validation_result['error_message']}\\n\\n"
            f"🔗 您提供的链接: {link[:100]}...\\n\\n"
            f"✅ 请确保提交的是正确的平台视频链接。"
        ) if user_lang.startswith('zh') else (
            f"❌ **Invalid Link Format**\\n\\n"
            f"📝 {validation_result['error_message']}\\n\\n"
            f"🔗 Your link: {link[:100]}...\\n\\n"
            f"✅ Please make sure to submit a valid platform video link."
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=error_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 重试" if user_lang.startswith('zh') else "🔁 Retry", callback_data=f"submit_link_{task_id}")],
                    [InlineKeyboardButton("« 返回" if user_lang.startswith('zh') else "« Back", callback_data=f"view_task_{task_id}")]
                ])
            )
        except Exception as e:
            logger.error(f"❌ 发送链接格式错误消息失败: {e}", exc_info=True)
        
        return ConversationHandler.END
    
    # ========== 异步验证模式：立即返回，后台验证 ==========
    
    # 将链接添加到验证队列
    from async_verification_worker import add_to_verification_queue
    queue_id = add_to_verification_queue(user_id, task_id, link, platform)
    
    if queue_id is None:
        # 该链接已经验证完成
        success_msg = (
            "✅ **该链接已提交过**\\n\\n"
            "此链接之前已成功验证并获得奖励。\\n"
            "请提交新的视频链接。"
        ) if user_lang.startswith('zh') else (
            "✅ **Link Already Submitted**\\n\\n"
            "This link was already verified and rewarded.\\n"
            "Please submit a new video link."
        )
        
        if task_card_message_id and task_card_chat_id:
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=success_msg,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 返回主菜单" if user_lang.startswith('zh') else "🏠 Back to Menu", callback_data='back_to_menu')
                ]])
            )
        return ConversationHandler.END
    
    # 立即返回"已接收"消息
    received_msg = (
        f"✅ <b>链接已接收！</b>\\n\\n"
        f"🎬 任务：{task['title']}\\n"
        f"💰 奖励：{task['node_power_reward']} X2C\\n\\n"
        f"🔍 系统正在后台核验中，请稍候...\\n"
        f"核验完成后会自动通知您结果。\\n\\n"
        f"💡 您现在可以继续领取其他任务！"
    ) if user_lang.startswith('zh') else (
        f"✅ <b>Link Received!</b>\\n\\n"
        f"🎬 Task: {task['title']}\\n"
        f"💰 Reward: {task['node_power_reward']} X2C\\n\\n"
        f"🔍 System is verifying in background...\\n"
        f"You will be notified when verification is complete.\\n\\n"
        f"💡 You can continue to claim other tasks!"
    )
    
    if task_card_message_id and task_card_chat_id:
        await context.bot.edit_message_text(
            chat_id=task_card_chat_id,
            message_id=task_card_message_id,
            text=received_msg,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 返回主菜单" if user_lang.startswith('zh') else "🏠 Back to Menu", callback_data='back_to_menu')
            ]]),
            disable_web_page_preview=True
        )
    
    logger.info(f"✅ 链接已加入验证队列: queue_id={queue_id}, user={user_id}, task={task_id}")
    
    return ConversationHandler.END'''

# 查找旧的 link_input_handler 函数
import re

# 找到函数开始位置
start_pattern = r'async def link_input_handler\(update: Update, context: ContextTypes\.DEFAULT_TYPE\):'
start_match = re.search(start_pattern, content)

if start_match:
    start_pos = start_match.start()
    
    # 找到下一个顶级函数定义（不缩进的 async def 或 def）
    # 从 link_input_handler 之后开始搜索
    remaining_content = content[start_match.end():]
    
    # 查找下一个顶级函数
    next_func_pattern = r'\n(?:async )?def \w+\('
    next_func_match = re.search(next_func_pattern, remaining_content)
    
    if next_func_match:
        end_pos = start_match.end() + next_func_match.start()
        
        # 替换函数
        new_content = content[:start_pos] + new_link_input_handler + content[end_pos:]
        
        # 写入文件
        with open('bot.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ link_input_handler 函数已替换为异步验证模式")
        print(f"   原函数位置: {start_pos} - {end_pos}")
    else:
        print("❌ 无法找到函数结束位置")
else:
    print("❌ 无法找到 link_input_handler 函数")
