# handlers/account_info.py
from db import get_user, add_user
from datetime import datetime

def send_account_info(bot, message):
    telegram_id = str(message.from_user.id)
    user = get_user(telegram_id)
    # If the user is not registered, add them
    if user is None:
        add_user(
            telegram_id,
            message.from_user.username or message.from_user.first_name,
            datetime.now().strftime("%Y-%m-%d")
        )
        user = get_user(telegram_id)
    # Now display the user’s info
    # Assuming the user schema: 
    # (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
    text = (
        f"👤 *Account Info*\n"
        f"• *Username:* {user[2]}\n"
        f"• *User ID:* {user[1]}\n"  # internal_id
        f"• *Join Date:* {user[3]}\n"
        f"• *Balance:* {user[4]} points\n"
        f"• *Total Referrals:* {user[5]}"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
