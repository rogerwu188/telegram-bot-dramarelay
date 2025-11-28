#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2C DramaRelayBot - 全球短剧分发节点 Telegram Bot
"""

import os
import re
import logging
import asyncio
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
from auto_migrate import auto_migrate
from link_verifier import LinkVerifier

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

# 初始化链接验证器
link_verifier = LinkVerifier()

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
        'welcome': """🎬 X2C 流量节点 (Traffic Node) 已连接
欢迎回来，节点 @{username}。
这里是全球首个 Post-to-Earn 去中心化短剧分发网络。

📊 节点面板 (Dashboard):
• 算力状态： 🔴 Idle (空闲)
• 全网币价： $0.002 / x2c 📈
• 挖矿难度： 🔥 简单 (TikTok/Reels/Shorts)

⛏️ 如何产出 x2c？
1️⃣ 获取原料： 领取爆款短剧切片
2️⃣ 贡献算力： 上传至社媒平台 (0粉可用)
3️⃣ 提交凭证： 回填链接，流量越大 = x2c 越多！

💰 预期收益：
单条视频爆款可挖 10,000+ x2c

👇 点击下方指令，激活节点开始挖矿：""",
        'menu_get_tasks': '⛏️ 领取挖矿原料',
        'menu_submit_link': '🔗 提交工作凭证',
        'menu_my_power': '📊 我的算力',
        'menu_ranking': '⚡ 全网算力榜',
        'menu_airdrop': '👥 邀请好友 (+10%)',
        'menu_bind_wallet': '📤 钱包提现',
        'menu_tutorial': '📚 节点挖矿手册',
        'menu_language': '🌐 语言 / Language',
        'no_tasks_available': '暂无可用任务，请稍后再试。',
        'task_details': """📋 任务详情

🎬 标题：{title}
📝 描述：{description}
⏱ 时长：{duration}秒
💰 奖励：{reward} Node Power
📱 平台：{platforms}

⬇️ 点击下方按钮领取任务，系统将自动下载视频到聊天窗口。""",
        'task_claimed': '✅ 任务领取成功！\n\n正在下载视频，下载完成后请上传到你选择的平台，然后回来提交链接。',
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
        'bind_wallet_prompt': '请输入你的 SOL 钱包地址：',
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
        'welcome': """🎬 X2C Traffic Node Connected
Welcome back, Node @{username}.
This is the world's first Post-to-Earn decentralized drama distribution network.

📊 Node Dashboard:
• Hashrate Status: 🔴 Idle
• Global Token Price: $0.002 / x2c 📈
• Mining Difficulty: 🔥 Easy (TikTok/Reels/Shorts)

⛏️ How to Mine x2c?
1️⃣ Get Materials: Claim viral drama clips
2️⃣ Contribute Hashrate: Upload to social media (0 followers OK)
3️⃣ Submit Proof: Post link, more traffic = more x2c!

💰 Expected Earnings:
Viral videos can mine 10,000+ x2c

👇 Click commands below to activate node and start mining:""",
        'menu_get_tasks': '⛏️ Get Mining Materials',
        'menu_submit_link': '🔗 Submit Work Proof',
        'menu_my_power': '📊 My Hashrate',
        'menu_ranking': '⚡ Global Hashrate Board',
        'menu_airdrop': '👥 Invite Friends (+10%)',
        'menu_bind_wallet': '📤 Wallet Withdrawal',
        'menu_tutorial': '📚 Node Mining Guide',
        'menu_language': '🌐 Language / 语言',
        'no_tasks_available': 'No tasks available at the moment. Please try again later.',
        'task_details': """📋 Task Details

🎬 Title: {title}
📝 Description: {description}
⏱ Duration: {duration}s
💰 Reward: {reward} Node Power
📱 Platforms: {platforms}

⬇️ Click the button below to claim the task. The video will be automatically downloaded to the chat.""",
        'task_claimed': '✅ Task claimed successfully!\n\nDownloading video... After download completes, please upload it to your chosen platform, and come back to submit the link.',
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
        """, (user_id, username, first_name))
        conn.commit()
        # 重新查询用户
        cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cur.fetchone()
    
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
        WHERE ut.user_id = %s 
          AND ut.status = 'in_progress'
          AND dt.status = 'active'
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

