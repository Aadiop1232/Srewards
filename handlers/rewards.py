# handlers/rewards.py
import telebot
from telebot import types
import random
import config
from db import get_user, update_user_points, get_account_claim_cost, db
from handlers.logs import log_event

def get_platforms():
    """
    Returns a list of platforms from the database.
    Each platform should have:
      - platform_name
      - stock: a list of account entries
      - price: points cost per account (if not set, defaults to get_account_claim_cost())
    """
    platforms = list(db.platforms.find())
    return platforms

def get_platform(platform_name):
    """Fetch a platform document by its name."""
    return db.platforms.find_one({"platform_name": platform_name})

def update_stock_for_platform(platform_name, stock):
    """Update the stock array for a given platform."""
    db.platforms.update_one(
        {"platform_name": platform_name},
        {"$set": {"stock": stock}}
    )

def send_rewards_menu(bot, message):
    """
    Sends the rewards menu to the user with available platforms.
    Each button shows the platform name, available stock count, and claim price.
    """
    platforms = get_platforms()
    if not platforms:
        bot.send_message(message.chat.id, "😢 No platforms available at the moment.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for platform in platforms:
        platform_name = platform.get("platform_name")
        stock = platform.get("stock", [])
        price = platform.get("price", get_account_claim_cost())
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
    When a user selects a platform, displays its details: name, available stock, and claim price.
    If stock exists, provides a "Claim Account" button.
    """
    platform = get_platform(platform_name)
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return

    stock = platform.get("stock", [])
    price = platform.get("price", get_account_claim_cost())
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
                              message_id=call.message.message_id,
                              parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)

def claim_account(bot, call, platform_name):
    """
    Processes a user's request to claim an account:
      - Checks that the user has enough points based on the platform's claim price.
      - Deducts points from the user's balance.
      - Removes one account from the platform's stock.
      - Sends the account details to the user.
      - Logs the claim event.
    """
    user_id = str(call.from_user.id)
    user = get_user(user_id)
    if user is None:
        bot.send_message(call.message.chat.id, "User not found. Please /start the bot first.")
        return

    platform = get_platform(platform_name)
    if not platform:
        bot.send_message(call.message.chat.id, "Platform not found.")
        return

    stock = platform.get("stock", [])
    price = platform.get("price", get_account_claim_cost())
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

    # Select a random account from the stock
    index = random.randint(0, len(stock) - 1)
    account = stock.pop(index)
    update_stock_for_platform(platform_name, stock)

    new_points = current_points - price
    update_user_points(user_id, new_points)

    log_event(bot, "account_claim", f"User {user_id} claimed an account from {platform_name}. Account: {account}. New balance: {new_points} pts.")

    bot.send_message(
        call.message.chat.id,
        f"🎉 Account claimed!\nYour account for {platform_name}:\n<code>{account}</code>\nRemaining points: {new_points}",
        parse_mode="HTML"
    )
