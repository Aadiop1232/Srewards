# rewards.py

import telebot
from telebot import types
import random
import config
from db import get_user, update_user_points, get_account_claim_cost, get_platforms
from handlers.logs import log_event
import json
import sqlite3

def send_rewards_menu(bot, message):
    """
    Shows available platforms in an inline keyboard. 
    Each button calls 'handle_platform_selection' for that specific platform.
    """
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
    """
    Called when the user selects a platform (callback data like 'reward_netflix').
    Shows how many accounts are in stock and offers a 'Claim Account' button if available.
    """
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
                "😞 No accounts available at the moment.\n"
                f"Price: {price} pts per account")
        markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_main"))
    try:
        bot.edit_message_text(text,
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def send_premium_account_info(bot, chat_id, platform_name, account_info):
    """
    Sends the fancy 'PREMIUM ACCOUNT UNLOCKED' text along with 
    login info and a 'Report' button in case the account doesn't work.
    """
    text = (
        "╔═════════━─━┅═❖═🌟═❖═┅═✧═┅═╗\n"
        "✨🎉 PREMIUM ACCOUNT UNLOCKED 🎉✨\n"
        "╚═════════━─── • ───━═══★\n"
        f"🔑 Service: {platform_name}\n"
        f"👤 Account: <code>{account_info}</code>\n\n"
        "┏━━━━━━━━━━━━━━━┓\n"
        "📌 HOW TO LOGIN\n"
        "┗━━━━━━━━━━━━━━━┛\n"
        "➊ Copy login details\n"
        "➋ Open The app/website\n"
        "➌ Paste & Login!\n\n"
        "═══════════════════\n"
        "❌ Having Trouble?\n"
        "▶ Report below for an immediate refund!\n"
        "★══━─── ─── • ────━══★\n"
        "By @shadowsquad0"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Report", callback_data="menu_report"))
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

def claim_account(bot, call, platform_name):
    """
    Deducts points from the user, randomly picks an account from the stock,
    sends the account info privately, and logs the event.
    """
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

    stock = json.loads(platform["stock"] or "[]")
    price = platform["price"] or get_account_claim_cost()

    try:
        current_points = int(user.get("points", 0))
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Error reading your points: {e}")
        return

    if current_points < price:
        bot.send_message(call.message.chat.id,
                         f"Insufficient points (each account costs {price} pts). "
                         "Earn more via referrals or keys.")
        return

    if not stock:
        bot.send_message(call.message.chat.id, "No accounts available.")
        return

    # Randomly pick an account from the stock
    index = random.randint(0, len(stock) - 1)
    account = stock.pop(index)

    # Update the stock in DB
    from db import update_stock_for_platform
    update_stock_for_platform(platform_name, stock)

    # Deduct points
    new_points = current_points - price
    from db import update_user_points
    update_user_points(user_id, new_points)

    # Log the action
    log_event(bot, "account_claim",
              f"User {user_id} claimed an account from {platform_name}. New balance: {new_points} pts.",
              user=call.from_user)

    # Send account info privately (or in the same chat if it's private)
    if call.message.chat.type == "private":
        target_chat = call.message.chat.id
    else:
        target_chat = call.from_user.id
        # Let them know to check DMs
        bot.send_message(call.message.chat.id,
                         "Account details have been sent to your private messages. Please check your DMs.")

    # Show the fancy unlocked account text
    send_premium_account_info(bot, target_chat, platform_name, account)
