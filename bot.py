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
from anti_fraud import check_all_limits, update_last_submit_time, get_user_submit_stats
from retry_submit_handler import retry_submit_callback
from translator import translate_task_content
from i18n import t, get_user_language as get_user_lang_i18n, set_user_language as set_user_lang_i18n, SUPPORTED_LANGUAGES
from category_browser import show_tasks_by_category, category_select_callback, pagination_callback
from category_classifier import classify_drama_by_ai

# ============================================================
# 配置和日志
# ============================================================

# 多语言辅助函数
def get_task_title(task, user_lang, auto_translate=True):
    """根据用户语言获取任务标题"""
    if user_lang == 'en':
        if task.get('title_en'):
            return task['title_en']
        elif auto_translate and task.get('title'):
            # 自动翻译并缓存
            from translator import translate_to_english
            title_en = translate_to_english(task['title'], context="drama title")
            # 更新数据库缓存
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE drama_tasks SET title_en = %s WHERE task_id = %s",
                    (title_en, task['task_id'])
                )
                conn.commit()
                cur.close()
                conn.close()
                logger.info(f"✅ Cached translation for task {task['task_id']}")
            except Exception as e:
                logger.error(f"❌ Failed to cache translation: {e}")
            return title_en
    return task['title']

def get_task_description(task, user_lang, auto_translate=True):
    """根据用户语言获取任务描述"""
    if user_lang == 'en':
        if task.get('description_en'):
            return task['description_en']
        elif auto_translate and task.get('description'):
            # 自动翻译并缓存
            from translator import translate_to_english
            description_en = translate_to_english(task['description'], context="drama description")
            # 更新数据库缓存
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE drama_tasks SET description_en = %s WHERE task_id = %s",
                    (description_en, task['task_id'])
                )
                conn.commit()
                cur.close()
                conn.close()
                logger.info(f"✅ Cached translation for task {task['task_id']}")
            except Exception as e:
                logger.error(f"❌ Failed to cache translation: {e}")
            return description_en
    return task.get('description', '')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 环境变量
BOT_TOKEN = os.getenv('BOT_TOKEN') or '8580007118:AAFmA9OlAT1D_XzUnKGL-0qU_FPK7G6uwyQ'
BOT_USERNAME = os.getenv('BOT_USERNAME') or 'DramaRelayBot'  # Bot username without @
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
    WITHDRAW_ADDRESS,
    WITHDRAW_AMOUNT,
    WITHDRAW_CONFIRM,
    ADMIN_ADD_TASK_TITLE,
    ADMIN_ADD_TASK_DESC,
    ADMIN_ADD_TASK_VIDEO,
    ADMIN_ADD_TASK_REWARD,
) = range(10)

# ============================================================
# 数据库连接
# ============================================================

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def auto_migrate():
    """自动运行数据库迁移"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        logger.info("🔄 检查数据库迁移...")
        
        # 检查 users 表是否有 invited_by 字段
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='invited_by'
        """)
        has_invited_by = cur.fetchone() is not None
        
        if not has_invited_by:
            logger.info("📝 添加邀请系统字段到 users 表...")
            
            # 添加 invited_by 字段
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS invited_by BIGINT
            """)
            
            # 添加 invitation_reward_received 字段
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS invitation_reward_received BOOLEAN DEFAULT FALSE
            """)
            
            # 添加 invitation_reward_received_at 字段
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS invitation_reward_received_at TIMESTAMP
            """)
            
            logger.info("✅ users 表字段已添加")
        
        # 检查 user_invitations 表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_invitations'
            )
        """)
        has_invitations_table = cur.fetchone()['exists']
        
        if not has_invitations_table:
            logger.info("📝 创建 user_invitations 表...")
            cur.execute("""
                CREATE TABLE user_invitations (
                    id SERIAL PRIMARY KEY,
                    inviter_id BIGINT NOT NULL,
                    invitee_id BIGINT NOT NULL UNIQUE,
                    first_task_completed BOOLEAN DEFAULT FALSE,
                    first_task_completed_at TIMESTAMP,
                    total_referral_rewards DECIMAL(18, 2) DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inviter_id) REFERENCES users(user_id),
                    FOREIGN KEY (invitee_id) REFERENCES users(user_id)
                )
            """)
            logger.info("✅ user_invitations 表已创建")
        
        # 检查 referral_rewards 表是否存在
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'referral_rewards'
            )
        """)
        has_rewards_table = cur.fetchone()['exists']
        
        if not has_rewards_table:
            logger.info("📝 创建 referral_rewards 表...")
            cur.execute("""
                CREATE TABLE referral_rewards (
                    id SERIAL PRIMARY KEY,
                    inviter_id BIGINT NOT NULL,
                    invitee_id BIGINT NOT NULL,
                    task_id INTEGER NOT NULL,
                    original_reward INTEGER NOT NULL,
                    referral_reward INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inviter_id) REFERENCES users(user_id),
                    FOREIGN KEY (invitee_id) REFERENCES users(user_id)
                )
            """)
            logger.info("✅ referral_rewards 表已创建")
        
        # 添加 project_id 字段到 drama_tasks 表
        logger.info("📝 添加 project_id 字段到 drama_tasks 表...")
        try:
            cur.execute("""
                ALTER TABLE drama_tasks 
                ADD COLUMN IF NOT EXISTS project_id VARCHAR(255)
            """)
            logger.info("✅ project_id 字段已添加")
        except Exception as e:
            logger.info(f"ℹ️ project_id 字段已存在或添加失败: {e}")
        
        # 同步已有的邀请关系
        if not has_invitations_table and has_invited_by:
            logger.info("📝 同步已有邀请关系...")
            cur.execute("""
                INSERT INTO user_invitations (inviter_id, invitee_id, created_at)
                SELECT invited_by, user_id, created_at
                FROM users
                WHERE invited_by IS NOT NULL
                ON CONFLICT (invitee_id) DO NOTHING
            """)
            synced = cur.rowcount
            logger.info(f"✅ 已同步 {synced} 条邀请关系")
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("✅ 数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库迁移失败: {e}", exc_info=True)
        if conn:
            conn.rollback()
            conn.close()
        return False

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
            invited_by BIGINT,
            invitation_reward_received BOOLEAN DEFAULT FALSE,
            invitation_reward_received_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 短剧任务表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drama_tasks (
            task_id SERIAL PRIMARY KEY,
            project_id VARCHAR(255),
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
    
    # 用户邀请关系表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_invitations (
            id SERIAL PRIMARY KEY,
            inviter_id BIGINT NOT NULL,
            invitee_id BIGINT NOT NULL UNIQUE,
            first_task_completed BOOLEAN DEFAULT FALSE,
            first_task_completed_at TIMESTAMP,
            total_referral_rewards DECIMAL(18, 2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES users(user_id),
            FOREIGN KEY (invitee_id) REFERENCES users(user_id)
        )
    """)
    
    # 推荐奖励记录表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            id SERIAL PRIMARY KEY,
            inviter_id BIGINT NOT NULL,
            invitee_id BIGINT NOT NULL,
            task_id INTEGER NOT NULL,
            original_reward DECIMAL(18, 2) NOT NULL,
            referral_reward DECIMAL(18, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (inviter_id) REFERENCES users(user_id),
            FOREIGN KEY (invitee_id) REFERENCES users(user_id),
            FOREIGN KEY (task_id) REFERENCES drama_tasks(task_id)
        )
    """)
    
    # 提现申请表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            withdrawal_id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            amount DECIMAL(18, 2) NOT NULL,
            sol_address VARCHAR(255) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            tx_hash VARCHAR(255),
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
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
        'welcome': """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 【主菜单】

🎬 X2C 流量节点 (Traffic Node) 已连接
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
        'menu_my_power': '📊 已完成分发任务',
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
💰 奖励：{reward} X2C
📱 平台：{platforms}

⬇️ 点击下方按钮领取任务，系统将自动下载视频到聊天窗口。""",
        'task_claimed': '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📥 【任务已领取】\n\n✅ 任务领取成功！\n\n正在下载视频，下载完成后请上传到你选择的平台，然后回来提交链接。',
        'task_already_claimed': '⚠️ 你已经领取过这个任务了。',
        'select_task_to_submit': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🆕 【继续提交任务】\n\n📋 请选择要提交的任务：',
        'no_tasks_in_progress': '你当前没有进行中的任务。\n\n请先领取任务！',
        'select_platform': '请选择你上传的平台：',
        'enter_link': '请输入你上传的链接：',
        'link_submitted': '✅ 链接提交成功！\n\n你获得了 {reward} X2C！\n\n总算力：{total_power}',
        'invalid_link': '❌ 链接格式不正确，请重新输入。',
        'my_power': """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 【已完成分发任务】

