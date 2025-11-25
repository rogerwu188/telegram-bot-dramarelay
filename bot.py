#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2C DramaRelayBot - 全球短剧分发节点 Telegram Bot
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# ============================================================
# 配置和日志
# ============================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 环境变量
BOT_TOKEN = os.getenv('BOT_TOKEN') or '8580007118:AAFmA9OlAT1D_XzUnKGL-0qU_FPK7G6uwyQ'
ADMIN_IDS_STR = os.getenv('ADMIN_IDS') or '5156570084'
DATABASE_URL = os.getenv('DATABASE_URL') or 'postgresql://postgres:UTKrUjgtzTzfCRQcXtohVuKalpdeCLns@postgres.railway.internal:5432/railway'

ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]

logger.info("✅ BOT_TOKEN loaded")
logger.info(f"✅ Admin IDs loaded: {ADMIN_IDS}")
logger.info("✅ DATABASE_URL loaded")

# 对话状态
(
    SUBMIT_PLATFORM,
    SUBMIT_LINK,
    BIND_WALLET,
    ADMIN_ADD_TASK_TITLE,
    ADMIN_ADD_TASK_DESC,
    ADMIN_ADD_TASK_VIDEO,
    ADMIN_ADD_TASK_REWARD,
) = range(7)

# ============================================================
# 数据库连接
# ============================================================

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_database():
    """初始化数据库表"""
    logger.info("Initializing database...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 用户表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255),
            first_name VARCHAR(255),
            language VARCHAR(10) DEFAULT 'zh',
            wallet_address VARCHAR(42),
            total_node_power INTEGER DEFAULT 0,
            completed_tasks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 短剧任务表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drama_tasks (
            task_id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            video_file_id TEXT,
            thumbnail_url TEXT,
            duration INTEGER DEFAULT 15,
            node_power_reward INTEGER DEFAULT 10,
            platform_requirements TEXT DEFAULT 'TikTok,YouTube,Instagram',
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 用户任务关联表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_tasks (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            task_id INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'in_progress',
            platform VARCHAR(50),
            submission_link TEXT,
            submitted_at TIMESTAMP,
            verified_at TIMESTAMP,
            node_power_earned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id)
        )
    """)
    
    # 空投快照表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS airdrop_snapshots (
            id SERIAL PRIMARY KEY,
            round_number INTEGER NOT NULL,
            user_id BIGINT NOT NULL,
            node_power INTEGER NOT NULL,
            rank INTEGER,
            estimated_airdrop DECIMAL(18, 6),
            snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info("✅ Database tables initialized successfully")

# ============================================================
# 文案字典
# ============================================================

MESSAGES = {
    'zh': {
        'welcome': """🎬 欢迎使用 DramaRelayBot！

这是 X2C 全球短剧分发节点的任务入口。
你可以领取短剧素材 → 上传到 TikTok / YouTube / IG 等平台 → 
回到这里提交链接 → 获得 Node Power 算力点数，参与 X2C 的奖励池。

👉 点击菜单领取短剧任务
👉 上传片段到你喜欢的平台
👉 提交链接完成节点贡献

一起构建全球短剧分发网络。""",
        'menu_get_tasks': '🎬 领取短剧任务',
        'menu_submit_link': '📤 提交链接',
        'menu_my_power': '📊 我的算力',
        'menu_ranking': '🏆 排行榜',
        'menu_airdrop': '🎁 空投状态',
        'menu_bind_wallet': '💼 绑定钱包',
        'menu_tutorial': 'ℹ️ 使用教程',
        'menu_language': '🌐 切换语言',
        'no_tasks_available': '暂无可用任务，请稍后再试。',
        'task_details': """📋 任务详情

🎬 标题：{title}
📝 描述：{description}
⏱ 时长：{duration}秒
💰 奖励：{reward} Node Power
📱 平台：{platforms}

⬇️ 点击下方按钮领取任务，系统将自动下载视频到聊天窗口。""",
        'task_claimed': '✅ 任务领取成功！\n\n请下载视频，上传到你选择的平台，然后回来提交链接。',
        'task_already_claimed': '⚠️ 你已经领取过这个任务了。',
        'select_task_to_submit': '请选择要提交的任务：',
        'no_tasks_in_progress': '你当前没有进行中的任务。\n\n请先领取任务！',
        'select_platform': '请选择你上传的平台：',
        'enter_link': '请输入你上传的链接：',
        'link_submitted': '✅ 链接提交成功！\n\n你获得了 {reward} Node Power！\n\n总算力：{total_power}',
        'invalid_link': '❌ 链接格式不正确，请重新输入。',
        'my_power': """📊 我的算力统计

💰 总 Node Power：{total_power}
✅ 已完成任务：{completed_tasks}
🔄 进行中任务：{in_progress_tasks}
📈 本周排名：#{rank}
🎁 预计空投：{estimated_airdrop} X2C""",
        'ranking': """🏆 全球排行榜

{ranking_list}

你的排名：#{your_rank}
你的算力：{your_power} Node Power""",
        'airdrop_status': """🎁 空投状态

📅 当前轮次：第 {round} 轮
✅ 空投资格：{eligible}
💰 预计空投：{estimated} X2C
⏰ 下次快照：{next_snapshot}

最低要求：100 Node Power""",
        'bind_wallet_prompt': '请输入你的 EVM 钱包地址（以 0x 开头）：',
        'wallet_bound': '✅ 钱包绑定成功！\n\n地址：{address}',
        'invalid_wallet': '❌ 钱包地址格式不正确，请重新输入。',
        'tutorial': """ℹ️ 使用教程

1️⃣ 领取任务
   点击"领取短剧任务"，选择你喜欢的短剧

2️⃣ 下载视频
   点击"确认领取"后，下载任务视频

3️⃣ 上传到平台
   将视频上传到 TikTok、YouTube、Instagram 等平台

4️⃣ 提交链接
   点击"提交链接"，选择任务，输入平台和链接

5️⃣ 获得奖励
   提交成功后立即获得 Node Power

6️⃣ 参与空投
   累积 100+ Node Power 即可参与每月空投

💡 小贴士：
- 每个任务只能提交一次
- 链接必须真实有效
- 多平台分发可获得更多奖励""",
        'back_to_menu': '« 返回主菜单',
        'cancel': '取消',
    },
    'en': {
        'welcome': """🎬 Welcome to DramaRelayBot!

This is the task portal for X2C Global Drama Distribution Network.
Get drama clips → Upload to TikTok / YouTube / IG → 
Submit links here → Earn Node Power points and join X2C reward pool.

👉 Get drama tasks from menu
👉 Upload clips to your favorite platforms
👉 Submit links to complete node contribution

Let's build the global drama distribution network together.""",
        'menu_get_tasks': '🎬 Get Drama Tasks',
        'menu_submit_link': '📤 Submit Link',
        'menu_my_power': '📊 My Node Power',
        'menu_ranking': '🏆 Ranking',
        'menu_airdrop': '🎁 Airdrop Status',
        'menu_bind_wallet': '💼 Bind Wallet',
        'menu_tutorial': 'ℹ️ How It Works',
        'menu_language': '🌐 Switch Language',
        'no_tasks_available': 'No tasks available at the moment. Please try again later.',
        'task_details': """📋 Task Details

🎬 Title: {title}
📝 Description: {description}
⏱ Duration: {duration}s
💰 Reward: {reward} Node Power
📱 Platforms: {platforms}

⬇️ Click the button below to claim the task. The video will be automatically downloaded to the chat.""",
        'task_claimed': '✅ Task claimed successfully!\n\nPlease download the video, upload it to your chosen platform, and come back to submit the link.',
        'task_already_claimed': '⚠️ You have already claimed this task.',
        'select_task_to_submit': 'Please select the task to submit:',
        'no_tasks_in_progress': 'You have no tasks in progress.\n\nPlease claim a task first!',
        'select_platform': 'Please select the platform you uploaded to:',
        'enter_link': 'Please enter your upload link:',
        'link_submitted': '✅ Link submitted successfully!\n\nYou earned {reward} Node Power!\n\nTotal Power: {total_power}',
        'invalid_link': '❌ Invalid link format. Please try again.',
        'my_power': """📊 My Node Power Stats

💰 Total Node Power: {total_power}
✅ Completed Tasks: {completed_tasks}
🔄 In Progress: {in_progress_tasks}
📈 This Week Rank: #{rank}
🎁 Estimated Airdrop: {estimated_airdrop} X2C""",
        'ranking': """🏆 Global Ranking

{ranking_list}

Your Rank: #{your_rank}
Your Power: {your_power} Node Power""",
        'airdrop_status': """🎁 Airdrop Status

📅 Current Round: Round {round}
✅ Eligibility: {eligible}
💰 Estimated Airdrop: {estimated} X2C
⏰ Next Snapshot: {next_snapshot}

Minimum Requirement: 100 Node Power""",
        'bind_wallet_prompt': 'Please enter your EVM wallet address (starting with 0x):',
        'wallet_bound': '✅ Wallet bound successfully!\n\nAddress: {address}',
        'invalid_wallet': '❌ Invalid wallet address format. Please try again.',
        'tutorial': """ℹ️ How It Works

1️⃣ Get Tasks
   Click "Get Drama Tasks" and choose your favorite drama

2️⃣ Download Video
   Click "Claim Task" and download the task video

3️⃣ Upload to Platform
   Upload the video to TikTok, YouTube, Instagram, etc.

4️⃣ Submit Link
   Click "Submit Link", select task, enter platform and link

5️⃣ Get Rewards
   Earn Node Power immediately after submission

6️⃣ Join Airdrop
   Accumulate 100+ Node Power to join monthly airdrops

💡 Tips:
- Each task can only be submitted once
- Links must be valid and real
- Multi-platform distribution earns more rewards""",
        'back_to_menu': '« Back to Menu',
        'cancel': 'Cancel',
    }
}

