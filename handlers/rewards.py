# handlers/rewards.py
import telebot
from telebot import types
import sqlite3
import json
import random
from db import DATABASE

def get_db_connection():
    return sqlite3.connect(DATABASE)

def get_platforms():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT platform_name FROM platforms")
    platforms = [row[0] for row in c.fetchall()]
    conn.close()
    return platforms

def get_stock_for_platform(platform_name):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT stock FROM platforms WHERE platform_name=?", (platform_name,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            return []
    return []

def update_stock_for_platform(platform_name, stock):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE platforms SET stock=? WHERE platform_name=?", (json.dumps(stock), platform_name))
    conn.commit()
    conn.close()

def send_rewards_menu(bot, message):
    platforms = get_platforms()
    markup = types.InlineKeyboardMarkup(row_width=2)
    if not platforms:
        bot.send_message(message.chat.id, "😢 No platforms available at the moment.")
        return
    for platform in platforms:
        markup.add(types.InlineKeyboardButton(f"📺 {platform}", callback_data=f"reward_{platform}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    try:
        bot.edit_message_text("🎯 *Available Platforms* 🎯", chat_id=message.chat.id,
                              message_id=message.message_id, parse_mode="Markdown", reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, "🎯 *Available Platforms* 🎯", parse_mode="Markdown", reply_markup=markup)

def handle_platform_selection(bot, call, platform):
    stock = get_stock_for_platform(platform)
    if stock:
        text = f"📺 *{platform}*:\n✅ *{len(stock)} accounts available!*"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 Claim Account", callback_data=f"claim_{platform}"))
    else:
        text = f"📺 *{platform}*:\n😞 No accounts available at the moment."
        markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_rewards"))
    bot.edit_message_text(text, chat_id=call.message.chat.id,
                          message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

def claim_account(bot, call, platform):
    stock = get_stock_for_platform(platform)
    if not stock:
        bot.answer_callback_query(call.id, "😞 No accounts available.")
        return
    index = random.randint(0, len(stock) - 1)
    account = stock.pop(index)
    update_stock_for_platform(platform, stock)
    bot.answer_callback_query(call.id, "🎉 Account claimed!")
    bot.send_message(call.message.chat.id, f"💳 *Your account for {platform}:*\n`{account}`", parse_mode="Markdown")
    
