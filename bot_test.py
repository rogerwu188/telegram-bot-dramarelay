#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X2C DramaRelayBot - 测试版本
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# 配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN') or '8580007118:AAFmA9OlAT1D_XzUnKGL-0qU_FPK7G6uwyQ'

# 测试欢迎消息
WELCOME_MESSAGE = """🎬 欢迎使用 DramaRelayBot！

这是 X2C 全球短剧分发节点的任务入口。
你可以领取短剧素材 → 上传到 TikTok / YouTube / IG 等平台 → 
回到这里提交链接 → 获得 Node Power 算力点数，参与 X2C 的奖励池。

👉 点击菜单领取短剧任务
👉 上传片段到你喜欢的平台
👉 提交链接完成节点贡献

一起构建全球短剧分发网络。"""

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    keyboard = [
        [
            InlineKeyboardButton("🎬 领取短剧任务", callback_data='get_tasks'),
            InlineKeyboardButton("📤 提交链接", callback_data='submit_link'),
        ],
        [
            InlineKeyboardButton("📊 我的算力", callback_data='my_power'),
            InlineKeyboardButton("🏆 排行榜", callback_data='ranking'),
        ],
        [
            InlineKeyboardButton("🎁 空投状态", callback_data='airdrop'),
            InlineKeyboardButton("💼 绑定钱包", callback_data='bind_wallet'),
        ],
        [
            InlineKeyboardButton("ℹ️ 使用教程", callback_data='tutorial'),
            InlineKeyboardButton("🌐 切换语言", callback_data='language'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(WELCOME_MESSAGE, reply_markup=reply_markup)
    logger.info(f"User {update.effective_user.id} started the bot")

def main():
    """主函数"""
    logger.info("🚀 X2C DramaRelayBot (Test Version) Starting...")
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    
    logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