def get_message(user_lang: str, key: str, **kwargs) -> str:
    """获取本地化消息"""
    lang = user_lang if user_lang in MESSAGES else 'zh'
    message = MESSAGES[lang].get(key, MESSAGES['zh'].get(key, ''))
    return message.format(**kwargs) if kwargs else message

# ============================================================
# 数据库操作函数
# ============================================================

def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> dict:
    """获取或创建用户"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cur.fetchone()
    
    if not user:
        cur.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (%s, %s, %s)
            RETURNING *
        """, (user_id, username, first_name))
        user = cur.fetchone()
        conn.commit()
    
    cur.close()
    conn.close()
    return dict(user)

def get_user_language(user_id: int) -> str:
    """获取用户语言"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT language FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return result['language'] if result else 'zh'

def set_user_language(user_id: int, language: str):
    """设置用户语言"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE users SET language = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (language, user_id))
    
    conn.commit()
    cur.close()
    conn.close()

def get_active_tasks() -> List[dict]:
    """获取所有活跃任务"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT * FROM drama_tasks
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)
    tasks = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(task) for task in tasks]

def get_task_by_id(task_id: int) -> Optional[dict]:
    """根据ID获取任务"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM drama_tasks WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return dict(task) if task else None

def claim_task(user_id: int, task_id: int) -> bool:
    """领取任务"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 检查是否已领取
    cur.execute("""
        SELECT * FROM user_tasks
        WHERE user_id = %s AND task_id = %s
    """, (user_id, task_id))
    
    if cur.fetchone():
        cur.close()
        conn.close()
        return False
    
    # 创建任务记录
    cur.execute("""
        INSERT INTO user_tasks (user_id, task_id, status)
        VALUES (%s, %s, 'in_progress')
    """, (user_id, task_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return True

def get_user_in_progress_tasks(user_id: int) -> List[dict]:
    """获取用户进行中的任务"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT ut.*, dt.title, dt.node_power_reward
        FROM user_tasks ut
        JOIN drama_tasks dt ON ut.task_id = dt.task_id
        WHERE ut.user_id = %s AND ut.status = 'in_progress'
        ORDER BY ut.created_at DESC
    """, (user_id,))
    
    tasks = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(task) for task in tasks]

def submit_task_link(user_id: int, task_id: int, platform: str, link: str) -> int:
    """提交任务链接"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 获取任务奖励
    cur.execute("SELECT node_power_reward FROM drama_tasks WHERE task_id = %s", (task_id,))
    task = cur.fetchone()
    reward = task['node_power_reward'] if task else 10
    
    # 更新任务状态
    cur.execute("""
        UPDATE user_tasks
        SET status = 'submitted', platform = %s, submission_link = %s,
            submitted_at = CURRENT_TIMESTAMP, node_power_earned = %s
        WHERE user_id = %s AND task_id = %s
    """, (platform, link, reward, user_id, task_id))
    
    # 更新用户算力
    cur.execute("""
        UPDATE users
        SET total_node_power = total_node_power + %s,
            completed_tasks = completed_tasks + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (reward, user_id))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return reward

def get_user_stats(user_id: int) -> dict:
    """获取用户统计"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 基本统计
    cur.execute("""
        SELECT total_node_power, completed_tasks
        FROM users
        WHERE user_id = %s
    """, (user_id,))
    user = cur.fetchone()
    
    # 进行中任务数
    cur.execute("""
        SELECT COUNT(*) as count
        FROM user_tasks
        WHERE user_id = %s AND status = 'in_progress'
    """, (user_id,))
    in_progress = cur.fetchone()
    
    # 排名
    cur.execute("""
        SELECT COUNT(*) + 1 as rank
        FROM users
        WHERE total_node_power > (SELECT total_node_power FROM users WHERE user_id = %s)
    """, (user_id,))
    rank = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return {
        'total_power': user['total_node_power'] if user else 0,
        'completed_tasks': user['completed_tasks'] if user else 0,
        'in_progress_tasks': in_progress['count'] if in_progress else 0,
        'rank': rank['rank'] if rank else 0,
        'estimated_airdrop': 0  # TODO: 实现空投计算
    }

def get_ranking(limit: int = 100) -> List[dict]:
    """获取排行榜"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT user_id, username, first_name, total_node_power,
               ROW_NUMBER() OVER (ORDER BY total_node_power DESC) as rank
        FROM users
        WHERE total_node_power > 0
        ORDER BY total_node_power DESC
        LIMIT %s
    """, (limit,))
    
    ranking = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return [dict(r) for r in ranking]

