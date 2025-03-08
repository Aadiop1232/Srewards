# handlers/account_info.py
from db import get_user

def send_account_info(bot, message):
    """
    Retrieves the latest user data from the database and sends a message
    displaying the real-time balance (points), referral count, join date, and username.
    """
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    if user:
        # user tuple: (user_id, username, join_date, points, referrals, banned, pending_referrer)
        text = (
            f"👤 *Account Info*\n"
            f"• *Username:* {user[1]}\n"
            f"• *User ID:* {user[0]}\n"
            f"• *Join Date:* {user[2]}\n"
            f"• *Balance:* {user[3]} points\n"
            f"• *Total Referrals:* {user[4]}"
        )
    else:
        text = (
            f"👤 *Account Info*\n"
            f"• *Username:* {message.from_user.username or message.from_user.first_name}\n"
            f"• *User ID:* {user_id}\n"
            "• *Join Date:* N/A\n"
            "• *Balance:* 0 points\n"
            "• *Total Referrals:* 0"
        )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")
    
