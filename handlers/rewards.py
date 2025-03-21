import telebot
from telebot import types
import random
import config
import json
import sqlite3
from db import get_user, update_user_points, get_account_claim_cost, get_platforms
from handlers.logs import log_event

def send_rewards_menu(bot, message):
    platforms = get_platforms()
    if not platforms:
        bot.send_message(message.chat.id, "😢 No platforms available at the moment.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for platform in platforms:
        platform_name = platform.get("platform_name")
        stock = json.loads(platform.get("stock") or "[]")
        price = platform.get("price") or get_account_claim_cost()
        btn_text = f"{platform_name} | Stock: {len(stock)} | Price: {price} pts"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"reward_{platform_name}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    try:
        bot.edit_message_text("<b>🎯 Available Platforms 🎯</b>", 
                              chat_id=message.chat.id,
                              message_id=message.message_id, 
                              parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, "<b>🎯 Available Platforms 🎯</b>", 
                         parse_mode="HTML", reply_markup=markup)

def handle_platform_selection(bot, call, platform_name):
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    platform = c.fetchone()
    c.close()
    conn.close()
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return
    # Convert the row to a dictionary
    platform = dict(platform)
    stock = json.loads(platform["stock"] or "[]")
    price = platform["price"] or get_account_claim_cost()
    if stock:
        text = f"<b>{platform_name}</b>:\n✅ Accounts Available: {len(stock)}\nPrice: {price} pts per account"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 Claim Account", callback_data=f"claim_{platform_name}"))
    else:
        text = f"<b>{platform_name}</b>:\n😞 No accounts available at the moment.\nPrice: {price} pts per account"
        markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_rewards"))
    try:
        bot.edit_message_text(text, 
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id, 
                              parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def send_premium_account_info(bot, chat_id, platform_name, account_info):
    """
    Sends the claimed account to the user, now with a "Report" button attached.
    """
    import io
    from telebot import types

    # Check if this is a cookie account or a normal "login pass" account
    if isinstance(account_info, dict) and account_info.get("type") == "cookie":
        # For cookie platforms, we might be sending as a .txt file or raw text, etc.
        # This snippet is just the example if you're sending a text message:
        cookie_content = account_info.get("content", "No details found")
        header = ("━━━━━━━━━━━━━━━━━━━━━━\n"
                  "🎁 Here Is Your Cookie For: " + platform_name + "\n"
                  "━━━━━━━━━━━━━━━━━━━━━━\n\n")
        full_text = header + cookie_content
        # Create an inline keyboard with a Report button
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Report", callback_data="menu_report"))
        # Send as text, or you could send as a file
        bot.send_message(chat_id, full_text, parse_mode="HTML", reply_markup=markup)

    else:
        # For normal "account" platforms or if the item is a simple string
        text = f"""🎉✨ PREMIUM ACCOUNT UNLOCKED 

✨🎉📦 Service: {platform_name}

🔑 Your Account: 
<code>{account_info}</code> 📌 

How to login:
1️⃣ Copy the details
2️⃣ Open app/website
3️⃣ Paste & login

❌ Account not working? Tap the button below to report and get a refund!
By @shadowsquad0"""
        # Create an inline keyboard with a Report button
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Report", callback_data="menu_report"))
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)


def claim_account(bot, call, platform_name):
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if user is None:
        bot.send_message(call.message.chat.id, "User not found. Please /start the bot first.")
        return
    conn = __import__('db').get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    platform = c.fetchone()
    c.close()
    conn.close()
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return
    # Convert platform row to dictionary
    platform = dict(platform)
    stock = json.loads(platform["stock"] or "[]")
    price = platform["price"] or get_account_claim_cost()
    try:
        current_points = int(user.get("points", 0))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error reading your points: {e}")
        return
    if current_points < price:
        bot.send_message(call.message.chat.id, f"Insufficient points (each account costs {price} pts). Earn more via referrals or keys.")
        return
    if not stock:
        bot.send_message(call.message.chat.id, "No accounts available.")
        return
    index = random.randint(0, len(stock) - 1)
    account = stock.pop(index)
    from db import update_stock_for_platform
    update_stock_for_platform(platform_name, stock)
    new_points = current_points - price
    update_user_points(user_id, new_points)
    log_event(bot, "account_claim", f"User {user_id} claimed an account from {platform_name}. New balance: {new_points} pts.")
    send_premium_account_info(bot, call.message.chat.id, platform_name, account)