💰 累计获得 X2C 奖励：{total_power}
✅ 已完成任务：{completed_tasks}
🔄 进行中任务：{in_progress_tasks}
📈 本周排名：#{rank}""",
        'ranking': """🏆 全球排行榜

👥 总参与人数：{total_participants}

{ranking_list}

你的排名：#{your_rank}
你的算力：{your_power} X2C""",
        'airdrop_status': """🎁 空投状态

📅 当前轮次：第 {round} 轮
✅ 空投资格：{eligible}
💰 预计空投：{estimated} X2C
⏰ 下次快照：{next_snapshot}

最低要求：100 X2C""",
        'withdraw_prompt': """💰 <b>发起资产提现 (Withdraw)</b>

请回复以下 <b>任意一种</b> 收款账户：

1️⃣ <b>SOL 链上钱包地址</b>
<i>(支持 Phantom, OKX, Bybit 等，以 4 开头)</i>

2️⃣ <b>X2C Pool 账户邮箱</b>
<i>(用于平台内转账，免 Gas 费，即时到账)</i>

⚠️ <b>注意：</b> 请直接发送地址或邮箱，不要附带其他文字。系统将自动识别格式。""",
        'withdraw_amount_prompt': """📥 已收到你的提现地址：

`{address}`

现在请输入你要提取的 X2C 数量：

💡 可提现余额：{balance} X2C""",
        'withdraw_confirm': """📤 提现确认

你正在提现：

🔹 数量：{amount} X2C
🔹 地址：{address}

是否确认提交提现请求？""",
        'withdraw_processing': """⏳ 正在处理你的提现请求…

我们正在将 {amount} X2C 转账至：

`{address}`

请稍候，大约需要 5–20 秒。""",
        'withdraw_success': """✅ 提现成功！

你的 {amount} X2C 已成功发送到：

📥 地址： `{address}`
🔗 交易哈希（Tx Hash）：
{tx_hash}

你可在 Solscan 查看交易详情：
https://solscan.io/tx/{tx_hash}

📘 你的提现已登记完毕，如有疑问可随时联系管理员。""",
        'withdraw_failed': """❌ 提现失败

原因：{error}

💡 请确认地址格式正确，或稍后重试。""",
        'invalid_sol_address': '❌ SOL 地址格式不正确，请重新输入。',
        'invalid_amount': '❌ 提现数量不正确，请输入正整数。',
        'insufficient_balance': '❌ 余额不足，你的可用余额为 {balance} X2C。',
        'confirm_withdraw': '✅ 确认提现',
        'cancel_withdraw': '❌ 取消并返回主菜单',
        'tutorial': """📚 X2C · 挖矿手册（官方指南）

1️⃣ 领取任务

进入「🎬 领取短剧任务」，选择你希望分发的官方短剧内容。

2️⃣ 下载素材

点击「确认领取」后，即可下载本次任务的视频素材。

3️⃣ 发布到平台

将素材发布至 TikTok / YouTube 等视频平台，并确保视频可公开访问。

4️⃣ 提交内容链接

在「🔗 提交链接」中选择任务，填写发布平台及对应链接，用于系统自动验证。

5️⃣ 获得算力奖励

内容验证通过后，系统将立即发放对应的 X2C（算力）到你的账户。

6️⃣ 参与月度空投

累计达到 100+ X2C 的用户，可自动获得当月 X2C 月度空投的参与资格。

───

💡 使用说明
• 每条任务 限提交一次
• 提交链接须真实有效且为本人发布
• 建议分发到 多个平台，可获得更高算力收益
• 请遵守各平台发布规范，避免违规内容""",
        'invite_friends': """👥 邀请好友奖励机制

你邀请的好友完成首次任务验证后：

🔸 你将获得：对方每次任务奖励的「10% 永久算力加成」
🔸 对方不会损失任何奖励（平台额外发放）
🔸 好友首次任务完成，你还可额外领取 +5 X2C 新人奖励

📈 多邀好友 = 多条长期算力通道
🔥 邀得越多，挖得越快

🔗 你的邀请链接：
{invite_link}

📊 邀请统计：
• 已邀请人数：{invited_count} 人
• 有效邀请：{active_count} 人
• 累计推荐奖励：{total_rewards} X2C""",
        'back_to_menu': '« 返回主菜单',
        'cancel': '取消',
        'copy_link': '📋 复制邀请链接',
        'share_link': '📤 分享给好友',
    },
    'en': {
        'welcome': """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏠 【Main Menu】

🎬 X2C Traffic Node Connected
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
        'menu_my_power': '📊 Completed Tasks',
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
💰 Reward: {reward} X2C
📱 Platforms: {platforms}

⬇️ Click the button below to claim the task. The video will be automatically downloaded to the chat.""",
        'task_claimed': '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📥 【Task Claimed】\n\n✅ Task claimed successfully!\n\nDownloading video... After download completes, please upload it to your chosen platform, and come back to submit the link.',
        'task_already_claimed': '⚠️ You have already claimed this task.',
        'select_task_to_submit': '\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🆕 【Continue Submitting】\n\n📋 Please select the task to submit:',
        'no_tasks_in_progress': 'You have no tasks in progress.\n\nPlease claim a task first!',
        'select_platform': 'Please select the platform you uploaded to:',
        'enter_link': 'Please enter your upload link:',
        'link_submitted': '✅ Link submitted successfully!\n\nYou earned {reward} X2C!\n\nTotal Power: {total_power}',
        'invalid_link': '❌ Invalid link format. Please try again.',
        'my_power': """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 【Completed Tasks】

💰 Total X2C Earned: {total_power}
✅ Completed Tasks: {completed_tasks}
🔄 In Progress: {in_progress_tasks}
📈 This Week Rank: #{rank}""",
        'ranking': """🏆 Global Ranking

👥 Total Participants: {total_participants}

{ranking_list}

Your Rank: #{your_rank}
Your Power: {your_power} X2C""",
        'airdrop_status': """🎁 Airdrop Status

📅 Current Round: Round {round}
✅ Eligibility: {eligible}
💰 Estimated Airdrop: {estimated} X2C
⏰ Next Snapshot: {next_snapshot}

Minimum Requirement: 100 X2C""",
        'withdraw_prompt': """💰 <b>Withdraw Assets</b>

Please reply with <b>either</b> of the following receiving accounts:

1️⃣ <b>SOL Wallet Address</b>
<i>(Supports Phantom, OKX, Bybit, etc., starts with 4)</i>

2️⃣ <b>X2C Pool Account Email</b>
<i>(For in-platform transfer, no Gas fee, instant arrival)</i>

⚠️ <b>Note:</b> Please send address or email only, without any other text. System will auto-detect the format.""",
        'withdraw_amount_prompt': """📥 Received your withdrawal address:

`{address}`

Now please enter the amount of X2C you want to withdraw:

💡 Available balance: {balance} X2C""",
        'withdraw_confirm': """📤 Withdrawal Confirmation

You are withdrawing:

🔹 Amount: {amount} X2C
🔹 Address: {address}

Confirm withdrawal request?""",
        'withdraw_processing': """⏳ Processing your withdrawal request…

Transferring {amount} X2C to:

`{address}`

Please wait, this may take 5–20 seconds.""",
        'withdraw_success': """✅ Withdrawal Successful!

Your {amount} X2C has been sent to:

📥 Address: `{address}`
🔗 Transaction Hash (Tx Hash):
{tx_hash}

View transaction details on Solscan:
https://solscan.io/tx/{tx_hash}

📘 Your withdrawal has been recorded. Contact admin if you have questions.""",
        'withdraw_failed': """❌ Withdrawal Failed

Reason: {error}

💡 Please confirm address format is correct, or try again later.""",
        'invalid_sol_address': '❌ Invalid SOL address format. Please try again.',
        'invalid_amount': '❌ Invalid withdrawal amount. Please enter a positive number.',
        'insufficient_balance': '❌ Insufficient balance. Your available balance is {balance} X2C.',
        'confirm_withdraw': '✅ Confirm Withdrawal',
        'cancel_withdraw': '❌ Cancel and Return to Menu',
        'tutorial': """📚 X2C · Mining Manual (Official Guide)

1️⃣ Claim Tasks

Go to "🎬 Get Drama Tasks" and select the official drama content you want to distribute.

2️⃣ Download Materials

After clicking "Confirm Claim", you can download the video materials for this task.

3️⃣ Publish to Platforms

Publish the materials to video platforms such as TikTok / YouTube, and ensure the video is publicly accessible.

4️⃣ Submit Content Link

In "🔗 Submit Link", select the task, fill in the publishing platform and corresponding link for automatic system verification.

5️⃣ Get Computing Power Rewards

After content verification passes, the system will immediately distribute the corresponding X2C (computing power) to your account.

6️⃣ Join Monthly Airdrop

Users who accumulate 100+ X2C can automatically qualify for the monthly X2C airdrop.

───

💡 Usage Instructions
• Each task can only be submitted once
• Submitted links must be real, valid, and published by yourself
• It is recommended to distribute to multiple platforms for higher computing power rewards
• Please follow the publishing rules of each platform and avoid violating content""",
        'invite_friends': """👥 Invite Friends Rewards

When your invited friend completes their first task:

🔸 You get: 10% permanent power bonus from every task they complete
🔸 They don't lose any rewards (platform bonus)
🔸 You also get +5 X2C bonus when they complete first task

📈 More invites = More passive income channels
🔥 Invite more, earn more

🔗 Your invitation link:
{invite_link}

📊 Invitation Stats:
• Total invites: {invited_count}
• Active invites: {active_count}
• Total referral rewards: {total_rewards} X2C""",
        'back_to_menu': '« Back to Menu',
        'cancel': 'Cancel',
        'copy_link': '📋 Copy Invite Link',
        'share_link': '📤 Share to Friends',
    }
}

