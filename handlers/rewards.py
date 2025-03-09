# handlers/rewards.py
import telebot
from telebot import types
import sqlite3
import json
import random
from db import DATABASE, update_user_points, get_user

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
        bot.send_message(message.chat.id, "😢 <b>No platforms available.</b>", parse_mode="HTML")
        return
    for platform in platforms:
        markup.add(types.InlineKeyboardButton(f"📺 {platform}", callback_data=f"reward_{platform}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    bot.send_message(message.chat.id, "<b>🎯 Available Platforms 🎯</b>", parse_mode="HTML", reply_markup=markup)

def handle_platform_selection(bot, call, platform):
    stock = get_stock_for_platform(platform)
    if stock:
        text = f"<b>📺 {platform}</b>\n✅ {len(stock)} accounts available!"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 Claim Account", callback_data=f"claim_{platform}"))
    else:
        text = f"<b>📺 {platform}</b>\n😞 No accounts available."
        markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_rewards"))
    bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def claim_account(bot, call, platform):
    telegram_id = str(call.from_user.id)
    user = get_user(telegram_id)
    if not user:
        bot.answer_callback_query(call.id, "User not found.")
        return
    current_points = user[3]
    if current_points < 2:
        bot.answer_callback_query(call.id, "Insufficient points.")
        return
    stock = get_stock_for_platform(platform)
    if not stock:
        bot.answer_callback_query(call.id, "No accounts available.")
        return
    index = random.randint(0, len(stock)-1)
    account = stock.pop(index)
    update_stock_for_platform(platform, stock)
    new_points = current_points - 2
    update_user_points(telegram_id, new_points)
    bot.answer_callback_query(call.id, "Account claimed!")
    bot.send_message(call.message.chat.id, f"<b>Your account for {platform}:</b>\n<code>{account}</code>\nRemaining points: {new_points}", parse_mode="HTML")
    
