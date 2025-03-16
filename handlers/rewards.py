import telebot
from telebot import types
import random
import json
import config
from db import get_user, update_user_points, get_account_claim_cost
from handlers.logs import log_event

def send_rewards_menu(bot, message):
    """
    Displays a menu of available platforms.
    """
    from db import get_platforms  # Ensure get_platforms is defined in db.py
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
                              parse_mode="HTML",
                              reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, "<b>🎯 Available Platforms 🎯</b>",
                         parse_mode="HTML", reply_markup=markup)

def handle_platform_selection(bot, call, platform_name):
    """
    When a user clicks a platform button, show details including stock and price.
    """
    from db import get_connection
    import sqlite3
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    platform = c.fetchone()
    c.close()
    conn.close()
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return
    stock = json.loads(platform["stock"] or "[]")
    price = platform["price"] or get_account_claim_cost()
    if stock:
        text = (f"<b>{platform_name}</b>:\n"
                f"✅ Accounts Available: {len(stock)}\n"
                f"Price: {price} pts per account")
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 Claim Account", callback_data=f"claim_{platform_name}"))
    else:
        text = (f"<b>{platform_name}</b>:\n"
                f"😞 No accounts available at the moment.\n"
                f"Price: {price} pts per account")
        markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_rewards"))
    try:
        bot.edit_message_text(text,
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              parse_mode="HTML",
                              reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def send_premium_account(bot, chat_id, platform_name, account):
    """
    Sends the premium account message with the provided text,
    and attaches a "Report" button to allow the user to report issues.
    """
    text = (
        "🎉✨ <b>𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗨𝗡𝗟𝗢𝗖𝗞𝗘𝗗</b> ✨🎉\n"
        "📦 <b>𝗦𝗲𝗿𝘃𝗶𝗰𝗲:</b> " + platform_name + "\n"
        "🔑 <b>𝗬𝗼𝘂𝗿 𝗔𝗰𝗰𝗼𝗻𝘁:</b> " + account + "\n"
        "📌 <b>𝗛𝗼𝘄 𝘁𝗼 𝗹𝗼𝗴𝗶𝗻:</b>\n"
        "1️⃣ Copy the details\n"
        "2️⃣ Open app/website\n"
        "3️⃣ Paste & login\n"
        "❌ <b>𝗔𝗰𝗰𝗼𝗻𝘁 𝗻𝗼𝘁 𝘄𝗼𝗿𝗸𝗶𝗻𝗴?</b> Report below to get a refund of your points!\n"
        "By @shadowsquad0"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    # Report button added here. Its callback data "report_account" should be handled in your report handler.
    markup.add(types.InlineKeyboardButton("Report", callback_data="report_account"))
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

def claim_account(bot, call, platform_name):
    """
    Claims an account from a platform if the user has enough points.
    Deducts points, updates stock, and sends the premium account text.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if user is None:
        bot.send_message(call.message.chat.id, "User not found. Please /start the bot first.")
        return

    from db import get_connection, update_stock_for_platform
    import sqlite3
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM platforms WHERE platform_name = ?", (platform_name,))
    platform = c.fetchone()
    c.close()
    conn.close()
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return

    stock = json.loads(platform["stock"] or "[]")
    price = platform["price"] or get_account_claim_cost()
    try:
        current_points = int(user.get("points", 0))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error reading your points: {e}")
        return

    if current_points < price:
        bot.send_message(call.message.chat.id,
                         f"Insufficient points (each account costs {price} pts). Earn more via referrals or keys.")
        return

    if not stock:
        bot.send_message(call.message.chat.id, "No accounts available.")
        return

    index = random.randint(0, len(stock) - 1)
    account = stock.pop(index)
    update_stock_for_platform(platform_name, stock)
    new_points = current_points - price
    update_user_points(user_id, new_points)

    log_event(bot, "account_claim", f"User {user_id} claimed an account from {platform_name}. "
                                     f"Account: {account}. New balance: {new_points} pts.")
    send_premium_account(bot, call.message.chat.id, platform_name, account)
                              
