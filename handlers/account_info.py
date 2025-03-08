# handlers/account_info.py
from db import get_user

def send_account_info(bot, message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    if user:
        # Assuming user tuple: (user_id, username, join_date, points, referrals, banned, pending_referrer)
        text = (
            f"Username: {user[1]}\n"
            f"User ID: {user[0]}\n"
            f"Join Date: {user[2]}\n"
            f"Points: {user[3]}\n"
            f"Total Referrals: {user[4]}"
        )
    else:
        # Show default values if no record exists.
        text = (
            f"Username: {message.from_user.username or message.from_user.first_name}\n"
            f"User ID: {user_id}\n"
            "Join Date: N/A\n"
            "Points: 0\n"
            "Total Referrals: 0"
        )
    bot.send_message(message.chat.id, text)
    
