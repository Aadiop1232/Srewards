# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, update):
    if hasattr(update, "data"):
        user_obj = update.from_user
        chat_id = update.message.chat.id
    else:
        user_obj = update.from_user
        chat_id = update.chat.id

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
        f"<b>👤 Account Info 😁</b>\n"
        f"• <b>Username:</b> {user[2]}\n"
        f"• <b>User ID:</b> {user[0]}\n"
        f"• <b>Join Date:</b> {user[3]}\n"
        f"• <b>Balance:</b> {user[4]} points\n"
        f"• <b>Total Referrals:</b> {user[5]}"
    )
    bot.send_message(chat_id, text, parse_mode="HTML")
    