def bind_wallet(user_id: int, wallet_address: str):
    """绑定钱包"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        UPDATE users
        SET wallet_address = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (wallet_address, user_id))
    
    conn.commit()
    cur.close()
    conn.close()

# ============================================================
# 工具函数
# ============================================================

def validate_link(platform: str, link: str) -> bool:
    """验证链接格式"""
    patterns = {
        'TikTok': r'https?://(www\.)?tiktok\.com/@[\w.-]+/video/\d+',
        'YouTube': r'https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+',
        'Instagram': r'https?://(www\.)?instagram\.com/(p|reel)/[\w-]+',
        'Facebook': r'https?://(www\.)?facebook\.com/.*',
        'Twitter': r'https?://(www\.)?(twitter\.com|x\.com)/.*',
    }
    
    if platform in patterns:
        return bool(re.match(patterns[platform], link))
    
    # 其他平台，只检查是否是有效URL
    return bool(re.match(r'https?://.*', link))

def validate_wallet_address(address: str) -> bool:
    """验证钱包地址"""
    return bool(re.match(r'^0x[a-fA-F0-9]{40}$', address))

def get_main_menu_keyboard(user_lang: str) -> InlineKeyboardMarkup:
    """获取主菜单键盘"""
    keyboard = [
        [
            InlineKeyboardButton(get_message(user_lang, 'menu_get_tasks'), callback_data='get_tasks'),
            InlineKeyboardButton(get_message(user_lang, 'menu_submit_link'), callback_data='submit_link'),
        ],
        [
            InlineKeyboardButton(get_message(user_lang, 'menu_my_power'), callback_data='my_power'),
            InlineKeyboardButton(get_message(user_lang, 'menu_ranking'), callback_data='ranking'),
        ],
        [
            InlineKeyboardButton(get_message(user_lang, 'menu_airdrop'), callback_data='airdrop'),
            InlineKeyboardButton(get_message(user_lang, 'menu_bind_wallet'), callback_data='bind_wallet'),
        ],
        [
            InlineKeyboardButton(get_message(user_lang, 'menu_tutorial'), callback_data='tutorial'),
            InlineKeyboardButton(get_message(user_lang, 'menu_language'), callback_data='language'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# 命令处理函数
# ============================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    user_lang = get_user_language(user.id)
    
    welcome_message = get_message(user_lang, 'welcome')
    keyboard = get_main_menu_keyboard(user_lang)
    
    await update.message.reply_text(welcome_message, reply_markup=keyboard)

async def get_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理获取任务列表"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    tasks = get_active_tasks()
    
    if not tasks:
        await query.edit_message_text(
            get_message(user_lang, 'no_tasks_available'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
            ]])
        )
        return
    
    # 显示任务列表
    keyboard = []
    for task in tasks:
        button_text = f"🎬 {task['title']} ({task['duration']}s) - {task['node_power_reward']} NP"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"claim_{task['task_id']}")])
    
    keyboard.append([InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')])
    
    await query.edit_message_text(
        "📋 选择你想要领取的任务：" if user_lang == 'zh' else "📋 Select a task to claim:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def task_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理任务详情"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    task_id = int(query.data.split('_')[1])
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text("任务不存在" if user_lang == 'zh' else "Task not found")
        return
    
    # 显示任务详情
    message = get_message(user_lang, 'task_details',
        title=task['title'],
        description=task['description'] or 'N/A',
        duration=task['duration'],
        reward=task['node_power_reward'],
        platforms=task['platform_requirements']
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ 确认领取" if user_lang == 'zh' else "✅ Claim Task", callback_data=f"claim_{task_id}")],
        [InlineKeyboardButton("« 返回任务列表" if user_lang == 'zh' else "« Back to Tasks", callback_data='get_tasks')]
    ]
    
    # 如果有视频文件，发送视频
    if task['video_file_id']:
        await query.message.reply_video(
            video=task['video_file_id'],
            caption=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await query.delete_message()
    else:
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

async def claim_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理领取任务"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    task_id = int(query.data.split('_')[1])
    
    # 获取任务详情
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text(
            "❌ 任务不存在" if user_lang == 'zh' else "❌ Task not found",
            reply_markup=get_main_menu_keyboard(user_lang)
        )
        return
    
    if claim_task(user_id, task_id):
        message = get_message(user_lang, 'task_claimed')
        
        # 先发送确认消息
        keyboard = get_main_menu_keyboard(user_lang)
        await query.edit_message_text(message, reply_markup=keyboard)
        
        # 如果任务有视频链接，下载并发送视频
        video_url = task.get('video_file_id')
        if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
            try:
                # 发送下载提示
                download_msg = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="⏳ 正在下载视频..." if user_lang == 'zh' else "⏳ Downloading video..."
                )
                
                # 下载视频
                import requests
                import tempfile
                import os
                
                response = requests.get(video_url, stream=True, timeout=60)
                response.raise_for_status()
                
                # 保存到临时文件
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            tmp_file.write(chunk)
                    tmp_file_path = tmp_file.name
                
                # 删除下载提示
                await download_msg.delete()
                
                # 发送视频
                with open(tmp_file_path, 'rb') as video_file:
                    caption = f"🎬 {task['title']}\n\n" + \
                              (f"💰 完成任务可获得 {task['node_power_reward']} Node Power" if user_lang == 'zh' \
                               else f"💰 Complete this task to earn {task['node_power_reward']} Node Power")
                    
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=video_file,
                        caption=caption,
                        supports_streaming=True
                    )
                
                # 删除临时文件
                os.unlink(tmp_file_path)
                
            except Exception as e:
                logger.error(f"Error downloading video: {e}")
                error_msg = "❌ 视频下载失败，请稍后重试" if user_lang == 'zh' else "❌ Failed to download video, please try again later"
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"{error_msg}\n\n📎 视频链接: {video_url}"
                )
    else:
        message = get_message(user_lang, 'task_already_claimed')
        keyboard = get_main_menu_keyboard(user_lang)
        await query.edit_message_text(message, reply_markup=keyboard)

async def submit_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理提交链接"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    tasks = get_user_in_progress_tasks(user_id)
    
    if not tasks:
        await query.edit_message_text(
            get_message(user_lang, 'no_tasks_in_progress'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
            ]])
        )
        return
    
    # 显示进行中的任务列表
    keyboard = []
    for task in tasks:
        button_text = f"📤 {task['title']} ({task['node_power_reward']} NP)"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"submit_task_{task['task_id']}")])
    
    keyboard.append([InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')])
    
    await query.edit_message_text(
        get_message(user_lang, 'select_task_to_submit'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def submit_task_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理选择要提交的任务"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    task_id = int(query.data.split('_')[2])
    context.user_data['submit_task_id'] = task_id
    
    # 显示平台选择
    keyboard = [
        [InlineKeyboardButton("TikTok", callback_data="platform_TikTok")],
        [InlineKeyboardButton("YouTube", callback_data="platform_YouTube")],
        [InlineKeyboardButton("Instagram", callback_data="platform_Instagram")],
        [InlineKeyboardButton("Facebook", callback_data="platform_Facebook")],
        [InlineKeyboardButton("Twitter", callback_data="platform_Twitter")],
        [InlineKeyboardButton("其他平台 / Other" if user_lang == 'zh' else "Other Platform", callback_data="platform_Other")],
        [InlineKeyboardButton(get_message(user_lang, 'cancel'), callback_data='submit_link')]
    ]
    
    await query.edit_message_text(
        get_message(user_lang, 'select_platform'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SUBMIT_PLATFORM

async def platform_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理平台选择"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    platform = query.data.split('_')[1]
    context.user_data['submit_platform'] = platform
    
    await query.edit_message_text(get_message(user_lang, 'enter_link'))
    
    return SUBMIT_LINK

async def link_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理链接输入"""
    user_id = update.effective_user.id
    user_lang = get_user_language(user_id)
    
    link = update.message.text.strip()
    task_id = context.user_data.get('submit_task_id')
    platform = context.user_data.get('submit_platform')
    
    if not validate_link(platform, link):
        await update.message.reply_text(get_message(user_lang, 'invalid_link'))
        return SUBMIT_LINK
    
    # 提交链接
    reward = submit_task_link(user_id, task_id, platform, link)
    stats = get_user_stats(user_id)
    
    message = get_message(user_lang, 'link_submitted',
        reward=reward,
        total_power=stats['total_power']
    )
    
    keyboard = get_main_menu_keyboard(user_lang)
    await update.message.reply_text(message, reply_markup=keyboard)
    
    return ConversationHandler.END

