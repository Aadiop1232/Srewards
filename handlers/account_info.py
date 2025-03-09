# handlers/account_info.py
from db import get_user

def send_account_info(bot, message):
    telegram_id = str(message.from_user.id)
    user = get_user(telegram_id)
    if user:
        # Expected schema: (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
        text = (
            f"👤 *Account Info* 😁\n"
            f"• *Username:* {user[2]}\n"
            f"• *User ID:* {user[1]}\n"
            f"• *Join Date:* {user[3]}\n"
            f"• *Balance:* {user[4]} points\n"
            f"• *Total Referrals:* {user[5]}"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
