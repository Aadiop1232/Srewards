# account_info.py
import telebot
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    """
    Displays the user's account info in a fancy ASCII box.
    Works for both a Message or a CallbackQuery.
    
    Make sure in your main code you do:
       send_account_info(bot, call)
    not:
       send_account_info(bot, call.message)
    """
    if isinstance(update, telebot.types.CallbackQuery):
        chat_id = update.message.chat.id
        user_obj = update.from_user
    elif isinstance(update, telebot.types.Message):
        chat_id = update.chat.id
        user_obj = update.from_user
    else:
        return

    telegram_id = str(user_obj.id)
    user = get_user(telegram_id)
    if not user:
        new_username = user_obj.username or user_obj.first_name
        add_user(telegram_id, new_username, datetime.now().strftime("%Y-%m-%d"))
        user = get_user(telegram_id)

    username = user.get("username", "N/A")
    join_date = user.get("join_date", "N/A")
    balance = user.get("points", 0)
    referrals = user.get("referrals", 0)

    text = (
        "╭━━━✦❘༻👤 ACCOUNT INFO ༺❘✦━━━╮\n"
        "┃\n"
        f"┃ ✧ Username: {username}\n"
        f"┃ ✧ User ID: {telegram_id}\n"
        f"┃ ✧ Join Date: {join_date}\n"
        f"┃ ✧ Balance: {balance} pts\n"
        f"┃ ✧ Total Referrals: {referrals}\n"
        "┃\n"
        "╰━━━━━━━✦✧✦━━━━━━━╯"
    )

    bot.send_message(chat_id, text, parse_mode="HTML")
  