async def my_power_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理我的算力"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    stats = get_user_stats(user_id)
    
    message = get_message(user_lang, 'my_power',
        total_power=stats['total_power'],
        completed_tasks=stats['completed_tasks'],
        in_progress_tasks=stats['in_progress_tasks'],
        rank=stats['rank'],
        estimated_airdrop=stats['estimated_airdrop']
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await query.edit_message_text(message, reply_markup=keyboard)

async def ranking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理排行榜"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    ranking = get_ranking(20)
    stats = get_user_stats(user_id)
    
    ranking_list = []
    for r in ranking:
        name = r['first_name'] or r['username'] or f"User {r['user_id']}"
        ranking_list.append(f"{r['rank']}. {name} - {r['total_node_power']} NP")
    
    message = get_message(user_lang, 'ranking',
        ranking_list='\n'.join(ranking_list),
        your_rank=stats['rank'],
        your_power=stats['total_power']
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await query.edit_message_text(message, reply_markup=keyboard)

async def airdrop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理空投状态"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    stats = get_user_stats(user_id)
    eligible = "✅ 是" if stats['total_power'] >= 100 else "❌ 否（需要 100+ NP）"
    if user_lang == 'en':
        eligible = "✅ Yes" if stats['total_power'] >= 100 else "❌ No (Need 100+ NP)"
    
    message = get_message(user_lang, 'airdrop_status',
        round=1,
        eligible=eligible,
        estimated=stats['estimated_airdrop'],
        next_snapshot="2025-12-01" if user_lang == 'zh' else "Dec 1, 2025"
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await query.edit_message_text(message, reply_markup=keyboard)

async def bind_wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理绑定钱包"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    await query.edit_message_text(get_message(user_lang, 'bind_wallet_prompt'))
    
    return BIND_WALLET

async def wallet_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理钱包地址输入"""
    user_id = update.effective_user.id
    user_lang = get_user_language(user_id)
    
    address = update.message.text.strip()
    
    if not validate_wallet_address(address):
        await update.message.reply_text(get_message(user_lang, 'invalid_wallet'))
        return BIND_WALLET
    
    bind_wallet(user_id, address)
    
    message = get_message(user_lang, 'wallet_bound', address=address)
    keyboard = get_main_menu_keyboard(user_lang)
    
    await update.message.reply_text(message, reply_markup=keyboard)
    
    return ConversationHandler.END

async def tutorial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理使用教程"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    message = get_message(user_lang, 'tutorial')
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await query.edit_message_text(message, reply_markup=keyboard)

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理语言切换"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    keyboard = [
        [InlineKeyboardButton("中文", callback_data="set_lang_zh")],
        [InlineKeyboardButton("English", callback_data="set_lang_en")],
        [InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')]
    ]
    
    await query.edit_message_text(
        "选择语言 / Select Language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置语言"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    new_lang = query.data.split('_')[2]
    
    set_user_language(user_id, new_lang)
    
    message = "✅ 语言已切换为中文" if new_lang == 'zh' else "✅ Language switched to English"
    keyboard = get_main_menu_keyboard(new_lang)
    
    await query.edit_message_text(message, reply_markup=keyboard)

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回主菜单"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    welcome_message = get_message(user_lang, 'welcome')
    keyboard = get_main_menu_keyboard(user_lang)
    
    await query.edit_message_text(welcome_message, reply_markup=keyboard)

# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    logger.info("🚀 X2C DramaRelayBot Starting...")
    
    # 初始化数据库
    init_database()
    
    # 创建应用
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 命令处理器
    application.add_handler(CommandHandler("start", start_command))
    
    # 回调查询处理器
    application.add_handler(CallbackQueryHandler(get_tasks_callback, pattern='^get_tasks$'))
    application.add_handler(CallbackQueryHandler(task_detail_callback, pattern='^task_\\d+$'))
    application.add_handler(CallbackQueryHandler(claim_task_callback, pattern='^claim_\\d+$'))
    application.add_handler(CallbackQueryHandler(submit_link_callback, pattern='^submit_link$'))
    application.add_handler(CallbackQueryHandler(submit_task_select_callback, pattern='^submit_task_\\d+$'))
    application.add_handler(CallbackQueryHandler(my_power_callback, pattern='^my_power$'))
    application.add_handler(CallbackQueryHandler(ranking_callback, pattern='^ranking$'))
    application.add_handler(CallbackQueryHandler(airdrop_callback, pattern='^airdrop$'))
    application.add_handler(CallbackQueryHandler(tutorial_callback, pattern='^tutorial$'))
    application.add_handler(CallbackQueryHandler(language_callback, pattern='^language$'))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern='^set_lang_'))
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$'))
    
    # 对话处理器 - 提交链接
    submit_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(platform_select_callback, pattern='^platform_')],
        states={
            SUBMIT_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, link_input_handler)],
        },
        fallbacks=[CallbackQueryHandler(submit_link_callback, pattern='^submit_link$')],
    )
    application.add_handler(submit_conv_handler)
    
    # 对话处理器 - 绑定钱包
    wallet_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(bind_wallet_callback, pattern='^bind_wallet$')],
        states={
            BIND_WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_input_handler)],
        },
        fallbacks=[CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
    )
    application.add_handler(wallet_conv_handler)
    
    # 检查是否有 WEBHOOK_URL 环境变量
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if webhook_url:
        # Webhook 模式
        logger.info(f"🌐 Using Webhook mode: {webhook_url}")
        
        # 设置 Webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv('PORT', 8080)),
            url_path=BOT_TOKEN,
            webhook_url=f"{webhook_url}/{BOT_TOKEN}"
        )
    else:
        # Polling 模式（本地开发）
        logger.info("🔄 Using Polling mode (local development)")
        logger.info("✅ Bot is running! Press Ctrl+C to stop.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
