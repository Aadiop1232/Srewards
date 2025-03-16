# handlers/rewards.py
import telebot
from telebot import types
import random
import config
import json
from db import get_user, update_user_points, get_account_claim_cost, get_platforms
from handlers.logs import log_event

def send_rewards_menu(bot, message):
    """Display the available platforms along with stock and price information."""
    platforms = get_platforms()
    if not platforms:
        bot.send_message(message.chat.id, "😢 No platforms available at the moment.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for platform in platforms:
        platform_name = platform.get("platform_name")
        # Parse the stock from JSON
        stock = json.loads(platform.get("stock") or "[]")
        # Use stored price or default account claim cost
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
    """Show details for a selected platform and display a Claim button if accounts are available."""
    conn = __import__('db').get_connection()
    conn.row_factory = telebot.types.DictRow
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
        text = f"<b>{platform_name}</b>:\n✅ Accounts Available: {len(stock)}\nPrice: {price} pts per account"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 Claim Account", callback_data=f"claim_{platform_name}"))
    else:
        text = f"<b>{platform_name}</b>:\n😞 No accounts available at the moment.\nPrice: {price} pts per account"
        markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="menu_rewards"))
    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def claim_account(bot, call, platform_name):
    """
    When a user claims an account:
    - Deduct the account price from their balance.
    - Remove an account from the platform's stock.
    - Send the claimed account details along with an inline "Report" button.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if user is None:
        bot.send_message(call.message.chat.id, "User not found. Please /start the bot first.")
        return
    # Retrieve platform data
    conn = __import__('db').get_connection()
    conn.row_factory = telebot.types.DictRow
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
        bot.send_message(call.message.chat.id, f"Insufficient points (each account costs {price} pts). Earn more via referrals or keys.")
        return
    if not stock:
        bot.send_message(call.message.chat.id, "No accounts available.")
        return
    # Randomly select an account from stock
    index = random.randint(0, len(stock) - 1)
    account = stock.pop(index)
    from db import update_stock_for_platform
    update_stock_for_platform(platform_name, stock)
    new_points = current_points - price
    update_user_points(user_id, new_points)
    log_event(bot, "account_claim", f"User {user_id} claimed an account from {platform_name}. Account: {account}. New balance: {new_points} pts.")
    
    # Prepare and send account details with an inline "Report" button
    account_message = (f"🎉 Account claimed!\nYour account for {platform_name}:\n<code>{account}</code>\n"
                       f"Remaining points: {new_points}")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Report", callback_data="report_account"))
    bot.send_message(call.message.chat.id, account_message, parse_mode="HTML", reply_markup=markup)
