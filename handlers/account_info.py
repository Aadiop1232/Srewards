# handlers/account_info.py
from db import get_user

def send_account_info(bot, message):
    telegram_id = str(message.from_user.id)
    user = get_user(telegram_id)
    if user:
        # user tuple: (telegram_id, internal_id, username, join_date, points, referrals, banned, pending_referrer)
        text = (
            f"👤 *Account Info*\n"
            f"• *Username:* {user[2]}\n"
            f"• *User ID:* {user[1]}\n"  # Display internal_id
            f"• *Join Date:* {user[3]}\n"
            f"• *Balance:* {user[4]} points\n"
            f"• *Total Referrals:* {user[5]}"
        )
    else:
        text = (
            f"👤 *Account Info*\n"
            f"• *Username:* {message.from_user.username or message.from_user.first_name}\n"
            f"• *User ID:* N/A\n"
            "• *Join Date:* N/A\n"
            "• *Balance:* 0 points\n"
            "• *Total Referrals:* 0"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
