"""
重试提交处理函数
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def retry_submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理重试提交按钮点击"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    task_id = int(query.data.split('_')[-1])
    
    # 从 bot.py 导入必要的函数
    from bot import get_user_language, submit_task_link, get_user_stats, get_db_connection
    
    user_lang = get_user_language(user_id)
    
    logger.info(f"🔁 用户 {user_id} 请求重试提交任务 {task_id}")
    
    # 检查是否有缓存的验证结果
    verified_data = context.user_data.get('verified_submission')
    
    if not verified_data:
        error_msg = (
            "❌ 重试失败\n\n"
            "验证结果已过期，请重新提交链接"
        ) if user_lang == 'zh' else (
            "❌ Retry Failed\n\n"
            "Verification result expired, please resubmit the link"
        )
        await query.edit_message_text(
            text=error_msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« 返回" if user_lang == 'zh' else "« Back", callback_data='submit_link')
            ]])
        )
        return
    
    # 检查缓存是否过期（10分钟）
    cached_time = verified_data.get('timestamp', 0)
    current_time = datetime.now().timestamp()
    if current_time - cached_time > 600:  # 10分钟 = 600秒
        error_msg = (
            "❌ 重试失败\n\n"
            "验证结果已过期（超过10分钟），请重新提交链接"
        ) if user_lang == 'zh' else (
            "❌ Retry Failed\n\n"
            "Verification result expired (over 10 minutes), please resubmit the link"
        )
        await query.edit_message_text(
            text=error_msg,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« 返回" if user_lang == 'zh' else "« Back", callback_data='submit_link')
            ]])
        )
        # 清除过期缓存
        del context.user_data['verified_submission']
        return
    
    # 检查任务ID是否匹配
    if verified_data['task_id'] != task_id:
        error_msg = (
            "❌ 重试失败\n\n"
            "任务不匹配，请重新提交"
        ) if user_lang == 'zh' else (
            "❌ Retry Failed\n\n"
            "Task mismatch, please resubmit"
        )
        await query.edit_message_text(text=error_msg)
        return
    
    # 提取缓存的数据
    platform = verified_data['platform']
    link = verified_data['link']
    verify_result = verified_data['verify_result']
    task = verified_data['task']
    
    logger.info(f"✅ 使用缓存的验证结果重试提交: task_id={task_id}, platform={platform}")
    
    # 显示"正在提交"
    await query.edit_message_text(
        text="⏳ 正在重新提交..." if user_lang == 'zh' else "⏳ Resubmitting...",
        parse_mode='HTML'
    )
    
    # 获取数据库连接
    conn = get_db_connection()
    
    try:
        # 直接提交任务（跳过验证）
        reward = submit_task_link(user_id, task_id, platform, link)
        logger.info(f"✅ 重试提交成功，奖励: {reward} X2C")
        
        # 更新最后提交时间
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET last_submission_time = NOW() WHERE user_id = %s",
                (user_id,)
            )
            conn.commit()
            cur.close()
            logger.info(f"✅ 已更新用户 {user_id} 的最后提交时间")
        except Exception as update_error:
            logger.error(f"⚠️ 更新最后提交时间失败: {update_error}")
            conn.rollback()
        
        # 发送 Webhook 回调通知
        try:
            from webhook_notifier import send_task_completed_webhook
            await send_task_completed_webhook(
                task_id=task_id,
                user_id=user_id,
                platform=platform.lower(),
                submission_link=link,
                node_power_earned=reward,
                verification_details=verify_result
            )
            logger.info(f"📤 Webhook 回调已发送: task_id={task_id}")
        except Exception as webhook_error:
            logger.error(f"⚠️ Webhook 回调失败 (不影响任务提交): {webhook_error}", exc_info=True)
        
        # 清除缓存
        del context.user_data['verified_submission']
        
        # 获取用户统计
        stats = get_user_stats(user_id)
        if stats.get('total_power') is None:
            stats['total_power'] = 0
        
        # 显示成功消息
        success_msg = (
            f"✅ <b>重试成功！任务已提交</b>\n\n"
            f"🎯 任务名称：{task['title']}\n"
            f"📱 平台：{platform.capitalize()}\n"
            f"🔗 已提交：<a href=\"{link}\">查看视频</a>\n\n"
            f"🎁 获得奖励：{reward} X2C\n"
            f"📊 累计算力：{stats['total_power']}\n\n"
            f"🔥 你正在推动短剧全球传播！\n"
            f"继续分发更多内容，解锁更高等级与更多X2C 奖励。"
        ) if user_lang == 'zh' else (
            f"✅ <b>Retry Successful! Task Submitted</b>\n\n"
            f"🎯 Task Name: {task['title']}\n"
            f"📱 Platform: {platform.capitalize()}\n"
            f"🔗 Submitted: <a href=\"{link}\">View Video</a>\n\n"
            f"🎁 Reward Earned: {reward} X2C\n"
            f"📊 Total Power: {stats['total_power']}\n\n"
            f"🔥 You're driving global short drama distribution!\n"
            f"Keep distributing more content to unlock higher levels and more X2C rewards."
        )
        
        back_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 返回主菜单" if user_lang == 'zh' else "🏠 Back to Menu", callback_data='back_to_menu')
        ]])
        
        await query.edit_message_text(
            text=success_msg,
            reply_markup=back_button,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ 重试提交失败: {e}", exc_info=True)
        error_msg = (
            f"❌ <b>重试失败</b>\n\n"
            f"保存仍然失败，请联系管理员\n\n"
            f"错误信息：{str(e)}"
        ) if user_lang == 'zh' else (
            f"❌ <b>Retry Failed</b>\n\n"
            f"Save still failed, please contact admin\n\n"
            f"Error: {str(e)}"
        )
        
        # 再次提供重试按钮
        retry_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 再次重试" if user_lang == 'zh' else "🔁 Retry Again", callback_data=f'retry_submit_{task_id}')
        ]])
        
        await query.edit_message_text(
            text=error_msg,
            reply_markup=retry_button,
            parse_mode='HTML'
        )
    finally:
        conn.close()
