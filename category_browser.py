#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧集分类浏览功能
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from category_classifier import get_all_categories, get_category_name
import logging

logger = logging.getLogger(__name__)


async def show_tasks_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str = 'latest'):
    """
    按分类显示任务列表
    
    Args:
        update: Telegram Update 对象
        context: Context 对象
        category: 分类代码（默认 latest）
    """
    from bot import get_db_connection, get_user_language, get_task_title, get_message
    
    query = update.callback_query
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    logger.info(f"📂 show_tasks_by_category: user_id={user_id}, category={category}")
    
    # 获取该分类的任务（最多 10 条）
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 查询该分类的活跃任务
    cur.execute("""
        SELECT * FROM drama_tasks
        WHERE status = 'active' AND category = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (category,))
    tasks = cur.fetchall()
    
    # 获取用户已领取的任务ID
    cur.execute("""
        SELECT task_id FROM user_tasks
        WHERE user_id = %s
    """, (user_id,))
    claimed_task_ids = {row['task_id'] for row in cur.fetchall()}
    
    cur.close()
    conn.close()
    
    # 过滤掉已领取的任务
    available_tasks = [task for task in tasks if task['task_id'] not in claimed_task_ids]
    
    logger.info(f"📊 分类 {category}: 总任务 {len(tasks)}, 可领取 {len(available_tasks)}")
    
    # 构建分类切换按钮
    categories = get_all_categories(user_lang)
    category_buttons = []
    
    # 每行显示 3 个分类按钮
    row = []
    for cat_code, cat_name in list(categories.items())[:12]:  # 只显示前 12 个分类
        # 当前分类用 ✓ 标记
        button_text = f"✓ {cat_name}" if cat_code == category else cat_name
        row.append(InlineKeyboardButton(button_text, callback_data=f"category_{cat_code}"))
        
        if len(row) == 3:
            category_buttons.append(row)
            row = []
    
    if row:  # 添加最后一行
        category_buttons.append(row)
    
    # 构建任务列表
    keyboard = []
    
    if available_tasks:
        # 添加任务按钮
        for task in available_tasks:
            title = get_task_title(task, user_lang)
            button_text = f"🎬 {title} ({task['duration']}s) - {task['node_power_reward']} X2C"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"claim_{task['task_id']}")])
        
        # 添加分隔线
        keyboard.append([InlineKeyboardButton("━━━━━ 切换分类 ━━━━━", callback_data="noop")])
    else:
        # 没有可用任务
        no_tasks_msg = "该分类暂无可领取任务" if user_lang.startswith('zh') else "No tasks available in this category"
        keyboard.append([InlineKeyboardButton(f"ℹ️ {no_tasks_msg}", callback_data="noop")])
        keyboard.append([InlineKeyboardButton("━━━━━ 切换分类 ━━━━━", callback_data="noop")])
    
    # 添加分类按钮
    keyboard.extend(category_buttons)
    
    # 添加返回主菜单按钮
    keyboard.append([InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')])
    
    # 构建消息文本
    category_name = get_category_name(category, user_lang)
    if user_lang.startswith('zh'):
        message_text = f"📂 剧集分类：{category_name}\n\n📋 选择你想要领取的任务："
    else:
        message_text = f"📂 Category: {category_name}\n\n📋 Select a task to claim:"
    
    await query.edit_message_text(
        message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def category_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理分类切换回调
    """
    query = update.callback_query
    await query.answer()
    
    # 提取分类代码
    category = query.data.split('_')[1]
    
    # 显示该分类的任务
    await show_tasks_by_category(update, context, category)