def get_message(user_lang: str, key: str, **kwargs) -> str:
    """获取本地化消息 - 兼容旧的 MESSAGES 字典和新的 i18n 系统"""
    # 尝试使用新的 i18n 系统
    try:
        # 将旧的 key 转换为新的 key 格式
        if key.startswith('menu_'):
            new_key = f"menu.{key[5:]}"
        elif key in ['welcome', 'tutorial']:
            new_key = key
        elif key.startswith('task_'):
            new_key = f"task.{key[5:]}"
        elif key.startswith('withdraw_'):
            new_key = f"withdraw.{key[9:]}"
        elif key.startswith('invite_'):
            new_key = f"invite.{key[7:]}"
        elif key in ['back_to_menu', 'cancel']:
            new_key = f"common.{key}"
        else:
            new_key = key
        
        result = t(new_key, user_lang, **kwargs)
        if result != new_key:  # 如果找到了翻译
            return result
    except:
        pass
    
    # 回退到旧的 MESSAGES 字典
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
    
    if result and result['language']:
        lang = result['language']
        # 兼容旧的语言代码
        if lang == 'zh':
            return 'zh-CN'
        elif lang in SUPPORTED_LANGUAGES:
            return lang
    
    return 'zh-CN'  # 默认返回简体中文

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
    
    # 处理推荐奖励
    try:
        from invitation_system import process_referral_reward
        process_referral_reward(user_id, task_id, reward)
    except Exception as e:
        logger.error(f"⚠️ Failed to process referral reward: {e}")
    
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
            InlineKeyboardButton(t('menu.get_tasks', user_lang), callback_data='get_tasks'),
            InlineKeyboardButton(t('menu.submit_link', user_lang), callback_data='submit_link'),
        ],
        [
            InlineKeyboardButton(t('menu.my_power', user_lang), callback_data='my_power'),
            InlineKeyboardButton(t('menu.ranking', user_lang), callback_data='ranking'),
        ],
        [
            InlineKeyboardButton(t('menu.airdrop', user_lang), callback_data='invite_friends'),
            InlineKeyboardButton(t('menu.bind_wallet', user_lang), callback_data='bind_wallet'),
        ],
        [
            InlineKeyboardButton(t('menu.tutorial', user_lang), callback_data='tutorial'),
            InlineKeyboardButton(t('menu.language', user_lang), callback_data='language'),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# 命令处理函数
# ============================================================

async def check_invitation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """检查邀请系统数据的临时命令"""
    user_id = update.effective_user.id
    
    # 仅允许管理员使用（您的user_id）
    if user_id != 5156570084:
        await update.message.reply_text("❌ 此命令仅供管理员使用")
        return
    
    await update.message.reply_text("🔍 正在查询数据库...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        inviter_id = 5156570084
        invitee_id = 8550836392
        
        result_text = "📊 邀请系统数据检查\n\n"
        
        # 1. 检查邀请关系
        result_text += "\u30101. 邀请关系】\n"
        cur.execute("""
            SELECT * FROM user_invitations 
            WHERE inviter_id = %s AND invitee_id = %s
        """, (inviter_id, invitee_id))
        invitation = cur.fetchone()
        
        if invitation:
            result_text += f"✅ 邀请关系已记录\n"
            result_text += f"   • 首次任务完成: {invitation['first_task_completed']}\n"
            result_text += f"   • 首次任务完成时间: {invitation['first_task_completed_at']}\n"
            result_text += f"   • 累计推荐奖励: {invitation['total_referral_rewards']}\n"
            result_text += f"   • 创建时间: {invitation['created_at']}\n"
        else:
            result_text += "❌ 未找到邀请关系记录\n"
        
        # 2. 检查被邀请人的任务
        result_text += "\n\u30102. 被邀请人任务】\n"
        cur.execute("""
            SELECT ut.*, dt.title
            FROM user_tasks ut
            JOIN drama_tasks dt ON ut.task_id = dt.task_id
            WHERE ut.user_id = %s AND ut.status = 'submitted'
            ORDER BY ut.submitted_at DESC
            LIMIT 5
        """, (invitee_id,))
        tasks = cur.fetchall()
        
        if tasks:
            result_text += f"✅ 完成了 {len(tasks)} 个任务\n"
            for i, task in enumerate(tasks, 1):
                result_text += f"   {i}. {task['title']} ({task['node_power_earned']} X2C)\n"
                result_text += f"      提交时间: {task['submitted_at']}\n"
        else:
            result_text += "❌ 没有完成任何任务\n"
        
        # 3. 检查推荐奖励记录
        result_text += "\n\u30103. 推荐奖励记录】\n"
        cur.execute("""
            SELECT * FROM referral_rewards 
            WHERE inviter_id = %s AND invitee_id = %s
            ORDER BY created_at DESC
        """, (inviter_id, invitee_id))
        rewards = cur.fetchall()
        
        if rewards:
            result_text += f"✅ 找到 {len(rewards)} 条奖励记录\n"
            for i, reward in enumerate(rewards, 1):
                result_text += f"   {i}. 任务{reward['task_id']}: {reward['referral_reward']} X2C\n"
        else:
            result_text += "❌ 没有推荐奖励记录\n"
        
        # 4. 问题分析
        result_text += "\n\u30104. 问题分析】\n"
        if invitation and tasks and not rewards:
            result_text += "⚠️ 发现问题：\n"
            result_text += "   • 邀请关系已记录\n"
            result_text += "   • 被邀请人完成了任务\n"
            result_text += "   • 但没有推荐奖励记录\n\n"
            
            if tasks[0]['submitted_at'] and invitation['created_at']:
                if tasks[0]['submitted_at'] < invitation['created_at']:
                    result_text += "❌ 原因：任务完成时间早于邀请时间\n"
                else:
                    result_text += "❌ 原因：process_referral_reward() 执行失败\n"
        elif invitation and not invitation['first_task_completed'] and tasks:
            result_text += "⚠️ 发现问题：\n"
            result_text += "   • 邀请关系已记录\n"
            result_text += "   • 被邀请人完成了任务\n"
            result_text += "   • 但 first_task_completed 未标记\n"
        else:
            result_text += "✅ 数据正常\n"
        
        cur.close()
        conn.close()
        
        await update.message.reply_text(result_text)
        
    except Exception as e:
        logger.error(f"❌ 检查邀请数据失败: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 查询失败: {str(e)}")

async def manual_reward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """手动补发推荐奖励的临时命令"""
    user_id = update.effective_user.id
    
    # 仅允许管理员使用
    if user_id != 5156570084:
        await update.message.reply_text("❌ 此命令仅供管理员使用")
        return
    
    await update.message.reply_text("🔧 正在补发推荐奖励...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        inviter_id = 5156570084
        invitee_id = 8550836392
        task_id = 51  # 从查询结果中看到的任务ID
        original_reward = 10  # 原始奖励
        referral_reward = int(original_reward * 0.1)  # 10%的推荐奖励
        
        # 1. 检查是否已经补发过
        cur.execute("""
            SELECT * FROM referral_rewards 
            WHERE inviter_id = %s AND invitee_id = %s AND task_id = %s
        """, (inviter_id, invitee_id, task_id))
        existing = cur.fetchone()
        
        if existing:
            await update.message.reply_text("⚠️ 该任务的推荐奖励已经发放过了")
            cur.close()
            conn.close()
            return
        
        # 2. 插入推荐奖励记录
        cur.execute("""
            INSERT INTO referral_rewards 
            (inviter_id, invitee_id, task_id, original_reward, referral_reward)
            VALUES (%s, %s, %s, %s, %s)
        """, (inviter_id, invitee_id, task_id, original_reward, referral_reward))
        
        # 3. 更新邀请关系表
        cur.execute("""
            UPDATE user_invitations
            SET first_task_completed = TRUE,
                first_task_completed_at = CURRENT_TIMESTAMP,
                total_referral_rewards = total_referral_rewards + %s
            WHERE inviter_id = %s AND invitee_id = %s
        """, (referral_reward, inviter_id, invitee_id))
        
        # 4. 给邀请人增加算力
        cur.execute("""
            UPDATE users
            SET total_node_power = total_node_power + %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (referral_reward, inviter_id))
        
        # 5. 给被邀请人发放新人奖励（+5 X2C）
        cur.execute("""
            UPDATE users
            SET total_node_power = total_node_power + 5,
                invitation_reward_received = TRUE,
                invitation_reward_received_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND invitation_reward_received = FALSE
        """, (invitee_id,))
        invitee_bonus_given = cur.rowcount > 0
        
        conn.commit()
        cur.close()
        conn.close()
        
        result_text = "✅ 推荐奖励补发成功！\n\n"
        result_text += f"🎯 任务ID: {task_id}\n"
        result_text += f"💰 原始奖励: {original_reward} X2C\n"
        result_text += f"🎁 推荐奖励: {referral_reward} X2C (10%)\n\n"
        result_text += f"✅ 已给邀请人增加 {referral_reward} X2C\n"
        
        if invitee_bonus_given:
            result_text += f"✅ 已给被邀请人发放新人奖励 +5 X2C\n"
        else:
            result_text += f"⚠️ 被邀请人已领取过新人奖励\n"
        
        result_text += "\n🔄 请再次发送 /check_invitation 查看更新后的数据"
        
        await update.message.reply_text(result_text)
        
        logger.info(f"✅ 手动补发推荐奖励成功: inviter={inviter_id}, invitee={invitee_id}, task={task_id}, reward={referral_reward}")
        
    except Exception as e:
        logger.error(f"❌ 补发推荐奖励失败: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 补发失败: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()

async def clear_pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """清理所有 pending 状态的验证任务"""
    user_id = update.effective_user.id
    
    # 仅允许管理员使用
    if user_id != 5156570084:
        await update.message.reply_text("❌ 此命令仅供管理员使用")
        return
    
    await update.message.reply_text("🧹 正在清理所有 pending 状态的验证任务...")
    
    try:
        from async_verification_worker import force_fail_all_pending
        cleaned_count = force_fail_all_pending()
        
        await update.message.reply_text(
            f"✅ 清理完成！\n\n"
            f"🧹 已将 {cleaned_count} 条 pending 任务标记为失败\n\n"
            f"用户现在可以重新提交链接了。"
        )
        
        logger.info(f"🧹 管理员 {user_id} 清理了 {cleaned_count} 条 pending 任务")
        
    except Exception as e:
        logger.error(f"❌ 清理 pending 任务失败: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 清理失败: {str(e)}")


async def debug_pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """调试命令：查看 pending_verifications 表中的记录"""
    user_id = update.effective_user.id
    
    # 仅允许管理员使用
    if user_id != 5156570084:
        await update.message.reply_text("❌ 此命令仅供管理员使用")
        return
    
    await update.message.reply_text("🔍 正在查询 pending_verifications 表...")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 查询所有记录（最近 20 条）
        cur.execute("""
            SELECT pv.id, pv.user_id, pv.task_id, pv.video_url, pv.platform, 
                   pv.status, pv.retry_count, pv.error_message, pv.created_at,
                   dt.title as task_title
            FROM pending_verifications pv
            LEFT JOIN drama_tasks dt ON pv.task_id = dt.task_id
            ORDER BY pv.created_at DESC
            LIMIT 20
        """)
        
        records = cur.fetchall()
        
        if not records:
            await update.message.reply_text("✅ pending_verifications 表中没有记录")
            return
        
        # 构建消息
        message_parts = [f"📊 找到 {len(records)} 条记录\n"]
        
        for r in records:
            record = dict(r)
            status_emoji = {
                'pending': '⏳',
                'completed': '✅',
                'failed': '❌'
            }.get(record['status'], '❓')
            
            # 显示完整的 video_url
            video_url = record['video_url'] or 'N/A'
            
            message_parts.append(
                f"\n{status_emoji} ID: {record['id']}\n"
                f"用户: {record['user_id']}\n"
                f"任务: {record['task_id']} - {record.get('task_title', 'N/A')}\n"
                f"链接: {video_url}\n"
                f"状态: {record['status']} (重试: {record['retry_count']})\n"
                f"错误: {record.get('error_message', 'N/A')}\n"
                f"时间: {record['created_at']}\n"
                f"{'='*40}"
            )
        
        # 如果消息太长，分段发送
        full_message = '\n'.join(message_parts)
        if len(full_message) > 4000:
            # 发送前 4000 个字符
            await update.message.reply_text(full_message[:4000] + "\n\n... (截断)")
        else:
            await update.message.reply_text(full_message)
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ 查询 pending_verifications 失败: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 查询失败: {str(e)}")


async def set_expiry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置任务有效期（小时）
    
    用法: /set_expiry <小时数>
    示例: /set_expiry 48
    """
    user_id = update.effective_user.id
    
    # 仅允许管理员使用
    if user_id != 5156570084:
        await update.message.reply_text("❌ 此命令仅供管理员使用")
        return
    
    from task_expiry import get_task_expiry_hours, set_task_expiry_hours
    
    # 获取参数
    if not context.args:
        # 显示当前配置
        current_hours = get_task_expiry_hours()
        await update.message.reply_text(
            f"🕐 任务有效期设置\n\n"
            f"当前有效期: {current_hours} 小时\n\n"
            f"用法: /set_expiry <小时数>\n"
            f"示例: /set_expiry 48"
        )
        return
    
    try:
        new_hours = int(context.args[0])
        
        if new_hours < 1:
            await update.message.reply_text("❌ 有效期必须大于 0 小时")
            return
        
        if new_hours > 720:  # 最多 30 天
            await update.message.reply_text("❌ 有效期不能超过 720 小时（30天）")
            return
        
        old_hours = get_task_expiry_hours()
        
        if set_task_expiry_hours(new_hours):
            await update.message.reply_text(
                f"✅ 任务有效期已更新\n\n"
                f"原有效期: {old_hours} 小时\n"
                f"新有效期: {new_hours} 小时\n\n"
                f"任务创建后超过 {new_hours} 小时将自动过期"
            )
            logger.info(f"🕐 管理员 {user_id} 将任务有效期从 {old_hours} 小时改为 {new_hours} 小时")
        else:
            await update.message.reply_text("❌ 设置失败，请查看日志")
            
    except ValueError:
        await update.message.reply_text("❌ 请输入有效的数字\n\n示例: /set_expiry 48")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    user_lang = get_user_language(user.id)
    
    # 处理邀请链接参数
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith('invite_'):
            try:
                inviter_id = int(arg.replace('invite_', ''))
                if inviter_id != user.id:  # 不能邀请自己
                    from invitation_system import record_invitation
                    success = record_invitation(inviter_id, user.id)
                    if success:
                        logger.info(f"✅ User {user.id} was invited by {inviter_id}")
                        # 可以在这里发送欢迎消息提示被邀请
            except ValueError:
                logger.warning(f"⚠️ Invalid invite parameter: {arg}")
    
    # 格式化欢迎消息，替换用户名
    username = user.username or user.first_name or f"User{user.id}"
    welcome_message = get_message(user_lang, 'welcome', username=username)
    keyboard = get_main_menu_keyboard(user_lang)
    
    await update.message.reply_text(welcome_message, reply_markup=keyboard, parse_mode='HTML')

async def get_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理领取任务按钮 - 默认显示 latest 分类"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 默认显示 latest 分类
    await show_tasks_by_category(update, context, 'latest')

async def task_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理任务详情"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    task_id = int(query.data.split('_')[1])
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text("任务不存在" if user_lang.startswith('zh') else "Task not found")
        return
    
    # 显示任务详情，根据用户语言选择内容（自动翻译）
    title = get_task_title(task, user_lang)
    description = get_task_description(task, user_lang)
    
    message = get_message(user_lang, 'task_details',
        title=title,
        description=description or 'N/A',
        duration=task['duration'],
        reward=task['node_power_reward'],
        platforms=task['platform_requirements']
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ 确认领取" if user_lang.startswith('zh') else "✅ Claim Task", callback_data=f"claim_{task_id}")],
        [InlineKeyboardButton("« 返回任务列表" if user_lang.startswith('zh') else "« Back to Tasks", callback_data='get_tasks')]
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
    
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"⚠️ query.answer() failed in claim_task_callback: {e}")
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    try:
        task_id = int(query.data.split('_')[1])
    except (IndexError, ValueError) as e:
        logger.error(f"❌ Failed to parse task_id from callback_data: {query.data}, error: {e}")
        return
    
    logger.info(f"🔔 claim_task_callback triggered! user_id={user_id}, task_id={task_id}, callback_data={query.data}")
    
    # 获取任务详情
    task = get_task_by_id(task_id)
    
    if not task:
        await query.edit_message_text(
            "❌ 任务不存在" if user_lang.startswith('zh') else "❌ Task not found",
            reply_markup=get_main_menu_keyboard(user_lang)
        )
        return
    
    # 检查任务是否已过期（48小时）
    from task_expiry import is_task_expired
    if is_task_expired(task):
        await query.edit_message_text(
            "❌ 该任务已过期，请选择其他任务" if user_lang.startswith('zh') else "❌ This task has expired, please select another task",
            reply_markup=get_main_menu_keyboard(user_lang)
        )
        return
    
    # 先检查是否已经领取
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_tasks WHERE user_id = %s AND task_id = %s", (user_id, task_id))
    existing_claim = cur.fetchone()
    cur.close()
    conn.close()
    
    if existing_claim:
        logger.info(f"⚠️ Task already claimed by user")
        message = get_message(user_lang, 'task_already_claimed')
        keyboard = get_main_menu_keyboard(user_lang)
        await query.edit_message_text(message, reply_markup=keyboard)
        return
    
    # 删除任务详情消息
    try:
        await query.delete_message()
    except Exception as e:
        logger.warning(f"⚠️ Failed to delete task details message: {e}")
    
    # 如果任务有视频链接，下载并发送视频
    video_url = task.get('video_url')
    logger.info(f"🎥 video_url from task: {video_url}")
    if video_url and (video_url.startswith('http://') or video_url.startswith('https://')):
        logger.info(f"✅ Starting video processing from: {video_url}")
        
        import requests
        import tempfile
        import os
        
        # 先检查文件大小
        try:
            head_response = requests.head(video_url, timeout=10)
            file_size = int(head_response.headers.get('content-length', 0))
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"📊 Video file size: {file_size_mb:.2f} MB")
        except Exception as e:
            logger.error(f"⚠️ Failed to get file size: {e}, assuming small file")
            file_size = 0
            file_size_mb = 0
        
        # 如果文件大于50MB,不下载,直接提供下载链接
        if file_size > 50 * 1024 * 1024:
            logger.warning(f"⚠️ Video file too large ({file_size_mb:.2f} MB), providing download link instead")
            
            # 准备任务信息
            title = task.get('title', '')
            description = task.get('description', '')
            keywords_raw = task.get('keywords_template', '')
            reward = task.get('node_power_reward', 0)
            
            # 清理 keywords_template
            keywords_lines = keywords_raw.split('\n')
            cleaned_keywords = []
            for line in keywords_lines:
                if '视频链接：' not in line and line.strip():
                    if 'keywords_template=' in line:
                        cleaned_keywords.append(line.split('keywords_template=')[1])
                    elif '上传关键词描述：' in line:
                        cleaned_keywords.append(line.split('上传关键词描述：')[1])
                    else:
                        cleaned_keywords.append(line)
            keywords = '\n'.join(cleaned_keywords) if cleaned_keywords else keywords_raw
            
            # 格式化关键词为 #tag 格式
            keywords_list = [kw.strip() for kw in keywords.replace(',', ' ').split() if kw.strip()]
            hashtags = ' '.join([f'#{kw}' for kw in keywords_list[:11]])
            
            # 提取剧情关键词和剧名
            plot_keyword = keywords_list[0] if keywords_list else "剧情关键词"
            import re
            drama_name_match = re.search(r'《(.+?)》', title)
            drama_name = drama_name_match.group(1) if drama_name_match else "剧名"
            drama_name_with_brackets = f"《{drama_name}》"
            
            # 发送下载链接消息
            if user_lang.startswith('zh'):
                download_msg = f"""📥 <b>视频文件过大({file_size_mb:.0f} MB)</b>

请点击下面的链接直接下载：

🔗 <a href=\"{video_url}\">点击下载视频</a>

💡 <b>提示：</b>
• 点击链接在浏览器中打开
• 右键"另存为"或直接下载
• 下载后上传到 TikTok/YouTube

━━━━━━━━━━━━━━━━━━
📋【一键复制内容】
💡 请复制到 TikTok 或 YouTube

<pre>
{plot_keyword} | {drama_name}
{description}
{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━
💰【奖励说明】

完成以上任务，点击下方的"提交链接"按钮，机器人验证通过你发布后的视频链接  
即可获得 🎉 {reward} X2C"""
            else:
                download_msg = f"""📥 <b>Video file is too large ({file_size_mb:.0f} MB)</b>

Please click the link below to download:

🔗 <a href=\"{video_url}\">Click to download video</a>

💡 <b>Tips:</b>
• Click the link to open in browser
• Right-click "Save as" or download directly
• Upload to TikTok/YouTube after downloading

━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】
💡 Please copy to TikTok or YouTube

<pre>
{title}
{description}
{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━
💰【Reward】

Complete the task above and submit your published video link in this bot  
to receive 🎉 {reward} X2C"""
            
            # 创建提交链接按钮
            keyboard = [
                [InlineKeyboardButton("📎 提交链接" if user_lang.startswith('zh') else "📎 Submit Link", callback_data=f"submit_link_{task_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 发送消息
            hint_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=download_msg,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # 保存提示消息ID
            if 'task_hint_messages' not in context.user_data:
                context.user_data['task_hint_messages'] = {}
            context.user_data['task_hint_messages'][task_id] = hint_msg.message_id
            
            # 标记任务为已领取
            claim_result = claim_task(user_id, task_id)
            logger.info(f"✅ Download link sent for large video file, task claimed: {claim_result}")
            return
        
        # 不下载视频，直接发送链接
        logger.info(f"✅ Sending video link instead of downloading...")
        try:
            # 准备任务信息
            title = task.get('title', '')
            description = task.get('description', '')
            keywords_raw = task.get('keywords_template', '') or ''
            reward = task.get('node_power_reward', 0)
            
            # 清理 keywords_template
            if keywords_raw:
                keywords_lines = keywords_raw.split('\n')
                cleaned_keywords = []
                for line in keywords_lines:
                    if '视频链接：' not in line and line.strip():
                        if 'keywords_template=' in line:
                            cleaned_keywords.append(line.split('keywords_template=')[1])
                        elif '上传关键词描述：' in line:
                            cleaned_keywords.append(line.split('上传关键词描述：')[1])
                        else:
                            cleaned_keywords.append(line)
                keywords = '\n'.join(cleaned_keywords) if cleaned_keywords else ''
            else:
                keywords = ''
            
            # 发送最终提示消息
            # 格式化关键词为 #tag 格式，限制最多4个标签
            keywords_list = [kw.strip() for kw in keywords.replace(',', ' ').split() if kw.strip()]
            hashtags = ' '.join([f'#{kw}' for kw in keywords_list[:4]])  # 限制4个标签
            
            # 提取剧名（从 title 中提取《》中的内容）
            import re
            drama_name_match = re.search(r'《(.+?)》', title)
            drama_name = drama_name_match.group(1) if drama_name_match else title
            
            if user_lang.startswith('zh'):
                # 构建复制文案内容 - 只保留标题和剧情描述
                copy_content = f"""{drama_name}
{description}"""
                
                final_msg = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🆕 <b>【新任务发布】</b>

💰 <b>奖励：</b>{reward} X2C
🎬 <b>剧集：</b>{title}

<b>👇 请按以下步骤操作：</b>

<b>1️⃣ 下载视频素材</b>
🔗 <a href="{video_url}">点击这里下载视频</a>
<i>(如无法下载，请复制链接到浏览器打开)</i>

<b>2️⃣ 一键复制文案</b>
💡 <i>点击下方文字框，发布时直接粘贴到标题和简介：</i>

<pre>{copy_content}</pre>

<b>3️⃣ 提交任务</b>
📝 请在下方粘贴你发布后的 <b>TikTok/YouTube 链接</b>：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
                
                # 创建 inline keyboard 按钮
                keyboard = [
                    [InlineKeyboardButton("« 返回", callback_data='back_to_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                final_msg = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆕 <b>【New Task】</b>

📤 <b>Submit Task</b>
🎬 {title}
💰 Reward: {reward} X2C
🔗 Video Link: {video_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋【One-Click Copy Content】
💡 Please copy to TikTok or YouTube

<pre>
{title}
Clip from @X2CDramaOfficial

{description}
{hashtags}
</pre>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)"""
                
                # 创建 inline keyboard 按钮
                keyboard = [
                    [InlineKeyboardButton("« Back", callback_data='back_to_menu')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            # 发送新的提示消息（在视频之后）
            hint_msg = await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=final_msg,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # 保存提示消息ID，以便用户提交链接时删除
            if 'task_hint_messages' not in context.user_data:
                context.user_data['task_hint_messages'] = {}
            context.user_data['task_hint_messages'][task_id] = hint_msg.message_id
            
            # 保存任务ID和消息ID，以便用户直接输入链接
            context.user_data['submit_task_id'] = task_id
            context.user_data['task_card_message_id'] = hint_msg.message_id
            context.user_data['task_card_chat_id'] = query.message.chat_id
            
            # 标记任务为已领取
            claim_result = claim_task(user_id, task_id)
            logger.info(f"✅ Video sent successfully, task claimed: {claim_result}, waiting for user to submit link")
            
            # 返回 SUBMIT_LINK 状态，让用户可以直接输入链接
            return SUBMIT_LINK
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            error_msg = "❌ 视频下载失败，请稍后重试" if user_lang.startswith('zh') else "❌ Failed to download video, please try again later"
            
            # 创建返回主菜单按钮
            keyboard = [
                [InlineKeyboardButton("« 返回主菜单" if user_lang.startswith('zh') else "« Back to Menu", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"{error_msg}\n\n📎 视频链接: {video_url}",
                reply_markup=reply_markup
            )

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
    
    # 获取用户所有 pending 和 failed 状态的任务
    from check_pending_status import get_user_pending_tasks, get_user_failed_tasks
    conn = get_db_connection()
    pending_task_ids = get_user_pending_tasks(conn, user_id)
    failed_tasks = get_user_failed_tasks(conn, user_id)  # {task_id: error_message}
    conn.close()
    
    # 显示进行中的任务列表
    keyboard = []
    for task in tasks:
        task_id = task['task_id']
        if task_id in pending_task_ids:
            # pending 状态：显示但不可点击
            button_text = f"⏳ {task['title']} (核验中...)" if user_lang.startswith('zh') else f"⏳ {task['title']} (Verifying...)"
            # 使用 noop 回调，点击时显示提示
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"pending_task_{task_id}")])
        elif task_id in failed_tasks:
            # failed 状态：显示失败标记，可以重新提交
            button_text = f"❌ {task['title']} (请重新提交)" if user_lang.startswith('zh') else f"❌ {task['title']} (Please resubmit)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"submit_task_{task_id}")])
        else:
            # 可以提交
            button_text = f"📤 {task['title']} ({task['node_power_reward']} X2C)"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"submit_task_{task_id}")])
    
    # 如果有失败的任务，在消息中添加提示
    has_failed = len(failed_tasks) > 0
    
    keyboard.append([InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')])
    
    # 构建消息文本
    message_text = get_message(user_lang, 'select_task_to_submit')
    if has_failed:
        failed_hint = "\n\n⚠️ 标记为 ❌ 的任务验证失败，请重新提交链接" if user_lang.startswith('zh') else "\n\n⚠️ Tasks marked with ❌ failed verification, please resubmit"
        message_text += failed_hint
    
    await query.edit_message_text(
        message_text,
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
        SELECT dt.*
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
            "❌ 任务不存在" if user_lang.startswith('zh') else "❌ Task not found",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
            ]])
        )
        return ConversationHandler.END
    
    # 显示提交界面（包含完整的描述和标签）
    title = task.get('title', '')
    # 兼容不同的字段名：description 或 task_template
    description = task.get('description') or task.get('task_template', '') or ''
    # 兼容不同的字段名：keywords 或 keywords_template
    keywords_raw = task.get('keywords') or task.get('keywords_template', '') or ''
    reward = task.get('node_power_reward', 0)
    # 获取视频链接
    video_url = task.get('video_url', '')
    
    # 清理 keywords：完全删除包含“视频链接：”的行
    keywords_lines = keywords_raw.split('\n') if keywords_raw else []
    cleaned_keywords = []
    for line in keywords_lines:
        # 跳过包含“视频链接：”的行
        if '视频链接：' not in line and line.strip():
            # 如果行中包含"keywords_template="，提取后面的内容
            if 'keywords_template=' in line:
                cleaned_keywords.append(line.split('keywords_template=')[1])
            # 如果行中包含“上传关键词描述：”，提取后面的内容
            elif '上传关键词描述：' in line:
                cleaned_keywords.append(line.split('上传关键词描述：')[1])
            else:
                cleaned_keywords.append(line)
    keywords = '\n'.join(cleaned_keywords) if cleaned_keywords else keywords_raw
    
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
    
    # 构建消息
    message_parts = []
    
    if user_lang.startswith('zh'):
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("🆕 <b>【新任务】</b>")
        message_parts.append("")
        message_parts.append("📤 <b>提交任务</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 完成可获得：{reward} X2C")
        if video_url:
            message_parts.append(f"🔗 视频链接：{video_url}")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【一键复制内容】")
        message_parts.append("💡 请复制到 TikTok 或 YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(f"{plot_keyword} | {drama_name}")
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 请粘贴你上传的视频链接（支持 TikTok、YouTube、Instagram 等平台）")
    else:
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("🆕 <b>【New Task】</b>")
        message_parts.append("")
        message_parts.append("📤 <b>Submit Task</b>")
        message_parts.append(f"🎬 {title}")
        message_parts.append(f"💰 Reward: {reward} X2C")
        if video_url:
            message_parts.append(f"🔗 Video Link: {video_url}")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("📋【One-Click Copy Content】")
        message_parts.append("💡 Please copy to TikTok or YouTube")
        message_parts.append("")
        message_parts.append("<pre>")
        message_parts.append(title)
        message_parts.append(description)
        message_parts.append(hashtags)
        message_parts.append("</pre>")
        message_parts.append("")
        message_parts.append("━" * 30)
        message_parts.append("")
        message_parts.append("📝 Please paste your uploaded video link (TikTok, YouTube, Instagram, etc.)")
    
    message = "\n".join(message_parts)
    
    keyboard = [[
        InlineKeyboardButton(
            "« 返回" if user_lang.startswith('zh') else "« Back",
            callback_data='back_to_menu'
        )
    ]]
    
    logger.info(f"✏️ 准备编辑原消息: message_id={query.message.message_id}, chat_id={query.message.chat_id}")
    try:
        sent_msg = await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        logger.info(f"✅ 成功编辑原消息: message_id={sent_msg.message_id}")
    except Exception as e:
        logger.error(f"❌ 编辑原消息失败: {e}", exc_info=True)
        # 如果编辑失败，尝试发送新消息
        sent_msg = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML',
            disable_web_page_preview=True
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
            "❌ **链接验证失败**\n\n"
            "🔍 请检查：\n"
            "• 链接是否完整（包含 https://）\n"
            "• 链接是否指向具体的视频页面\n"
            "• 支持的平台：TikTok、YouTube、Instagram、Facebook、Twitter\n\n"
            "🔁 请重新发送正确的链接"
        ) if user_lang.startswith('zh') else (
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
            f"❌ **链接格式错误**\n\n"
            f"📝 {validation_result['error_message']}\n\n"
            f"🔗 您提供的链接: {link[:100]}...\n\n"
            f"✅ 请确保提交的是正确的平台视频链接。"
        ) if user_lang.startswith('zh') else (
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
            "✅ **该链接已提交过**\n\n"
            "此链接之前已成功验证并获得奖励。\n"
            "请提交新的视频链接。"
        ) if user_lang.startswith('zh') else (
            "✅ **Link Already Submitted**\n\n"
            "This link was already verified and rewarded.\n"
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
        f"✅ <b>链接已接收！</b>\n\n"
        f"🎬 任务：{task['title']}\n"
        f"💰 奖励：{task['node_power_reward']} X2C\n\n"
        f"🔍 系统正在后台核验中，请稍候...\n"
        f"核验完成后会自动通知您结果。\n\n"
        f"💡 您现在可以继续领取其他任务！"
    ) if user_lang.startswith('zh') else (
        f"✅ <b>Link Received!</b>\n\n"
        f"🎬 Task: {task['title']}\n"
        f"💰 Reward: {task['node_power_reward']} X2C\n\n"
        f"🔍 System is verifying in background...\n"
        f"You will be notified when verification is complete.\n\n"
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
    
    # 获取总参与人数
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_id) as total FROM user_tasks WHERE status = 'submitted'")
    result = cur.fetchone()
    total_participants = result['total'] if result else 0
    cur.close()
    conn.close()
    
    ranking_list = []
    for r in ranking:
        name = r['first_name'] or r['username'] or f"User {r['user_id']}"
        ranking_list.append(f"{r['rank']}. {name} - {r['total_node_power']} X2C")
    
    message = get_message(user_lang, 'ranking',
        ranking_list='\n'.join(ranking_list),
        your_rank=stats['rank'],
        your_power=stats['total_power'],
        total_participants=total_participants
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
    eligible = "✅ 是" if stats['total_power'] >= 100 else "❌ 否（需要 100+ X2C）"
    if user_lang == 'en':
        eligible = "✅ Yes" if stats['total_power'] >= 100 else "❌ No (Need 100+ X2C)"
    
    message = get_message(user_lang, 'airdrop_status',
        round=1,
        eligible=eligible,
        estimated=stats['estimated_airdrop'],
        next_snapshot="2025-12-01" if user_lang.startswith('zh') else "Dec 1, 2025"
    )
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await query.edit_message_text(message, reply_markup=keyboard)

async def invite_friends_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
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
        if user_lang.startswith('zh'):
            message += "\n\n👥 有效邀请列表："
        else:
            message += "\n\n👥 Active Invitees:"
        
        for inv in invitees_data['invitees']:
            username = inv.get('username') or inv.get('first_name') or f"User_{inv['user_id']}"
            if inv.get('username'):
                message += f"\n• @{username}"
            else:
                message += f"\n• {username}"
        
        # 显示分页信息
        if invitees_data['total_pages'] > 1:
            if user_lang.startswith('zh'):
                message += f"\n\n📄 第 {page}/{invitees_data['total_pages']} 页"
            else:
                message += f"\n\n📄 Page {page}/{invitees_data['total_pages']}"
    
    # 构建键盘
    keyboard_rows = []
    
    # 分页按钮
    if invitees_data['total_pages'] > 1:
        pagination_row = []
        if page > 1:
            if user_lang.startswith('zh'):
                pagination_row.append(InlineKeyboardButton("⬅️ 上一页", callback_data=f'invite_page_{page-1}'))
            else:
                pagination_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'invite_page_{page-1}'))
        if page < invitees_data['total_pages']:
            if user_lang.startswith('zh'):
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
    await invite_friends_callback(update, context, page=page)

async def withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理提现 - Step 1: 输入 SOL 地址"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 获取用户余额
    from withdrawal_system import get_user_balance, get_user_withdrawals
    balance = get_user_balance(user_id)
    
    # 获取用户提现记录
    withdrawals = get_user_withdrawals(user_id, limit=5)
    
    # 构建提现记录文本
    history_text = ""
    if withdrawals:
        history_text = "\n\n📜 <b>最近提现记录</b>\n" if user_lang == 'zh-CN' else "\n\n📜 <b>Recent Withdrawals</b>\n"
        history_text += "─" * 20 + "\n"
        
        status_map = {
            'pending': ('⏳ 待审批', '⏳ Pending'),
            'processing': ('⚡ 处理中', '⚡ Processing'),
            'completed': ('✅ 已完成', '✅ Completed'),
            'rejected': ('❌ 已拒绝', '❌ Rejected'),
            'failed': ('⚠️ 失败', '⚠️ Failed')
        }
        
        for w in withdrawals:
            status_text = status_map.get(w['status'], (w['status'], w['status']))
            status_display = status_text[0] if user_lang == 'zh-CN' else status_text[1]
            
            # 格式化时间
            created_time = w['created_at'].strftime('%m/%d %H:%M') if w['created_at'] else '-'
            
            # 截取地址显示
            addr = w['sol_address']
            addr_display = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 12 else addr
            
            history_text += f"• <code>{w['amount']:.0f}</code> X2C → <code>{addr_display}</code>\n"
            history_text += f"  {status_display} | {created_time}\n"
    else:
        history_text = "\n\n💭 " + ("暂无提现记录" if user_lang == 'zh-CN' else "No withdrawal history")
    
    # 构建完整消息
    balance_text = f"\n\n💰 <b>可提现余额: {balance:.0f} X2C</b>" if user_lang == 'zh-CN' else f"\n\n💰 <b>Available Balance: {balance:.0f} X2C</b>"
    
    full_message = get_message(user_lang, 'withdraw_prompt') + balance_text + history_text
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await query.edit_message_text(
        full_message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    return WITHDRAW_ADDRESS

async def withdraw_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 SOL 地址/邮箱输入 - Step 2: 输入提现数量"""
    user_id = update.effective_user.id
    user_lang = get_user_language(user_id)
    
    address = update.message.text.strip()
    
    # 📝 记录提现请求日志
    logger.info(f"💰 [提现请求] user_id={user_id}, 提现地址/邮箱={address}")
    
    # 验证 SOL 地址
    from withdrawal_system import validate_sol_address
    if not validate_sol_address(address):
        await update.message.reply_text(get_message(user_lang, 'invalid_sol_address'))
        return WITHDRAW_ADDRESS
    
    # 保存地址到 context
    context.user_data['withdraw_address'] = address
    
    # 获取用户余额
    from withdrawal_system import get_user_balance
    balance = get_user_balance(user_id)
    
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    await update.message.reply_text(
        get_message(user_lang, 'withdraw_amount_prompt', address=address, balance=balance),
        reply_markup=keyboard
    )
    
    return WITHDRAW_AMOUNT

async def withdraw_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理提现数量输入 - Step 3: 二次确认"""
    user_id = update.effective_user.id
    user_lang = get_user_language(user_id)
    
    amount_str = update.message.text.strip()
    
    # 验证数量
    try:
        amount = float(amount_str)
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        await update.message.reply_text(get_message(user_lang, 'invalid_amount'))
        return WITHDRAW_AMOUNT
    
    # 检查余额
    from withdrawal_system import get_user_balance
    balance = get_user_balance(user_id)
    
    if amount > balance:
        await update.message.reply_text(
            get_message(user_lang, 'insufficient_balance', balance=balance)
        )
        return WITHDRAW_AMOUNT
    
    # 保存数量到 context
    context.user_data['withdraw_amount'] = amount
    
    # 显示确认消息
    address = context.user_data.get('withdraw_address')
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(get_message(user_lang, 'confirm_withdraw'), callback_data='confirm_withdraw')],
        [InlineKeyboardButton(get_message(user_lang, 'cancel_withdraw'), callback_data='back_to_menu')]
    ])
    
    await update.message.reply_text(
        get_message(user_lang, 'withdraw_confirm', amount=amount, address=address),
        reply_markup=keyboard
    )
    
    return WITHDRAW_CONFIRM

async def confirm_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """确认提现 - Step 4: 提交申请等待审批"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    address = context.user_data.get('withdraw_address')
    amount = context.user_data.get('withdraw_amount')
    
    if not address or not amount:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
        ]])
        await query.edit_message_text(
            get_message(user_lang, 'withdraw_failed', error='Missing withdrawal information'),
            reply_markup=keyboard
        )
        return ConversationHandler.END
    
    # 显示处理中消息
    await query.edit_message_text(
        "⏳ 正在提交提现申请..." if user_lang.startswith('zh') else "⏳ Submitting withdrawal request..."
    )
    
    # 创建提现申请（不立即转账，等待管理员审批）
    from withdrawal_system import create_withdrawal_request
    withdrawal_id = create_withdrawal_request(user_id, address, amount)
    
    if not withdrawal_id:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
        ]])
        await query.edit_message_text(
            get_message(user_lang, 'withdraw_failed', error='余额不足或创建请求失败'),
            reply_markup=keyboard
        )
        return ConversationHandler.END
    
    # 显示申请已提交的消息
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
    ]])
    
    if user_lang.startswith('zh'):
        success_msg = f"""✅ <b>提现申请已提交</b>

📋 申请编号：<code>#{withdrawal_id}</code>
💰 提现金额：{amount} X2C
📥 收款地址：<code>{address}</code>

⏳ <b>状态：</b>等待审批

💡 管理员将在 24 小时内审核您的申请。
审批通过后，资产将自动转入您的钱包。"""
    else:
        success_msg = f"""✅ <b>Withdrawal Request Submitted</b>

📋 Request ID: <code>#{withdrawal_id}</code>
💰 Amount: {amount} X2C
📥 Address: <code>{address}</code>

⏳ <b>Status:</b> Pending Approval

💡 Admin will review your request within 24 hours.
Once approved, assets will be transferred to your wallet automatically."""
    
    await query.edit_message_text(
        success_msg,
        reply_markup=keyboard,
        parse_mode='HTML'
    )
    
    # 清理 context
    context.user_data.pop('withdraw_address', None)
    context.user_data.pop('withdraw_amount', None)
    
    return ConversationHandler.END