def detect_platform(link: str) -> Optional[str]:
    """自动识别平台"""
    patterns = {
        'TikTok': r'https?://(www\.)?tiktok\.com',
        'YouTube': r'https?://(www\.)?(youtube\.com|youtu\.be)',
        'Instagram': r'https?://(www\.)?instagram\.com',
        'Facebook': r'https?://(www\.)?facebook\.com',
        'Twitter': r'https?://(www\.)?(twitter\.com|x\.com)',
    }
    
    for platform, pattern in patterns.items():
        if re.match(pattern, link):
            return platform
    
    return 'Other'

def validate_link(platform: str, link: str) -> bool:
    """验证链接格式"""
    patterns = {
        'TikTok': r'https?://(www\.)?tiktok\.com/@[\w.-]+/video/\d+',
        'YouTube': r'https?://(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)[\w-]+',
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
    
    # 格式化欢迎消息，替换用户名
    welcome_message = get_message(user_lang, 'welcome').format(
        username=user.username or user.first_name or f"User{user.id}"
    )
    keyboard = get_main_menu_keyboard(user_lang)
    
    await update.message.reply_text(welcome_message, reply_markup=keyboard)

async def get_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理领取任务按钮"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    logger.info(f"📝 get_tasks_callback triggered! user_id={user_id}")
    
    tasks = get_active_tasks()
    
    if not tasks:
        await query.edit_message_text(
            get_message(user_lang, 'no_tasks_available'),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
            ]])
        )
        return
    
    # 获取用户已领取的任务ID列表
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT task_id FROM user_tasks
        WHERE user_id = %s
    """, (user_id,))
    claimed_task_ids = {row['task_id'] for row in cur.fetchall()}
    cur.close()
    conn.close()
    logger.info(f"📋 用户 {user_id} 已领取的任务ID: {claimed_task_ids}")
    
    # 过滤掉已领取的任务
    available_tasks = [task for task in tasks if task['task_id'] not in claimed_task_ids]
    logger.info(f"🎯 可领取的任务数量: {len(available_tasks)}/{len(tasks)}")
    
    if not available_tasks:
        await query.edit_message_text(
            "✅ 你已经领取了所有可用的任务！" if user_lang == 'zh' else "✅ You have claimed all available tasks!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
            ]])
        )
        return
    
    # 显示任务列表
    keyboard = []
    for task in available_tasks:
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
    
    logger.info(f"🔔 claim_task_callback triggered! user_id={user_id}, task_id={task_id}, callback_data={query.data}")
    
    # 获取任务详情
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text(
            "❌ 任务不存在" if user_lang == 'zh' else "❌ Task not found",
            reply_markup=get_main_menu_keyboard(user_lang)
        )
        return
    
    claim_result = claim_task(user_id, task_id)
    logger.info(f"📊 claim_task result: {claim_result}")
    
    if claim_result:
        logger.info(f"✅ Task claimed successfully")
        
        # 删除任务详情消息
        try:
            await query.delete_message()
        except Exception as e:
            logger.warning(f"⚠️ Failed to delete task details message: {e}")
        
        # 如果任务有视频链接，下载并发送视频
        video_url = task.get('video_file_id')
        logger.info(f"🎥 video_url from task: {video_url}")
        if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
            logger.info(f"✅ Starting video download from: {video_url}")
            try:
                # 不显示下载提示,直接下载
                
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
                
                logger.info(f"✅ Video downloaded successfully, file size: {os.path.getsize(tmp_file_path)} bytes")
                
                # 发送视频
                with open(tmp_file_path, 'rb') as video_file:
                    # 构建多行模版格式
                    logger.info(f"📝 Task data for caption: title={task.get('title')}, description={task.get('description')}, keywords_template={task.get('keywords_template')}")
                    
                    # 确保每个字段都有值，并且格式正确
                    title = task.get('title', '')
                    description = task.get('description', '')
                    keywords_raw = task.get('keywords_template', '')
                    reward = task.get('node_power_reward', 0)
                    
                    # 清理 keywords_template：完全删除包含"视频链接："的行
                    keywords_lines = keywords_raw.split('\n')
                    cleaned_keywords = []
                    for line in keywords_lines:
                        # 跳过包含"视频链接："的行
                        if '视频链接：' not in line and line.strip():
                            # 如果行中包含"keywords_template="，提取后面的内容
                            if 'keywords_template=' in line:
                                cleaned_keywords.append(line.split('keywords_template=')[1])
                            # 如果行中包含"上传关键词描述："，提取后面的内容
                            elif '上传关键词描述：' in line:
                                cleaned_keywords.append(line.split('上传关键词描述：')[1])
                            else:
                                cleaned_keywords.append(line)
                    keywords = '\n'.join(cleaned_keywords) if cleaned_keywords else keywords_raw
                    
                    # 生成合法的文件名（去掉特殊字符）
                    safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '·', '《', '》')).strip()
                    if not safe_filename:
                        safe_filename = f"video_{task_id}"
                    filename = f"{safe_filename}.mp4"
                    
                    video_msg = await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=video_file,
                        filename=filename,
                        supports_streaming=True
                    )
                    
                    # 保存视频消息 ID 以便后续删除
                    if 'task_video_messages' not in context.user_data:
                        context.user_data['task_video_messages'] = {}
                    context.user_data['task_video_messages'][task_id] = video_msg.message_id
                    logger.info(f"📹 保存视频消息 ID: task_id={task_id}, message_id={video_msg.message_id}")
                
                # 删除临时文件
                os.unlink(tmp_file_path)
                
                # 发送最终提示消息（新消息，在视频之后）
                # 格式化关键词为 #tag 格式
                keywords_list = [kw.strip() for kw in keywords.replace(',', ' ').split() if kw.strip()]
                hashtags = ' '.join([f'#{kw}' for kw in keywords_list[:11]])  # 限制11个标签
                
                # 提取剧情关键词（从 keywords_list 中取第一个）
                plot_keyword = keywords_list[0] if keywords_list else "剧情关键词"
                
                # 提取剧名（从 title 中提取《》中的内容）
                import re
                drama_name_match = re.search(r'《(.+?)》', title)
                drama_name = drama_name_match.group(1) if drama_name_match else "剧名"
                drama_name_with_brackets = f"《{drama_name}》"  # 带书名号的剧名
                
                if user_lang == 'zh':
                    final_msg = f"""📥 下载已完成，请按以下提示上传：

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

