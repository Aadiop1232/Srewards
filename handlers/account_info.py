from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    if hasattr(update, "message"):
        chat_id = update.message.chat.id
        user_obj = update.from_user
    elif hasattr(update, "data"):
        chat_id = update.message.chat.id
        user_obj = update.from_user
    else:
        chat_id = update.chat.id
        user_obj = update.from_user

    telegram_id = str(user_obj.id)
    user = get_user(telegram_id)
    if not user:
        add_user(
            telegram_id,
            user_obj.username or user_obj.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
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
    