async def tutorial_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理赚钱攻略/新手教程"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    message = get_message(user_lang, 'tutorial')
    
    # 添加快捷按钮：开始挖矿、提交链接、返回主菜单
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t('menu.get_tasks', user_lang), callback_data='get_tasks'),
            InlineKeyboardButton(t('menu.submit_link', user_lang), callback_data='submit_link'),
        ],
        [
            InlineKeyboardButton(get_message(user_lang, 'back_to_menu'), callback_data='back_to_menu')
        ]
    ])
    
    await query.edit_message_text(
        message, 
        reply_markup=keyboard,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理语言切换"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 支持 6 种语言
    keyboard = [
        [InlineKeyboardButton("🇨🇳 简体中文", callback_data="set_lang_zh-CN")],
        [InlineKeyboardButton("🇹🇼 繁體中文", callback_data="set_lang_zh-TW")],
        [InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")],
        [InlineKeyboardButton("🇯🇵 日本語", callback_data="set_lang_ja")],
        [InlineKeyboardButton("🇰🇷 한국어", callback_data="set_lang_ko")],
        [InlineKeyboardButton("🇪🇸 Español", callback_data="set_lang_es")],
        [InlineKeyboardButton(t('common.back_to_menu', user_lang), callback_data='back_to_menu')]
    ]
    
    await query.edit_message_text(
        t('language.select', user_lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置语言"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    logger.info(f"Language callback triggered: user_id={user_id}, callback_data={query.data}")
    
    # 支持新的语言代码格式 (zh-CN, zh-TW, en, ja, ko, es)
    new_lang = query.data.replace('set_lang_', '')
    logger.info(f"Switching language to: {new_lang}")
    
    # 验证语言代码
    if new_lang not in SUPPORTED_LANGUAGES:
        logger.warning(f"Unsupported language: {new_lang}")
        new_lang = 'zh-CN'  # 默认使用简体中文
    
    set_user_language(user_id, new_lang)
    
    # 获取用户信息
    user = query.from_user
    
    # 格式化欢迎消息，替换用户名
    username = user.username or user.first_name or f"User{user.id}"
    welcome_message = t('welcome', new_lang, username=username)
    keyboard = get_main_menu_keyboard(new_lang)
    
    # 直接编辑消息，而不是删除后发送新消息
    await query.edit_message_text(
        text=welcome_message,
        reply_markup=keyboard,
        parse_mode='HTML'
    )

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回主菜单"""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"⚠️ query.answer() failed: {e}")
    
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 获取用户名
    username = query.from_user.username or query.from_user.first_name or "用户"
    
    welcome_message = get_message(user_lang, 'welcome', username=username)
    keyboard = get_main_menu_keyboard(user_lang)
    
    try:
        await query.edit_message_text(welcome_message, reply_markup=keyboard, parse_mode='HTML')
    except Exception as e:
        logger.warning(f"⚠️ edit_message_text failed: {e}, trying send_message")
        # 如果编辑失败，尝试发送新消息
        try:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=welcome_message,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        except Exception as e2:
            logger.error(f"❌ send_message also failed: {e2}")
    
    # 清理 context 数据
    context.user_data.clear()
    
    return ConversationHandler.END

async def pending_task_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理点击 pending 状态的任务"""
    query = update.callback_query
    user_id = query.from_user.id
    user_lang = get_user_language(user_id)
    
    # 显示提示消息
    if user_lang.startswith('zh'):
        await query.answer("该任务正在核验中，请稍候...", show_alert=True)
    else:
        await query.answer("This task is being verified, please wait...", show_alert=True)

async def retry_submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理重试提交"""
    query = update.callback_query
    await query.answer()
    
    # 提取 task_id
    task_id = int(query.data.split('_')[-1])
    
    # 调用 submit_task_select_callback
    context.user_data['submit_task_id'] = task_id
    await submit_task_select_callback(update, context)

# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    logger.info("🚀 X2C DramaRelayBot Starting...")
    
    # 运行数据库迁移
    logger.info("🔧 Running database migrations...")
    auto_migrate()
    
    # 初始化异步验证队列表
    from async_verification_worker import init_pending_verifications_table
    init_pending_verifications_table()
    
    # 初始化数据库
    init_database()
    
    # 创建应用
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 启动异步验证 Worker
    verification_worker_task = None
    
    async def start_verification_worker(app):
        """启动验证 Worker 作为后台任务"""
        nonlocal verification_worker_task
        from async_verification_worker import run_verification_worker
        logger.info("🔧 Starting async verification worker...")
        
        async def worker_wrapper():
            try:
                await run_verification_worker(app.bot, link_verifier, interval=5)
            except asyncio.CancelledError:
                logger.info("🛑 Verification Worker 已取消")
            except Exception as e:
                logger.error(f"❌ Verification Worker 崩溃: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        verification_worker_task = asyncio.create_task(worker_wrapper())
        logger.info("✅ Verification Worker 任务已创建")
    
    async def stop_verification_worker(app):
        """停止验证 Worker"""
        nonlocal verification_worker_task
        if verification_worker_task and not verification_worker_task.done():
            verification_worker_task.cancel()
            try:
                await verification_worker_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ Verification Worker 已停止")
    
    application.post_init = start_verification_worker
    application.post_shutdown = stop_verification_worker
    
    # 启动分类同步调度器
    from category_sync_scheduler import start_category_sync_scheduler
    start_category_sync_scheduler(application)
    
    # 初始化 bot_settings 表并启动任务过期清理调度器
    from task_expiry import init_bot_settings_table, start_expiry_cleanup_scheduler
    init_bot_settings_table()
    start_expiry_cleanup_scheduler(application)
    
    # 命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("check_invitation", check_invitation_command))
    application.add_handler(CommandHandler("manual_reward", manual_reward_command))
    application.add_handler(CommandHandler("clear_pending", clear_pending_command))
    application.add_handler(CommandHandler("debug_pending", debug_pending_command))
    application.add_handler(CommandHandler("set_expiry", set_expiry_command))
    
    # 回调查询处理器
    application.add_handler(CallbackQueryHandler(get_tasks_callback, pattern='^get_tasks$'))
    application.add_handler(CallbackQueryHandler(task_detail_callback, pattern='^task_\\d+$'))
    # claim_task_callback 现在由 ConversationHandler 处理，不需要全局 handler
    application.add_handler(CallbackQueryHandler(submit_link_callback, pattern='^submit_link$'))
    application.add_handler(CallbackQueryHandler(my_power_callback, pattern='^my_power$'))
    application.add_handler(CallbackQueryHandler(ranking_callback, pattern='^ranking$'))
    application.add_handler(CallbackQueryHandler(airdrop_callback, pattern='^airdrop$'))
    application.add_handler(CallbackQueryHandler(invite_friends_callback, pattern='^invite_friends$'))
    application.add_handler(CallbackQueryHandler(invite_page_callback, pattern='^invite_page_'))
    application.add_handler(CallbackQueryHandler(tutorial_callback, pattern='^tutorial$'))
    application.add_handler(CallbackQueryHandler(language_callback, pattern='^language$'))
    application.add_handler(CallbackQueryHandler(set_language_callback, pattern='^set_lang_'))
    application.add_handler(CallbackQueryHandler(category_select_callback, pattern='^category_'))
    application.add_handler(CallbackQueryHandler(pagination_callback, pattern='^page_'))
    # back_to_menu 由 ConversationHandler 的 fallback 处理，不需要全局 handler
    
    # 对话处理器 - 提交链接
    submit_conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(submit_task_select_callback, pattern='^submit_task_\\d+$'),
            CallbackQueryHandler(submit_task_select_callback, pattern='^submit_link_\\d+$'),  # 支持从下载消息直接提交
            CallbackQueryHandler(claim_task_callback, pattern='^claim_\\d+$')  # 领取任务后直接进入提交状态
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
    
    # 对话处理器 - 提现
    withdraw_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_callback, pattern='^bind_wallet$')],
        states={
            WITHDRAW_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_address_handler)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount_handler)],
            WITHDRAW_CONFIRM: [
                CallbackQueryHandler(confirm_withdraw_callback, pattern='^confirm_withdraw$'),
                CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')
            ],
        },
        fallbacks=[CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$')],
    )
    application.add_handler(withdraw_conv_handler)
    
    # 全局 back_to_menu handler（放在 ConversationHandler 之后）
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern='^back_to_menu$'))
    
    # 全局 claim_task handler（作为备用，当 ConversationHandler 未匹配时触发）
    application.add_handler(CallbackQueryHandler(claim_task_callback, pattern='^claim_\\d+$'))
    
    # 重试提交 handler
    application.add_handler(CallbackQueryHandler(retry_submit_callback, pattern='^retry_submit_\d+$'))
    
    # pending 任务点击提示 handler
    application.add_handler(CallbackQueryHandler(pending_task_callback, pattern='^pending_task_\d+$'))
    
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
