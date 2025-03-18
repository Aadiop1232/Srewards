from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    # If update is a callback query, update.from_user is the user who pressed the button.
    if hasattr(update, "data"):
        user_obj = update.from_user
        chat_id = update.message.chat.id
    else:
        user_obj = update.from_user
        chat_id = update.chat.id
    telegram_id = str(user_obj.id)
    user = get_user(telegram_id)
    if not user:
        add_user(telegram_id, user_obj.username or user_obj.first_name, datetime.now().strftime("%Y-%m-%d"))
        user = get_user(telegram_id)
    text = (
        "<b>👤 Account Info</b>\n"
        f"• <b>Username:</b> {user.get('username')}\n"
        f"• <b>User ID:</b> {user.get('telegram_id')}\n"
        f"• <b>Join Date:</b> {user.get('join_date')}\n"
        f"• <b>Balance:</b> {user.get('points')} points\n"
        f"• <b>Total Referrals:</b> {user.get('referrals')}\n"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")