完成以上任务，并在本机器人提交你发布后的视频链接  
即可获得 🎉 {reward} Node Power"""
                    
                    # 创建 inline keyboard 按钮
                    keyboard = [
                        [InlineKeyboardButton("📎 提交链接", callback_data=f"submit_link_{task_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    final_msg = f"""📤 Please follow the instructions below to upload the video and complete the task:

━━━━━━━━━━━━━━━━━━
🎬【YouTube Upload Content】

▶ Video Title (copy directly):
{title}

▶ Video Description (paste in YouTube description):
{description}

(YouTube does not require tags, leave blank)

━━━━━━━━━━━━━━━━━━
🎬【TikTok Upload Content】

▶ TikTok Description (copy completely):
{description}

▶ TikTok Hashtags (paste below description):
{hashtags}

━━━━━━━━━━━━━━━━━━
💰【Reward】

Complete the task above and submit your published video link in this bot  
to receive 🎉 {reward} Node Power"""
                    
                    # 创建 inline keyboard 按钮
                    keyboard = [
                        [InlineKeyboardButton("📎 Submit Link", callback_data=f"submit_link_{task_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                
                # 发送新的提示消息（在视频之后）
                hint_msg = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=final_msg,
                    reply_markup=reply_markup,
                    parse_mode=None
                )
                
                # 保存提示消息ID，以便用户提交链接时删除
                if 'task_hint_messages' not in context.user_data:
                    context.user_data['task_hint_messages'] = {}
                context.user_data['task_hint_messages'][task_id] = hint_msg.message_id
                
                logger.info(f"✅ Video sent successfully, waiting for user to submit link")
                
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
    
    # 支持 submit_task_123 和 submit_link_123 两种格式
    parts = query.data.split('_')
    task_id = int(parts[-1])  # 获取最后一个部分作为 task_id
    logger.info(f"🔗 User {user_id} clicked submit link button for task {task_id}, callback_data: {query.data}")
    context.user_data['submit_task_id'] = task_id
    
    # 获取任务信息
    conn = get_db_connection()
    cur = conn.cursor()
    logger.info(f"📊 Querying task info for user_id={user_id}, task_id={task_id}")
    cur.execute("""
        SELECT dt.title, dt.node_power_reward
        FROM user_tasks ut
        JOIN drama_tasks dt ON ut.task_id = dt.task_id
        WHERE ut.user_id = %s AND ut.task_id = %s
    """, (user_id, task_id))
    task = cur.fetchone()
    logger.info(f"📋 Query result: {task}")
    cur.close()
    conn.close()
    
    if not task:
        logger.warning(f"⚠️ Task {task_id} not found for user {user_id}")
        await query.edit_message_text(
            "❌ 任务不存在" if user_lang == 'zh' else "❌ Task not found",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
            ]])
        )
        return ConversationHandler.END
    
    # 显示提交界面
    message = (
        f"📤 <b>提交任务</b>\n"
        f"🎬 {task['title']}\n"
        f"💰 完成可获得：{task['node_power_reward']} NP\n\n"
        f"📝 请粘贴你上传的视频链接（支持 TikTok、YouTube、Instagram 等平台）"
    ) if user_lang == 'zh' else (
        f"📤 <b>Submit Task</b>\n"
        f"🎬 {task['title']}\n"
        f"💰 Reward: {task['node_power_reward']} NP\n\n"
        f"📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)"
    )
    
    keyboard = [[
        InlineKeyboardButton(
            "« 返回" if user_lang == 'zh' else "« Back",
            callback_data='submit_link'
        )
    ]]
    
    logger.info(f"✏️ 准备编辑原消息: message_id={query.message.message_id}, chat_id={query.message.chat_id}")
    try:
        sent_msg = await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        logger.info(f"✅ 成功编辑原消息: message_id={sent_msg.message_id}")
    except Exception as e:
        logger.error(f"❌ 编辑原消息失败: {e}", exc_info=True)
        # 如果编辑失败，尝试发送新消息
        sent_msg = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
        logger.warning(f"⚠️ 已发送新消息: message_id={sent_msg.message_id}")
    
    # 保存任务卡片消息 ID
    context.user_data['task_card_message_id'] = sent_msg.message_id
    context.user_data['task_card_chat_id'] = query.message.chat_id
    
    return SUBMIT_LINK

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
    """处理链接输入（新版本：编辑原消息）"""
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
            "❌ **链接验证失败**\n\n"
            "🔍 请检查：\n"
            "• 链接是否完整（包含 https://）\n"
            "• 链接是否指向具体的视频页面\n"
            "• 支持的平台：TikTok、YouTube、Instagram、Facebook、Twitter\n\n"
            "🔁 请重新发送正确的链接"
        ) if user_lang == 'zh' else (
            "❌ **Link Validation Failed**\n\n"
            "🔍 Please check:\n"
            "• Link is complete (includes https://)\n"
            "• Link points to a specific video page\n"
            "• Supported platforms: TikTok, YouTube, Instagram, Facebook, Twitter\n\n"
            "🔁 Please resend the correct link"
        )
        
        # 编辑任务卡片显示错误
        if task_card_message_id and task_card_chat_id:
            retry_button = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔁 重试" if user_lang == 'zh' else "🔁 Retry", callback_data=f'submit_task_{task_id}'),
                InlineKeyboardButton("« 返回" if user_lang == 'zh' else "« Back", callback_data='submit_link')
            ]])
            
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=error_msg,
                reply_markup=retry_button,
                parse_mode='HTML'
            )
        return SUBMIT_LINK
    
    # 获取任务信息
    conn = get_db_connection()
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
                text="❌ 任务不存在" if user_lang == 'zh' else "❌ Task not found"
            )
        return ConversationHandler.END
    
    # 更新任务卡片显示"验证中"
    if task_card_message_id and task_card_chat_id:
        verifying_text = (
            f"🔍 <b>正在验证视频内容...</b>\n\n"
            f"🎬 任务：{task['title']}\n"
            f"🔗 链接：{link[:50]}...\n\n"
            f"⏳ 请稍候，这可能需要 5-15 秒"
        ) if user_lang == 'zh' else (
            f"🔍 <b>Verifying video content...</b>\n\n"
            f"🎬 Task: {task['title']}\n"
            f"🔗 Link: {link[:50]}...\n\n"
            f"⏳ Please wait, this may take 5-15 seconds"
        )
        
        await context.bot.edit_message_text(
            chat_id=task_card_chat_id,
            message_id=task_card_message_id,
            text=verifying_text,
            parse_mode='HTML'
        )
    
    # 先验证链接格式
    logger.info(f"🔍 验证链接格式: platform={platform}, url={link[:50]}...")
    validation_result = link_verifier.validate_platform_url(link, platform)
    
    if not validation_result['valid']:
        logger.warning(f"⚠️ 链接格式不合法: {validation_result['error_message']}")
        
        error_text = (
            f"❌ **链接格式错误**\n\n"
            f"📝 {validation_result['error_message']}\n\n"
            f"🔗 您提供的链接: {link[:100]}...\n\n"
            f"✅ 请确保提交的是正确的平台视频链接。"
        ) if user_lang == 'zh' else (
            f"❌ **Invalid Link Format**\n\n"
            f"📝 {validation_result['error_message']}\n\n"
            f"🔗 Your link: {link[:100]}...\n\n"
            f"✅ Please make sure to submit a valid platform video link."
        )
        
        try:
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=error_text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 重试" if user_lang == 'zh' else "🔁 Retry", callback_data=f"submit_link_{task_id}")],
                    [InlineKeyboardButton("« 返回" if user_lang == 'zh' else "« Back", callback_data=f"view_task_{task_id}")]
                ])
            )
            logger.info("✅ 链接格式错误消息已发送")
        except Exception as e:
            logger.error(f"❌ 发送链接格式错误消息失败: {e}", exc_info=True)
        
        logger.info("🔙 返回 SUBMIT_LINK 状态")
        return ConversationHandler.END
    
    logger.info("✅ 链接格式验证通过，开始内容验证")
    
    # 调用验证器（异步）并设置超时
    logger.info(f"🔍 开始调用 verify_link: url={link[:50]}...")
    try:
        verify_result = await asyncio.wait_for(
            link_verifier.verify_link(
                url=link,
                task_title=task['title'],
                task_description=task['description'] or ''
            ),
            timeout=45.0  # 45秒超时
        )
        logger.info(f"✅ verify_link 返回: success={verify_result.get('success')}, matched={verify_result.get('matched')}")
    except asyncio.TimeoutError:
        logger.error("⚠️ verify_link 超时！45秒未返回")
        verify_result = {
            'success': False,
            'matched': False,
            'error': '验证超时，请稍后重试'
        }
    except Exception as e:
        logger.error(f"❌ verify_link 异常: {e}", exc_info=True)
        verify_result = {
            'success': False,
            'matched': False,
            'error': f'验证失败: {str(e)}'
        }
    
    # 检查验证结果
    if not verify_result['success']:
        error_msg = (
            f"❌ **验证失败**\n\n"
            f"无法访问您提交的链接，请检查：\n"
            f"• 链接是否可以正常访问\n"
            f"• 视频是否公开可见\n\n"
            f"错误信息：{verify_result.get('error', '未知错误')}\n\n"
            f"🔁 点击下方按钮重试"
        ) if user_lang == 'zh' else (
            f"❌ **Verification Failed**\n\n"
            f"Cannot access your submitted link. Please check:\n"
            f"• Link is accessible\n"
            f"• Video is publicly visible\n\n"
            f"Error: {verify_result.get('error', 'Unknown error')}\n\n"
            f"🔁 Click button below to retry"
        )
        
        retry_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 重试" if user_lang == 'zh' else "🔁 Retry", callback_data=f'submit_task_{task_id}'),
            InlineKeyboardButton("« 返回" if user_lang == 'zh' else "« Back", callback_data='submit_link')
        ]])
        
        logger.info(f"⚠️ 内容不匹配，准备发送错误消息")
        if task_card_message_id and task_card_chat_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=task_card_chat_id,
                    message_id=task_card_message_id,
                    text=error_msg,
                    reply_markup=retry_button,
                    parse_mode='HTML'
                )
                logger.info("✅ 不匹配错误消息已发送")
            except Exception as e:
                logger.error(f"❌ 发送不匹配错误消息失败: {e}", exc_info=True)
        else:
            logger.warning("⚠️ task_card_message_id 或 task_card_chat_id 为空")
        
        logger.info("✅ 返回 SUBMIT_LINK 状态")
        return SUBMIT_LINK
    
    if not verify_result['matched']:
        error_msg = (
            f"❌ **内容不匹配**\n\n"
            f"📝 您提交的视频内容与任务要求不匹配。\n\n"
            f"🎯 任务要求：{task['title']}\n"
            f"📱 您的视频：{verify_result.get('page_title', '未知')}\n\n"
            f"✅ 请确保上传的是正确的任务视频，然后点击重试。"
        ) if user_lang == 'zh' else (
            f"❌ **Content Mismatch**\n\n"
            f"📝 Your submitted video content doesn't match the task requirements.\n\n"
            f"🎯 Task: {task['title']}\n"
            f"📱 Your video: {verify_result.get('page_title', 'Unknown')}\n\n"
            f"✅ Please ensure you upload the correct task video and click retry."
        )
        
        retry_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 重试" if user_lang == 'zh' else "🔁 Retry", callback_data=f'submit_task_{task_id}'),
            InlineKeyboardButton("« 返回" if user_lang == 'zh' else "« Back", callback_data='submit_link')
        ]])
        
        logger.info(f"⚠️ 内容不匹配，准备发送错误消息")
        if task_card_message_id and task_card_chat_id:
            try:
                await context.bot.edit_message_text(
                    chat_id=task_card_chat_id,
                    message_id=task_card_message_id,
                    text=error_msg,
                    reply_markup=retry_button,
                    parse_mode='HTML'
                )
                logger.info("✅ 不匹配错误消息已发送")
            except Exception as e:
                logger.error(f"❌ 发送不匹配错误消息失败: {e}", exc_info=True)
        else:
            logger.warning("⚠️ task_card_message_id 或 task_card_chat_id 为空")
        
        logger.info("✅ 返回 SUBMIT_LINK 状态")
        return SUBMIT_LINK
    
    # 验证通过，提交链接
    logger.info(f"✅ 验证通过，开始提交任务: user_id={user_id}, task_id={task_id}, platform={platform}")
    try:
        reward = submit_task_link(user_id, task_id, platform, link)
        logger.info(f"✅ 任务提交成功，奖励: {reward} NP")
        
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
    except Exception as e:
        logger.error(f"❌ 提交任务失败: {e}", exc_info=True)
        error_msg = (
            f"❌ <b>提交失败</b>\n\n"
            f"验证成功但保存失败，请联系管理员\n\n"
            f"错误信息：{str(e)}"
        ) if user_lang == 'zh' else (
            f"❌ <b>Submission Failed</b>\n\n"
            f"Verification passed but save failed, please contact admin\n\n"
            f"Error: {str(e)}"
        )
        if task_card_message_id and task_card_chat_id:
            await context.bot.edit_message_text(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id,
                text=error_msg,
                parse_mode='HTML'
            )
        return ConversationHandler.END
    
    try:
        stats = get_user_stats(user_id)
        logger.info(f"✅ 获取用户统计成功: total_power={stats.get('total_power')}")
        # 确保 total_power 不为 None
        if stats.get('total_power') is None:
            stats['total_power'] = 0
            logger.warning("⚠️ total_power 为 None，设置为 0")
    except Exception as e:
        logger.error(f"❌ 获取用户统计失败: {e}", exc_info=True)
        stats = {'total_power': 0}
    
    # 删除之前的提示消息
    try:
        if 'task_hint_messages' in context.user_data and task_id in context.user_data['task_hint_messages']:
            hint_msg_id = context.user_data['task_hint_messages'][task_id]
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=hint_msg_id
            )
            del context.user_data['task_hint_messages'][task_id]
            logger.info(f"✅ Deleted hint message for task {task_id}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete hint message: {e}")
    
    # 删除视频消息
    try:
        if 'task_video_messages' in context.user_data and task_id in context.user_data['task_video_messages']:
            video_msg_id = context.user_data['task_video_messages'][task_id]
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=video_msg_id
            )
            del context.user_data['task_video_messages'][task_id]
            logger.info(f"✅ Deleted video message for task {task_id}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete video message: {e}")
    
    # 显示提交成功消息（编辑任务卡片）
    platform_emoji = {
        'tiktok': '📱 TikTok',
        'youtube': '▶️ YouTube',
        'instagram': '📷 Instagram',
        'facebook': '👥 Facebook',
        'twitter': '🐦 Twitter'
    }
    
    success_msg = (
        f"✅ <b>提交成功！</b>\n\n"
        f"平台：{platform_emoji.get(platform, platform)}\n"
        f"🎁 奖励：+{reward} NP\n"
        f"📊 总算力：{stats['total_power']} NP\n\n"
        f"🚀 继续分享更多视频获得更多奖励！"
    ) if user_lang == 'zh' else (
        f"✅ <b>Submitted Successfully!</b>\n\n"
        f"Platform: {platform_emoji.get(platform, platform)}\n"
        f"🎁 Reward: +{reward} NP\n"
        f"📊 Total Power: {stats['total_power']} NP\n\n"
        f"🚀 Keep sharing more videos to earn more rewards!"
    )
    
    back_button = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 返回主菜单" if user_lang == 'zh' else "🏠 Back to Menu", callback_data='back_to_menu')
    ]])
    
    logger.info(f"📣 准备发送成功消息: task_card_message_id={task_card_message_id}, task_card_chat_id={task_card_chat_id}")
    
    # 先删除任务卡片消息
    if task_card_message_id and task_card_chat_id:
        try:
            await context.bot.delete_message(
                chat_id=task_card_chat_id,
                message_id=task_card_message_id
            )
            logger.info("✅ 任务卡片已删除")
        except Exception as e:
            logger.error(f"❌ 删除任务卡片失败: {e}", exc_info=True)
    else:
        logger.warning("⚠️ task_card_message_id 或 task_card_chat_id 为空，无法删除消息")
    
    # 发送成功通知消息（简短版本，3秒后自动删除）
    try:
        notification_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=success_msg,
            parse_mode='HTML'
        )
        logger.info("✅ 成功通知已发送")
        
        # 3秒后删除通知消息
        await asyncio.sleep(3)
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=notification_msg.message_id
            )
            logger.info("✅ 成功通知已删除")
        except Exception as e:
            logger.warning(f"⚠️ 删除成功通知失败: {e}")
    except Exception as e:
        logger.error(f"❌ 发送成功通知失败: {e}", exc_info=True)
    
    # 自动显示主菜单
    try:
        welcome_message = get_message(user_lang, 'welcome')
        keyboard = get_main_menu_keyboard(user_lang)
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message,
            reply_markup=keyboard
        )
        logger.info("✅ 主菜单已自动显示")
    except Exception as e:
        logger.error(f"❌ 显示主菜单失败: {e}", exc_info=True)
    
    logger.info("✅ link_input_handler 完成，返回 ConversationHandler.END")
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
    logger.info(f"Language callback triggered: user_id={user_id}, callback_data={query.data}")
    
    new_lang = query.data.split('_')[2]
    logger.info(f"Switching language to: {new_lang}")
    
    set_user_language(user_id, new_lang)
    
    # 获取用户信息
    user = query.from_user
    
    # 格式化欢迎消息，替换用户名
    welcome_message = get_message(new_lang, 'welcome').format(
        username=user.username or user.first_name or f"User{user.id}"
    )
    keyboard = get_main_menu_keyboard(new_lang)
    
    # 直接编辑消息，而不是删除后发送新消息
    await query.edit_message_text(
        text=welcome_message,
        reply_markup=keyboard
    )

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
    
    # 运行数据库迁移
    logger.info("🔧 Running database migrations...")
    auto_migrate()
    
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
    application.add_handler(CallbackQueryHandler(my_power_callback, pattern='^my_power$'))
    application.add_handler(CallbackQueryHandler(ranking_callback, pattern='^ranking$'))
    application.add_handler(CallbackQueryHandler(airdrop_callback, pattern='^airdrop$'))
    application.add_handler(CallbackQueryHandler(tutorial_callback, pattern='^tutorial$'))
    application.add_handler(CallbackQueryHandler(language_callback, pattern='^language$'))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern='^set_lang_'))
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$'))
    
    # 对话处理器 - 提交链接
    submit_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(submit_task_select_callback, pattern='^submit_task_\\d+$'),
            CallbackQueryHandler(submit_task_select_callback, pattern='^submit_link_\\d+$')  # 支持从下载消息直接提交
        ],
        states={
            SUBMIT_LINK: [
                CallbackQueryHandler(submit_task_select_callback, pattern='^submit_task_\\d+$'),  # 允许在对话中切换任务
                MessageHandler(filters.TEXT & ~filters.COMMAND, link_input_handler)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(submit_link_callback, pattern='^submit_link$'),
            CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
        ],
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
