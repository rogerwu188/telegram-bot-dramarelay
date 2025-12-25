#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剧集分类浏览功能
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from x2c_category_sync import get_all_categories_for_bot
import logging

logger = logging.getLogger(__name__)


async def show_tasks_by_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str = 'latest', page: int = 1):
    """
    按分类显示任务列表
    
    Args:
        update: Telegram Update 对象
        context: Context 对象
        category: 分类代码（默认 latest）
        page: 页码（默认 1）
    """
    from bot import get_db_connection, get_user_language, get_task_title, get_message, get_display_reward
    
    query = update.callback_query
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 分页参数
    page_size = 10  # 每页显示 10 个任务
    offset = (page - 1) * page_size
    
    logger.info(f"📋 [v2.2] show_tasks_by_category: user_id={user_id}, category={category}, page={page}")
    
    # 获取该分类的任务
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 获取任务过期时间配置
    from task_expiry import get_task_expiry_hours
    expiry_hours = get_task_expiry_hours()
    
    # 查询该分类的活跃任务（直接在 SQL 中过滤已领取的任务，并过滤超过有效期的任务）
    # 任务超过有效期自动过期，不再允许领取
    # 同时统计每个任务被领取的人数
    if category == 'latest':
        # latest 分类显示所有类型的最新任务（包括 category 为 NULL 的任务）
        cur.execute("""
            SELECT dt.*, COALESCE(claim_counts.claim_count, 0) as claim_count
            FROM drama_tasks dt
            LEFT JOIN (
                SELECT task_id, COUNT(DISTINCT user_id) as claim_count
                FROM user_tasks
                GROUP BY task_id
            ) claim_counts ON dt.task_id = claim_counts.task_id
            WHERE dt.status = 'active' 
            AND dt.created_at > NOW() - INTERVAL '%s hours'
            AND dt.task_id NOT IN (
                SELECT task_id FROM user_tasks WHERE user_id = %s
            )
            ORDER BY dt.created_at DESC
            LIMIT %s OFFSET %s
        """, (expiry_hours, user_id, page_size, offset))
    else:
        # 其他分类只显示该分类的任务
        cur.execute("""
            SELECT dt.*, COALESCE(claim_counts.claim_count, 0) as claim_count
            FROM drama_tasks dt
            LEFT JOIN (
                SELECT task_id, COUNT(DISTINCT user_id) as claim_count
                FROM user_tasks
                GROUP BY task_id
            ) claim_counts ON dt.task_id = claim_counts.task_id
            WHERE dt.status = 'active' 
            AND dt.category = %s 
            AND dt.created_at > NOW() - INTERVAL '%s hours'
            AND dt.task_id NOT IN (
                SELECT task_id FROM user_tasks WHERE user_id = %s
            )
            ORDER BY dt.created_at DESC
            LIMIT %s OFFSET %s
        """, (category, expiry_hours, user_id, page_size, offset))
    
    available_tasks = cur.fetchall()
    
    cur.close()
    conn.close()
    
    logger.info(f"📊 分类 {category}: 可领取 {len(available_tasks)}")
    if len(available_tasks) == 0:
        logger.warning(f"⚠️ 分类 {category} 查询结果为空！user_id={user_id}")
    else:
        logger.info(f"✅ 分类 {category} 查询到任务: {[t['task_id'] for t in available_tasks[:3]]}")
    
    # 构建分类切换按钮
    categories = get_all_categories_for_bot(user_lang)
    category_buttons = []
    
    # 查询每个分类的可领取任务数量
    conn = get_db_connection()
    cur = conn.cursor()
    category_counts = {}
    
    for cat_code in categories.keys():
        if cat_code == 'latest':
            # latest 分类显示所有类型的任务数（过滤超过有效期的任务）
            cur.execute("""
                SELECT COUNT(*) as count FROM drama_tasks
                WHERE status = 'active' 
                AND created_at > NOW() - INTERVAL '%s hours'
                AND task_id NOT IN (
                    SELECT task_id FROM user_tasks WHERE user_id = %s
                )
            """, (expiry_hours, user_id))
        else:
            # 其他分类只统计该分类的任务（过滤超过有效期的任务）
            cur.execute("""
                SELECT COUNT(*) as count FROM drama_tasks
                WHERE status = 'active' 
                AND category = %s 
                AND created_at > NOW() - INTERVAL '%s hours'
                AND task_id NOT IN (
                    SELECT task_id FROM user_tasks WHERE user_id = %s
                )
            """, (cat_code, expiry_hours, user_id))
        
        result = cur.fetchone()
        category_counts[cat_code] = result['count'] if result else 0
    
    cur.close()
    conn.close()
    
    # 每行显示 3 个分类按钮
    row = []
    for cat_code, cat_name in list(categories.items())[:15]:  # 显示前 15 个分类（包括 latest + 13 个 API 分类 + 预留）
        # 当前分类用 ✓ 标记，并显示任务数量
        count = category_counts.get(cat_code, 0)
        if cat_code == category:
            button_text = f"✓ {cat_name} ({count})"
        else:
            button_text = f"{cat_name} ({count})"
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
            claim_count = task.get('claim_count', 0)
            # 只有有人领取时才显示领取人数，合并到同一行
            if claim_count > 0:
                if user_lang.startswith('zh'):
                    claim_info = f" | 👥{claim_count}"
                else:
                    claim_info = f" | 👥{claim_count}"
            else:
                claim_info = ""
            # 使用全局配置的奖励金额
            display_reward = get_display_reward(user_id)
            button_text = f"🎬 {title} ({task['duration']}s) - {display_reward} X2C{claim_info}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"claim_{task['task_id']}")])
        
        # 添加分页按钮
        pagination_row = []
        total_count = category_counts.get(category, 0)
        total_pages = (total_count + page_size - 1) // page_size  # 向上取整
        
        if page > 1:
            # 上一页按钮
            prev_text = "⬅️ 上一页" if user_lang.startswith('zh') else "⬅️ Previous"
            pagination_row.append(InlineKeyboardButton(prev_text, callback_data=f"page_{category}_{page-1}"))
        
        # 页码显示
        page_info = f"{page}/{total_pages}" if total_pages > 0 else "1/1"
        pagination_row.append(InlineKeyboardButton(f"📊 {page_info}", callback_data="noop"))
        
        if page < total_pages:
            # 下一页按钮
            next_text = "下一页 ➡️" if user_lang.startswith('zh') else "Next ➡️"
            pagination_row.append(InlineKeyboardButton(next_text, callback_data=f"page_{category}_{page+1}"))
        
        if pagination_row:
            keyboard.append(pagination_row)
        
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
    # 使用 categories 字典获取分类名称（从 X2C API 同步的分类）
    category_name = categories.get(category, category)
    if category == 'latest':
        category_name = '最新' if user_lang.startswith('zh') else 'Latest'
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
    
    # 显示该分类的任务（默认第 1 页）
    await show_tasks_by_category(update, context, category, page=1)


async def pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理分页回调
    """
    query = update.callback_query
    await query.answer()
    
    # 提取分类代码和页码
    # callback_data 格式: page_{category}_{page}
    parts = query.data.split('_')
    category = parts[1]
    page = int(parts[2])
    
    # 显示指定页的任务
    await show_tasks_by_category(update, context, category, page=page)
